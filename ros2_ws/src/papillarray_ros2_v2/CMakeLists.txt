cmake_minimum_required(VERSION 3.8)
project(papillarray_ros2_v2)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_interfaces REQUIRED)

add_executable(papillarray_ros2_node src/papillarray_ros2_node.cpp)

target_include_directories(papillarray_ros2_node PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/lib
)

target_link_libraries(papillarray_ros2_node
  ${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK.a
)
ament_target_dependencies(papillarray_ros2_node rclcpp std_msgs sensor_interfaces)

install(TARGETS 
  papillarray_ros2_node
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)


if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
