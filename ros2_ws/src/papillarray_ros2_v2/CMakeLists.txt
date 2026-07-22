# ============================================================
# papillarray_ros2_v2 — CMake 构建脚本
# PapillArray 触觉传感器 ROS 2 驱动节点
# 通过串口与传感器集线器通信，链接 Contactile 官方 PTSDK 库
# ============================================================

cmake_minimum_required(VERSION 3.8)
project(papillarray_ros2_v2)

# 默认使用 C99 标准
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# 默认使用 C++17 标准 (PTSDK 库使用了 C++17 特性)
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

# 开启常用编译警告
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ---------- 查找依赖 ----------
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)                      # ROS 2 C++ 客户端库
find_package(std_msgs REQUIRED)                    # 标准消息类型
find_package(papillarray_interfaces REQUIRED)      # PapillArray 自定义接口

# ---------- 构建可执行节点 ----------
add_executable(papillarray_ros2_node
  src/csv_logger.cpp
  src/papillarray_ros2_node.cpp
)

# 添加 PTSDK 头文件搜索路径
target_include_directories(papillarray_ros2_node PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/lib
)

# 链接 PTSDK 静态库 (libPTSDK.a)
# 原厂二进制默认不提交到 Git；允许使用方显式指定已获授权的本地 SDK 路径。
set(PTSDK_LIBRARY
  "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK.a"
  CACHE FILEPATH "Path to the Contactile PTSDK static library"
)
if(NOT EXISTS "${PTSDK_LIBRARY}")
  message(FATAL_ERROR
    "Contactile PTSDK library not found: ${PTSDK_LIBRARY}\n"
    "Copy the licensed x86_64 libPTSDK.a into papillarray_ros2_v2/lib, "
    "or configure with -DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a"
  )
endif()
target_link_libraries(papillarray_ros2_node
  ${PTSDK_LIBRARY}
)
ament_target_dependencies(papillarray_ros2_node rclcpp std_msgs papillarray_interfaces)

# ---------- 安装规则 ----------
# 安装可执行文件到 lib/<package_name>/
install(TARGETS
  papillarray_ros2_node
  DESTINATION lib/${PROJECT_NAME})

# 安装 launch 文件到 share/<package_name>/
install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

# ---------- 测试 ----------
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()

  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_csv_logger
    test/test_csv_logger.cpp
    src/csv_logger.cpp
  )
  target_include_directories(test_csv_logger PRIVATE src)
  ament_target_dependencies(test_csv_logger papillarray_interfaces)
endif()

ament_package()
