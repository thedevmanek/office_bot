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

add_executable(drawers src/drawers.cpp)
ament_target_dependencies(drawers 
rclcpp  
trajectory_msgs
control_msgs)

install(TARGETS
  drawers
  DESTINATION lib/${PROJECT_NAME})

ament_package()