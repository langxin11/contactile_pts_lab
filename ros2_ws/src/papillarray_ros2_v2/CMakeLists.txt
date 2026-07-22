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

# ---------- 选择 PTSDK 静态库 ----------
# PTSDK_LIBRARY 用于特殊工具链或外部 SDK，非空时优先于自动检测。
set(PTSDK_LIBRARY
  ""
  CACHE FILEPATH "Explicit PTSDK library path; empty enables platform detection"
)

set(PTSDK_ARCH
  "auto"
  CACHE STRING "PTSDK architecture: auto, x86_64, aarch64, arm32_hf, arm32_sf, or arm32v6_hf"
)
set_property(CACHE PTSDK_ARCH PROPERTY STRINGS
  auto
  x86_64
  aarch64
  arm32_hf
  arm32_sf
  arm32v6_hf
)

if(PTSDK_LIBRARY)
  set(PTSDK_SELECTED_LIBRARY "${PTSDK_LIBRARY}")
  set(PTSDK_SELECTED_ARCH "explicit path")
else()
  string(TOLOWER "${CMAKE_SYSTEM_PROCESSOR}" PTSDK_SYSTEM_PROCESSOR)
  string(TOLOWER
    "${CMAKE_LIBRARY_ARCHITECTURE};${CMAKE_CXX_COMPILER_TARGET};${CMAKE_CXX_FLAGS}"
    PTSDK_ABI_HINTS
  )

  if(PTSDK_ARCH STREQUAL "auto")
    if(PTSDK_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64)$")
      set(PTSDK_SELECTED_ARCH "x86_64")
    elseif(PTSDK_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
      set(PTSDK_SELECTED_ARCH "aarch64")
    elseif(PTSDK_SYSTEM_PROCESSOR MATCHES "^(armv6|armv6l)$")
      if(PTSDK_ABI_HINTS MATCHES "gnueabihf|armhf|-mfloat-abi=hard")
        set(PTSDK_SELECTED_ARCH "arm32v6_hf")
      else()
        message(FATAL_ERROR
          "Cannot safely select an ARMv6 PTSDK library from ABI hints: ${PTSDK_ABI_HINTS}\n"
          "Only the ARMv6 hard-float library is available. Configure with "
          "-DPTSDK_ARCH=arm32v6_hf or -DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a"
        )
      endif()
    elseif(PTSDK_SYSTEM_PROCESSOR MATCHES "^(arm|armv7|armv7l|armhf)$")
      if(PTSDK_ABI_HINTS MATCHES "gnueabihf|armhf|-mfloat-abi=hard")
        set(PTSDK_SELECTED_ARCH "arm32_hf")
      elseif(PTSDK_ABI_HINTS MATCHES "gnueabi|-mfloat-abi=(soft|softfp)")
        set(PTSDK_SELECTED_ARCH "arm32_sf")
      else()
        message(FATAL_ERROR
          "Cannot determine the ARM32 floating-point ABI from: ${PTSDK_ABI_HINTS}\n"
          "Configure with -DPTSDK_ARCH=arm32_hf or -DPTSDK_ARCH=arm32_sf"
        )
      endif()
    else()
      message(FATAL_ERROR
        "Unsupported processor for automatic PTSDK selection: ${CMAKE_SYSTEM_PROCESSOR}\n"
        "Configure with -DPTSDK_ARCH=<supported-arch> or "
        "-DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a"
      )
    endif()
  else()
    set(PTSDK_SELECTED_ARCH "${PTSDK_ARCH}")
  endif()

  if(PTSDK_SELECTED_ARCH STREQUAL "x86_64")
    set(PTSDK_SELECTED_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK.a")
  elseif(PTSDK_SELECTED_ARCH STREQUAL "aarch64")
    set(PTSDK_SELECTED_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK_aarch64.a")
  elseif(PTSDK_SELECTED_ARCH STREQUAL "arm32_hf")
    set(PTSDK_SELECTED_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK_arm32_hf.a")
  elseif(PTSDK_SELECTED_ARCH STREQUAL "arm32_sf")
    set(PTSDK_SELECTED_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK_arm32_sf.a")
  elseif(PTSDK_SELECTED_ARCH STREQUAL "arm32v6_hf")
    set(PTSDK_SELECTED_LIBRARY "${CMAKE_CURRENT_SOURCE_DIR}/lib/libPTSDK_arm32v6_hf.a")
  else()
    message(FATAL_ERROR
      "Invalid PTSDK_ARCH=${PTSDK_SELECTED_ARCH}; expected x86_64, aarch64, "
      "arm32_hf, arm32_sf, or arm32v6_hf"
    )
  endif()
endif()

if(NOT EXISTS "${PTSDK_SELECTED_LIBRARY}")
  message(FATAL_ERROR
    "Contactile PTSDK library not found: ${PTSDK_SELECTED_LIBRARY}\n"
    "Restore the matching library under papillarray_ros2_v2/lib, or configure "
    "with -DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a"
  )
endif()

message(STATUS
  "PTSDK platform: processor=${CMAKE_SYSTEM_PROCESSOR}, selection=${PTSDK_SELECTED_ARCH}"
)
message(STATUS "PTSDK library: ${PTSDK_SELECTED_LIBRARY}")

target_link_libraries(papillarray_ros2_node
  "${PTSDK_SELECTED_LIBRARY}"
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
