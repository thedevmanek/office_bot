#!/usr/bin/env bash

_openhri_had_nounset=0
case $- in
  *u*)
    _openhri_had_nounset=1
    set +u
    ;;
esac

source /opt/ros/humble/setup.bash

if [[ -f /workspace/openhri-office/dev_ws/install/setup.bash ]]; then
  source /workspace/openhri-office/dev_ws/install/setup.bash
fi

if [[ "${_openhri_had_nounset}" == "1" ]]; then
  set -u
fi
unset _openhri_had_nounset

cd /workspace/openhri-office/dev_ws 2>/dev/null || true
