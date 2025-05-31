#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch_ros.actions import Node  

from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution, FindExecutable, Command
from launch.event_handlers import OnProcessExit

def generate_launch_description():


    world_description_path = PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "models",
            'service.world'  # Adjust this path as needed
        ]
    )


    # Path to the robot SDF description
    robot_description_path = PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "models",
            "robot.urdf",  # Adjust this path as needed
        ]
    )

    robot_description = Command([
        FindExecutable(name='cat'),
        ' ',
        robot_description_path
    ])

    robot_state_publisher_node = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
    )
    # Gazebo Ignition Launch
    ignition_launch = ExecuteProcess(
        cmd=[
            PathJoinSubstitution([FindExecutable(name='ign')]),  # 'ign' is the Ignition Gazebo executable
            "gazebo",
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
            "-x", "0",  # X position
            "-y", "2",  # Y position
            "-z", "0.5" # Z position
            
        ],
        output="screen"
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager", "/controller_manager",
        ],
        output="screen",
    )

        # Load controllers
    # Spawner for joint_group_position_controller
    drawers_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_group_position_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )

    # Spawner for mecanum_drive_controller
    wheels_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["mecanum_drive_controller", "--controller-manager", "/controller_manager"],
        output="screen",
    )
    # Add RViz to the launch description
    rviz_config_path = PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "config",
            "robot_config.rviz",  # Adjust this path to your specific RViz configuration file

        ]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],  # Launch RViz with the configuration file
    )

      # Bridge for LiDAR topic
    gz_bridge_node=  Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='lidar_bridge',
            arguments=['/lidar/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked', '/imu@sensor_msgs/msg/Imu@gz.msgs.IMU'],

            output='screen'
        )

    return LaunchDescription([
        robot_state_publisher_node,
        ignition_launch,
        spawn_robot,
        joint_state_broadcaster_spawner,
        drawers_controller_spawner,
        wheels_controller_spawner,
        rviz_node,
        gz_bridge_node
    ])

