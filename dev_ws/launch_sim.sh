#!/bin/zsh
source /opt/ros/humble/setup.zsh
source install/setup.zsh
export GZ_SIM_RESOURCE_PATH=/home/thedevmanek/dev_ws/src/office_bot_model/models/officebot
ros2 launch office_bot_model launch_sdf_into_gazebo.launch.py
