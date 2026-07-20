# ============================================================
# papillarray_interfaces — CMake 构建脚本
# PapillArray 触觉传感器的 ROS 2 自定义接口包
# 定义消息 (.msg) 和服务 (.srv)，供驱动节点与上层应用使用
# ============================================================

cmake_minimum_required(VERSION 3.5)
project(papillarray_interfaces)

# 默认使用 C99 标准
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# 默认使用 C++14 标准
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

# 开启常用编译警告，帮助发现潜在问题
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ---------- 查找依赖 ----------
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)  # ROS 接口代码生成器
find_package(std_msgs REQUIRED)                    # 标准消息类型 (Header 等)

# ---------- 生成接口代码 ----------
# rosidl_generate_interfaces 会将 .msg / .srv 编译为 C++ / Python 类型
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PillarState.msg"              # 单触点状态消息
  "msg/SensorState.msg"              # 传感器完整状态消息
  "srv/BiasRequest.srv"              # 偏置校准请求服务
  "srv/StartSlipDetection.srv"       # 启动滑动检测服务
  "srv/StopSlipDetection.srv"        # 停止滑动检测服务
  DEPENDENCIES std_msgs
)

# ---------- 测试 ----------
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # 以下行跳过版权检查（项目暂未配置版权声明）
  # 添加版权和许可证信息后可取消注释
  #set(ament_cmake_copyright_FOUND TRUE)
  # 以下行跳过 cpplint（仅在 git 仓库中生效）
  # 如不在 git 仓库中运行可取消注释
  #set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
