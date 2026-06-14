#!/usr/bin/env bash
set -euo pipefail

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-3.3}"
export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"

source /etc/profile.d/openhri-container-env.sh

cd "${OPENHRI_WS}"
exec ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
