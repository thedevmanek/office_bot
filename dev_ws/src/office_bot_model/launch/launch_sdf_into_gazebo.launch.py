#!/usr/bin/env python3

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _configured_robot_description(package_share):
    robot_description_path = os.path.join(
        package_share, "models", "officebot", "robot.urdf"
    )
    controller_config_path = os.path.join(
        package_share, "controllers", "officebotcontroller.yaml"
    )
    package_mesh_prefix = "package://office_bot_model/models/officebot/"
    gazebo_mesh_prefix = f"file://{package_share}/models/officebot/"

    with open(robot_description_path, "r", encoding="utf-8") as robot_file:
        robot_description = robot_file.read().replace(
            "@OFFICEBOT_CONTROLLER_CONFIG@", controller_config_path
        )
    gazebo_robot_description = robot_description.replace(
        package_mesh_prefix, gazebo_mesh_prefix
    )

    temp_robot = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".urdf",
        prefix="officebot_",
        delete=False,
    )
    with temp_robot:
        temp_robot.write(gazebo_robot_description)

    return robot_description, temp_robot.name


def generate_launch_description():
    package_share = get_package_share_directory("office_bot_model")

    world_description_path = os.path.join(
        package_share, "models", "worlds", "office_world", "service.world"
    )
    robot_description, configured_robot_path = _configured_robot_description(
        package_share
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
    )

    ignition_launch = ExecuteProcess(
        cmd=[
            PathJoinSubstitution([FindExecutable(name="ign")]),
            "gazebo",
            "-r",
            world_description_path,
        ],
        output="screen",
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "office_bot",
            "-file",
            configured_robot_path,
            "-x",
            "0",
            "-y",
            "2",
            "-z",
            "0.5",
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    drawers_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_group_position_controller",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    wheels_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "mecanum_drive_controller",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )

    rviz_config_path = os.path.join(package_share, "config", "robot_config.rviz")
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[{"use_sim_time": True}],
    )

    gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gazebo_bridge",
        arguments=[
            "/lidar/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked",
            "/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock",
            "/lidar@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
            "/imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
            "/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        ],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    ekf_config_path = os.path.join(package_share, "controllers", "ekf.yaml")
    robot_localization_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_node",
        output="screen",
        parameters=[ekf_config_path, {"use_sim_time": True}],
    )

    slam_config_path = os.path.join(package_share, "controllers", "slam_toolbox.yaml")
    slam_toolbox_node = Node(
        package="slam_toolbox",
        executable="async_slam_toolbox_node",
        name="slam_toolbox",
        output="screen",
        parameters=[slam_config_path, {"use_sim_time": True}],
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [FindPackageShare("nav2_bringup"), "launch", "navigation_launch.py"]
                )
            ]
        ),
        launch_arguments={
            "params_file": os.path.join(
                package_share, "controllers", "nav2_params.yaml"
            ),
            "use_sim_time": "true",
            "slam": "True",
        }.items(),
    )

    cmd_vel_stamper_node = Node(
        package="office_bot_controller_handlers",
        executable="velstamper",
        name="velstamper",
        output="screen",
    )

    def start_after_spawn():
        return [
            robot_localization_node,
            slam_toolbox_node,
            nav2_launch,
            rviz_node,
            gz_bridge_node,
            cmd_vel_stamper_node,
            joint_state_broadcaster_spawner,
            drawers_controller_spawner,
            wheels_controller_spawner,
        ]

    return LaunchDescription(
        [
            robot_state_publisher_node,
            ignition_launch,
            spawn_robot,
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_robot,
                    on_exit=start_after_spawn(),
                )
            ),
        ]
    )
