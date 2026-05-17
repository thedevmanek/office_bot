#!/bin/zsh
source /opt/ros/humble/setup.zsh
source install/local_setup.zsh
OFFICE_BOT_MODEL_SHARE="$(ros2 pkg prefix office_bot_model)/share/office_bot_model"
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib/
export MESA_GL_VERSION_OVERRIDE=3.3
export GZ_SIM_RESOURCE_PATH=$GAZEBO_MODEL_PATH:$OFFICE_BOT_MODEL_SHARE/models/worlds/office_world/models
ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
