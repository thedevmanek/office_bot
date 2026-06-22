#!/usr/bin/env bash
set -euo pipefail

source /opt/ros/humble/setup.bash
source install/local_setup.bash

OFFICE_BOT_MODEL_SHARE="$(ros2 pkg prefix office_bot_model)/share/office_bot_model"
OFFICE_WORLD_MODELS="${OFFICE_BOT_MODEL_SHARE}/models/worlds/office_world/models"

export GZ_SIM_SYSTEM_PLUGIN_PATH="/opt/ros/humble/lib${GZ_SIM_SYSTEM_PLUGIN_PATH:+:${GZ_SIM_SYSTEM_PLUGIN_PATH}}"
export IGN_GAZEBO_SYSTEM_PLUGIN_PATH="/opt/ros/humble/lib${IGN_GAZEBO_SYSTEM_PLUGIN_PATH:+:${IGN_GAZEBO_SYSTEM_PLUGIN_PATH}}"
export GZ_SIM_RESOURCE_PATH="${OFFICE_WORLD_MODELS}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export IGN_GAZEBO_RESOURCE_PATH="${OFFICE_WORLD_MODELS}${IGN_GAZEBO_RESOURCE_PATH:+:${IGN_GAZEBO_RESOURCE_PATH}}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-3.3}"

ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
