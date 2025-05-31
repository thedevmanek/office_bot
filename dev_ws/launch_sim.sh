#!/bin/zsh
source /opt/ros/humble/setup.zsh
source install/local_setup.zsh
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib/
export MESA_GL_VERSION_OVERRIDE=3.3
export GZ_SIM_RESOURCE_PATH=$GAZEBO_MODEL_PATH:/home/thedevmanek/office_bot/dev_ws/src/office_bot_model/models/worlds/office_world/models
ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
