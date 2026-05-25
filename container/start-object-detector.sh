#!/usr/bin/env bash
set -euo pipefail

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"

source /opt/ros/humble/setup.bash
source "${OPENHRI_WS}/install/local_setup.bash"

cd "${OPENHRI_WS}"
exec ros2 run object_detector detect --ros-args \
  --params-file "${OPENHRI_WS}/src/object_detector/config/object_detector.yaml"
