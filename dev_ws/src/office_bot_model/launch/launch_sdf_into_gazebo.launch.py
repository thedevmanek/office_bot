#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution, FindExecutable

def generate_launch_description():
    
    world_description_path = PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "models",
            "empty_world.sdf",  # Adjust this path as needed
        ]
    )
    # Path to the robot SDF description
    robot_description_path = PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "models",
            "robot.sdf",  # Adjust this path as needed
        ]
    )

    # Gazebo Ignition Launch
    ignition_launch = ExecuteProcess(
        cmd=[
            PathJoinSubstitution([FindExecutable(name='ign')]),  # 'ign' is the Ignition Gazebo executable
            "gazebo",
            "--verbose",
            "-r",  # Automatically run the simulation
            world_description_path
            
        ],
        output='screen'
    )

    # Spawn the robot in Gazebo Ignition via ROS 2 service
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", "office_bot",  # Name of the robot
            "-file", robot_description_path,  # Use the SDF file directly
        ],
        output="screen"
    )

    return LaunchDescription([
        ignition_launch,
        spawn_robot
    ])
