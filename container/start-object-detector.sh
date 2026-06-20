#!/usr/bin/env bash
set -euo pipefail

export OPENHRI_WS="${OPENHRI_WS:-/workspace/openhri-office/dev_ws}"
export OPENHRI_DETECTOR_PARAMS="${OPENHRI_WS}/src/object_detector/config/object_detector.yaml"

source /etc/profile.d/openhri-container-env.sh

cd "${OPENHRI_WS}"
exec ros2 run object_detector detect --ros-args \
  --params-file "${OPENHRI_DETECTOR_PARAMS}"
