#!/usr/bin/env bash

_openhri_had_nounset=0
case $- in
  *u*)
    _openhri_had_nounset=1
    set +u
    ;;
esac

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"

source /opt/ros/humble/setup.bash

if [[ -f "${OPENHRI_WS}/install/setup.bash" ]]; then
  source "${OPENHRI_WS}/install/setup.bash"
fi

_openhri_prepend_path_env() {
  local name="$1"
  local value="$2"
  local existing="${!name:-}"
  case ":${existing}:" in
    *":${value}:"*) export "${name}=${existing}" ;;
    *) export "${name}=${value}${existing:+:${existing}}" ;;
  esac
}

if command -v ros2 >/dev/null 2>&1; then
  OFFICE_BOT_MODEL_PREFIX="$(ros2 pkg prefix office_bot_model 2>/dev/null || true)"
  if [[ -n "${OFFICE_BOT_MODEL_PREFIX}" ]]; then
    OFFICE_BOT_MODEL_SHARE="${OFFICE_BOT_MODEL_PREFIX}/share/office_bot_model"
    OFFICE_WORLD_MODELS="${OFFICE_BOT_MODEL_SHARE}/models/worlds/office_world/models"
    _openhri_prepend_path_env GZ_SIM_RESOURCE_PATH "${OFFICE_WORLD_MODELS}"
    _openhri_prepend_path_env IGN_GAZEBO_RESOURCE_PATH "${OFFICE_WORLD_MODELS}"
    _openhri_prepend_path_env GZ_SIM_SYSTEM_PLUGIN_PATH /opt/ros/humble/lib
    _openhri_prepend_path_env IGN_GAZEBO_SYSTEM_PLUGIN_PATH /opt/ros/humble/lib
  fi
  unset OFFICE_BOT_MODEL_PREFIX OFFICE_BOT_MODEL_SHARE OFFICE_WORLD_MODELS
fi

if [[ "${_openhri_had_nounset}" == "1" ]]; then
  set -u
fi
unset _openhri_had_nounset
unset -f _openhri_prepend_path_env

cd "${OPENHRI_WS}" 2>/dev/null || true
