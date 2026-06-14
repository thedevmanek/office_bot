#!/usr/bin/env bash
set -euo pipefail

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"
export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"

if [[ ! -d "${OPENHRI_WS}/src" ]]; then
  echo "Mounted ROS workspace not found at ${OPENHRI_WS}/src." >&2
  echo "Start the container from the repository root so compose can mount the checkout." >&2
  exit 1
fi

source /etc/profile.d/openhri-container-env.sh
cd "${OPENHRI_WS}"

mkdir -p build install log

metadata_hash() {
  find src \
    \( -name package.xml -o -name setup.py -o -name setup.cfg -o -name CMakeLists.txt \) \
    -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    | sha256sum \
    | awk '{ print $1 }'
}

marker_dir="${OPENHRI_WS}/install/.openhri"
marker_file="${marker_dir}/rosdep-inputs.sha256"
mkdir -p "${marker_dir}"

if [[ "${OPENHRI_BOOTSTRAP_ROSDEP:-1}" == "1" ]]; then
  current_hash="$(metadata_hash)"
  previous_hash=""
  if [[ -f "${marker_file}" ]]; then
    previous_hash="$(<"${marker_file}")"
  fi

  if [[ "${current_hash}" != "${previous_hash}" ]]; then
    echo "Installing ROS package dependencies for mounted workspace..."
    apt-get update
    rosdep install --from-paths src --ignore-src -r -y
    printf '%s\n' "${current_hash}" > "${marker_file}"
  else
    echo "ROS dependency metadata unchanged; skipping rosdep install."
  fi
else
  echo "Skipping rosdep install because OPENHRI_BOOTSTRAP_ROSDEP=${OPENHRI_BOOTSTRAP_ROSDEP}."
fi

echo "Building mounted ROS workspace..."
colcon build --symlink-install

echo "OpenHRI workspace bootstrap complete."
