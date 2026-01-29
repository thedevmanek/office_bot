#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch_ros.actions import Node  
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution, FindExecutable, Command, LaunchConfiguration
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
            parameters=[{'robot_description': robot_description,'use_sim_time': True}],
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
        arguments=["-d", rviz_config_path,],  # Launch RViz with the configuration file
        parameters=[{'use_sim_time': True}]

    )

      # Bridge for LiDAR topic
    gz_bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gazebo_bridge',
        arguments=[
            '/lidar/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
            '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',
            '/lidar@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/imu@sensor_msgs/msg/Imu@gz.msgs.IMU',
            '/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    
    find_ekf=PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "controllers",
            "ekf.yaml",  # Adjust this path to your specific RViz configuration file

        ]
    )
    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_node',
        output='screen',
        parameters=[find_ekf, {'use_sim_time': True}]
    )
    find_slam_yaml=PathJoinSubstitution(
        [
            FindPackageShare("office_bot_model"),
            "controllers",
            "slam_toolbox.yaml",  # Adjust this path to your specific RViz configuration file

        ]
    )
    # from launch_ros.actions import ComposableNodeContainer
    # from launch_ros.descriptions import ComposableNode

    # composable_nodes = [
    #         ComposableNode(
    #             package='image_proc',
    #             plugin='image_proc::RectifyNode',
    #             name='rectify_node',
    #             namespace='camera',
    #             remappings=[
    #                 ('image', 'image_raw'),
    #                 ('image_rect', 'image_rectified'),
    #             ],
    #             parameters=[{'use_sim_time': True},
    #                         {'queue_size': 10},
    #                 {'approximate_sync': True}],
    #         )
    #     ]

    # img_proc = ComposableNodeContainer(
    #         name='image_proc_container',
    #         package='rclcpp_components',
    #         executable='component_container',
    #         namespace= 'camera',
    #         composable_node_descriptions=composable_nodes,
    #     )

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[find_slam_yaml, {'use_sim_time': True}]
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'params_file': PathJoinSubstitution([
                FindPackageShare("office_bot_model"),
                "controllers",
                "nav2_params.yaml"
            ]),
            'use_sim_time': 'true',
            'slam': 'True'
        }.items()
    )
        # Add CmdVelStamper Node
    cmd_vel_stamper_node = Node(
        package='office_bot_controller_handlers',  # Replace with your actual package name
        executable='velstamper',  # This should match the name of your compiled executable
        name='velstamper',
        output='screen'
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
        # img_proc
    ]

    from launch.actions import RegisterEventHandler
    from launch.event_handlers import OnProcessExit

    launch_description = [
        robot_state_publisher_node,
        ignition_launch,
        spawn_robot,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_robot,
                on_exit=start_after_spawn()
            )
        ),
    ]



    return LaunchDescription(
        launch_description)

