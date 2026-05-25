#!/usr/bin/env bash
set -euo pipefail

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-3.3}"
export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"

source /opt/ros/humble/setup.bash
source "${OPENHRI_WS}/install/local_setup.bash"

OFFICE_BOT_MODEL_SHARE="$(ros2 pkg prefix office_bot_model)/share/office_bot_model"
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib/
export GZ_SIM_RESOURCE_PATH="${GAZEBO_MODEL_PATH:-}:${OFFICE_BOT_MODEL_SHARE}/models/worlds/office_world/models"

cd "${OPENHRI_WS}"
exec ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
