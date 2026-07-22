# ROS2 集成笔记

> 基于原厂手册 PTSROS2_1.0_MAN_NOV23 的中文总结。

---

## 1. 系统要求

原厂测试环境：

| 项目 | 规格 |
|------|------|
| CPU | Intel Core i5-1240P |
| RAM | 16 GB |
| OS | Ubuntu 20.04.2 LTS |
| ROS2 | Foxy |

**我们的环境**：Ubuntu 24.04 + ROS2 Jazzy。包结构应兼容，但可能需要调整 CMake/依赖。

---

## 2. 包结构

原厂 ROS2 包位于 `vendor/ROS2/ros2_contactile_sensors/`。本仓库已扁平化到标准 colcon 结构，包直接位于 `ros2_ws/src/` 下。

### papillarray_ros2_v2（主驱动包）

| 文件 | 说明 |
|------|------|
| `src/papillarray_ros2_node.cpp` | 节点源码 |
| `src/papillarray_ros2_node.hpp` | 节点头文件 |
| `launch/papillarray.launch` | 启动文件 |
| `include/` | PTSDK C++ 头文件与静态库 |
| `CMakeLists.txt` | 构建配置 |
| `package.xml` | 包清单 |

### papillarray_interfaces（消息接口包）

| 文件 | 说明 |
|------|------|
| `msg/PillarState.msg` | 单柱状态消息 |
| `msg/SensorState.msg` | 单传感器状态消息 |
| `srv/BiasRequest.srv` | Bias 服务 |
| `srv/StartSlipDetection.srv` | 启动滑动检测服务 |
| `srv/StopSlipDetection.srv` | 停止滑动检测服务 |
| `CMakeLists.txt` | 构建配置 |
| `package.xml` | 包清单 |

### papillarray_serial_driver（自研 Python 串口驱动）

该包直接解析 PTS v2.0 串口协议，不依赖原厂 PTSDK 静态库。它与
`papillarray_ros2_v2` 发布相同消息并提供同名服务，两套驱动应二选一运行，不能同时占用
同一个串口。

---

## 3. 编译步骤

```bash
cd ~/project/contactile_pts_lab/ros2_ws

# 1. 先编译接口包
colcon build --packages-select papillarray_interfaces \
    --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3

# 2. 再编译主包
colcon build --packages-select papillarray_ros2_v2 \
    --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3

# 3. 加载环境
source install/setup.bash
```

构建自研串口驱动：

```bash
colcon build --packages-select papillarray_interfaces papillarray_serial_driver \
    --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
```

> **注意**：如果系统同时存在 uv 的 Python，colcon 可能找到错误的解释器。必须显式指定 `-DPython3_EXECUTABLE=/usr/bin/python3`。

---

## 4. 节点参数

启动文件 `papillarray.launch` 中可配置以下参数：

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `hub_id` | int | — | Controller 标识符 |
| `n_sensors` | int | 2 | 连接的传感器数量 |
| `com_port` | string | `/dev/ttyACM0` | 串口设备 |
| `baud_rate` | int | **9600** | 波特率 |
| `parity` | int | 0 | 校验位 |
| `byte_size` | int | 8 | 字节大小 |
| `is_flush` | bool | — | 是否 flush 硬件缓冲区 |
| `sampling_rate` | int | — | 采样率 (100/250/500/1000 Hz) |

自研串口驱动默认使用 115200 baud，另外提供 `serial_timeout_sec`、
`contact_threshold_n`、`reconnect_initial_delay_sec` 和 `reconnect_max_delay_sec` 参数。

---

## 5. Topic 与消息

### 发布的 Topic

| Topic | 消息类型 | 说明 |
|-------|----------|------|
| `/hub_0/sensor_0` | `SensorState` | 传感器 0 数据 |
| `/hub_0/sensor_1` | `SensorState` | 传感器 1 数据 |

### SensorState 消息结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `header` | std_msgs/Header | ROS2 时间戳与 frame_id |
| `tus` | int64 | 控制器时间戳 (µs)，保留原厂字段名 |
| `pillars` | PillarState[] | 各柱状态数组 |
| `gfx` | float32 | 全局 X 力 (N) |
| `gfy` | float32 | 全局 Y 力 (N) |
| `gfz` | float32 | 全局 Z 力 (N) |
| `gtx` | float32 | 全局 X 力矩 (N·mm) |
| `gty` | float32 | 全局 Y 力矩 (N·mm) |
| `gtz` | float32 | 全局 Z 力矩 (N·mm) |
| `friction_est` | float32 | 摩擦估计 |
| `target_grip_force` | float32 | 目标夹持力 (N) |
| `is_sd_active` | bool | 滑动检测是否激活，保留原厂字段名 |
| `is_ref_loaded` | bool | 参考柱是否被切向加载，保留原厂字段名 |

> 力矩参考点为**中心柱 P4 的当前顶端位置**。

### PillarState 消息结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int32 | 柱体 ID |
| `dx` | float32 | X 位移 (mm) |
| `dy` | float32 | Y 位移 (mm) |
| `dz` | float32 | Z 位移 (mm) |
| `fx` | float32 | X 力 (N) |
| `fy` | float32 | Y 力 (N) |
| `fz` | float32 | Z 力 (N) |
| `in_contact` | bool | 是否接触 |
| `slip_state` | int32 | 滑动状态（见 PTSDKConstants） |

---

## 6. 服务

| 服务名 | 说明 | 关键提示 |
|--------|------|----------|
| `SendBiasRequest` | Bias 传感器 | 耗时最长 2 秒，必须无负载 |
| `StartSlipDetection` | 启动滑动检测 | 需在柱接触后、切向加载前调用 |
| `StopSlipDetection` | 停止滑动检测 | 停止并重置算法 |

---

## 7. 启动节点

```bash
# 加载环境
source ~/project/contactile_pts_lab/ros2_ws/install/setup.bash

# 启动
ros2 launch papillarray_ros2_v2 papillarray.launch.py
```

不使用原厂 SDK、改用自研串口解析时启动：

```bash
ros2 launch papillarray_serial_driver papillarray_serial.launch.py
```

---

## 8. 日志文件

- 日志开关：在 `papillarray_ros2_node.cpp` 第 3 行附近，修改 `PTSDKListener` 的构造参数 `isLogging`
- 日志位置：`<ros2_ws>/Logs/`
- 日志命名：`LOG_YYYY_MM_DD_hh_mm_ss.csv`
- 修改后需重新编译：`colcon build --packages-select papillarray_ros2_v2`

---

## 9. 与 C++ / Python SDK 的对比

| 特性 | ROS2 | C++ | Python |
|------|------|-----|--------|
| 波特率 | 9600 | 9600 | 115200 |
| 架构 | 发布-订阅 | 直接调用 | 直接调用 |
| 多传感器 | Topic `/hub_0/sensor_X` | 手动管理多个 `PTSDKSensor` | 手动管理多个 `PTSDKSensor` |
| Bias 方式 | Service 调用 | `sendBiasRequest()` | `sendBiasRequest()` |
| 适用场景 | 机器人系统集成 | 最低延迟 | 快速原型/数据分析 |
