#!/usr/bin/env bash
set -u

ERRORS=0
WARNINGS=0
PODMAN_ENGINE_OK=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_SYSTEM="$(uname -s 2>/dev/null || printf unknown)"
HOST_MACHINE="$(uname -m 2>/dev/null || printf unknown)"
CONTAINER_NAME="${OPENHRI_CONTAINER_NAME:-openhri-office}"

pass() {
  printf 'OK: %s\n' "$1"
}

warn() {
  WARNINGS=$((WARNINGS + 1))
  printf 'WARN: %s\n' "$1"
}

fail() {
  ERRORS=$((ERRORS + 1))
  printf 'FAIL: %s\n' "$1"
}

detect_platform() {
  case "${HOST_SYSTEM}-${HOST_MACHINE}" in
    Darwin-arm64 | *-aarch64 | *-arm64)
      printf 'linux/arm64'
      ;;
    *)
      printf 'linux/amd64'
      ;;
  esac
}

is_numeric() {
  case "$1" in
    '' | *[!0-9]*)
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

port_in_use() {
  port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk -v target=":${port}" 'NR > 1 && $4 ~ target "$" { found = 1 } END { exit found ? 0 : 1 }'
    return $?
  fi

  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "${port}" >/dev/null 2>&1
    return $?
  fi

  return 2
}

container_running() {
  if ! command -v podman >/dev/null 2>&1; then
    return 1
  fi

  if ! podman container exists "${CONTAINER_NAME}" >/dev/null 2>&1; then
    return 1
  fi

  state="$(podman inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  [[ "${state}" == "true" ]]
}

check_platform() {
  platform="${OPENHRI_PLATFORM:-$(detect_platform)}"

  case "${platform}" in
    linux/amd64 | linux/arm64)
      pass "OPENHRI_PLATFORM=${platform}"
      ;;
    *)
      fail "OPENHRI_PLATFORM must be linux/amd64 or linux/arm64; got '${platform}'."
      printf '      Example: OPENHRI_PLATFORM=linux/amd64 make start\n'
      ;;
  esac
}

check_podman() {
  if ! command -v podman >/dev/null 2>&1; then
    fail "Podman is not installed or is not on PATH."
    printf '      Install Podman, then rerun: make doctor\n'
    return
  fi

  pass "Podman command is available"

  if [[ "${HOST_SYSTEM}" == "Darwin" ]]; then
    if podman machine list --format '{{.Running}}' 2>/dev/null | awk '$1 == "true" { found = 1 } END { exit found ? 0 : 1 }'; then
      pass "A Podman machine is running"
    else
      fail "No running Podman machine found on macOS."
      printf '      Run: podman machine start\n'
    fi
  fi

  if podman info >/dev/null 2>&1; then
    PODMAN_ENGINE_OK=1
    pass "Podman engine responds"
  else
    fail "Podman is installed but the engine is not responding."
    if [[ "${HOST_SYSTEM}" == "Darwin" ]]; then
      printf '      Run: podman machine start\n'
    else
      printf '      Check the Podman service, then rerun: make doctor\n'
    fi
  fi

  if [[ "${PODMAN_ENGINE_OK}" != "1" ]]; then
    warn "Skipping Podman Compose check until the Podman engine responds."
  elif podman compose version >/dev/null 2>&1; then
    pass "Podman Compose is available"
  else
    fail "Podman Compose is not available."
    printf "      Install Podman Compose support so 'podman compose version' works.\n"
  fi
}

check_ports() {
  novnc_port="${OPENHRI_NOVNC_PORT:-6080}"
  vnc_port="${OPENHRI_VNC_PORT:-5900}"
  object_ui_port="${OPENHRI_OBJECT_UI_PORT:-8080}"

  if container_running; then
    pass "Container '${CONTAINER_NAME}' is already running; skipping host port availability checks"
    return
  fi

  if ! command -v lsof >/dev/null 2>&1 && ! command -v ss >/dev/null 2>&1 && ! command -v nc >/dev/null 2>&1; then
    warn "Cannot check host ports because lsof, ss, and nc are unavailable."
    return
  fi

  for item in "OPENHRI_NOVNC_PORT:${novnc_port}" "OPENHRI_VNC_PORT:${vnc_port}" "OPENHRI_OBJECT_UI_PORT:${object_ui_port}"; do
    name="${item%%:*}"
    port="${item#*:}"

    if ! is_numeric "${port}"; then
      fail "${name} must be numeric; got '${port}'."
      continue
    fi

    if port_in_use "${port}"; then
      fail "Host port ${port} is already in use (${name})."
      printf '      Choose another port, for example: OPENHRI_NOVNC_PORT=6081 OPENHRI_OBJECT_UI_PORT=8081 make start\n'
    else
      pass "Host port ${port} is available (${name})"
    fi
  done
}

check_disk() {
  min_free_kb="${OPENHRI_MIN_FREE_KB:-8388608}"

  if ! is_numeric "${min_free_kb}"; then
    fail "OPENHRI_MIN_FREE_KB must be numeric; got '${min_free_kb}'."
    return
  fi

  available_kb="$(df -Pk "${REPO_ROOT}" 2>/dev/null | awk 'NR == 2 { print $4 }')"
  if ! is_numeric "${available_kb}"; then
    warn "Could not determine free disk space for ${REPO_ROOT}."
    return
  fi

  available_mb=$((available_kb / 1024))
  min_free_mb=$((min_free_kb / 1024))

  if ((available_kb < min_free_kb)); then
    fail "Only ${available_mb} MB free near ${REPO_ROOT}; expected at least ${min_free_mb} MB."
    printf '      Free disk space before pulling the runtime image.\n'
  else
    pass "Disk space looks sufficient (${available_mb} MB free)"
  fi
}

printf 'OpenHRI preflight checks\n'
printf 'Repository: %s\n' "${REPO_ROOT}"
printf '\n'

check_platform
check_podman
check_ports
check_disk

printf '\n'
if ((ERRORS > 0)); then
  printf 'OpenHRI doctor found %d problem(s). Fix them and rerun: make doctor\n' "${ERRORS}"
  exit 1
fi

if ((WARNINGS > 0)); then
  printf 'OpenHRI doctor completed with %d warning(s).\n' "${WARNINGS}"
else
  printf 'OpenHRI doctor passed.\n'
fi
