cmake_minimum_required(VERSION 3.5)
project(office_bot_controller_handlers)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)
find_package(control_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)


add_executable(velstamper src/velstamper.cpp)
ament_target_dependencies(velstamper 
rclcpp
tf2
tf2_geometry_msgs
nav_msgs  
trajectory_msgs
control_msgs)

install(TARGETS
  velstamper
  DESTINATION lib/${PROJECT_NAME})

ament_package()