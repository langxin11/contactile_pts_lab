# papillarray_ros2_v2

PapillArray 触觉传感器的 ROS 2 驱动节点，通过串口与传感器集线器通信，实时发布触觉数据并暴露控制服务。

## 包说明

本包是 PapillArray 传感器在 ROS 2 环境下的核心驱动。它封装了 Contactile 官方 PTSDK 静态库 (`libPTSDK.a`)，通过串口与传感器硬件通信，并将采集到的位移、力、力矩、摩擦系数、滑动状态等数据以 ROS 2 Topic 形式发布，同时提供偏置校准和滑动检测等服务接口。

## 硬件架构

```
传感器1 ──┐
传感器2 ──┼── 集线器 (Hub) ──[USB/串口]── 上位机 (本节点)
传感器N ──┘
```

- 一个集线器最多连接 **4 个**传感器（`MAX_NSENSOR = 4`）
- 每个传感器最多 **25 个**触点（`MAX_NPILLAR = 25`）
- 数据通过串口（默认 `/dev/ttyACM0`）以 500 Hz 频率传输

## Topic（发布话题）

每个传感器独立发布数据，话题格式为：

```
/hub_{hub_id}/sensor_{sensor_id}
```

消息类型：[`papillarray_interfaces/msg/SensorState`](../papillarray_interfaces/msg/SensorState.msg)

示例（默认 hub_id=0，2 个传感器）：

```
/hub_0/sensor_0    — 传感器 0 的数据
/hub_0/sensor_1    — 传感器 1 的数据
```

话题使用 `rclcpp::SensorDataQoS()` 服务质量配置，确保实时数据优先交付。

## Service（服务）

| 服务名 | 类型 | 说明 |
|--------|------|------|
| `/hub_{hub_id}/send_bias_request` | `BiasRequest` | 发送偏置校准请求 |
| `/hub_{hub_id}/start_slip_detection` | `StartSlipDetection` | 启动滑动检测 |
| `/hub_{hub_id}/stop_slip_detection` | `StopSlipDetection` | 停止滑动检测 |

## 启动参数

通过 launch 文件启动时可配置以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `hub_id` | `0` | 集线器 ID，用于命名 Topic 和 Service |
| `n_sensors` | `2` | 传感器数量（1 或 2） |
| `com_port` | `/dev/ttyACM0` | 串口设备路径 |
| `baud_rate` | `9600` | 串口波特率 |
| `parity` | `0` | 校验位：0=无校验, 1=奇校验, 2=偶校验 |
| `byte_size` | `8` | 数据位宽 |
| `is_flush` | `true` | 是否在缓冲区溢出时清空硬件输入缓冲 |
| `sampling_rate` | `500` | 采样频率（Hz）：100、250、500 或 1000 |

## 快速开始

### 1. 编译

```bash
cd ros2_ws
colcon build --packages-select papillarray_interfaces papillarray_ros2_v2
source install/setup.bash
```

### 2. 启动（默认参数）

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py
```

### 3. 自定义参数启动

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  com_port:=/dev/ttyACM1 \
  sampling_rate:=1000 \
  n_sensors:=1
```

### 4. 查看传感器数据

```bash
# 查看传感器 0 的实时数据
ros2 topic echo /hub_0/sensor_0

# 查看数据发布频率
ros2 topic hz /hub_0/sensor_0
```

### 5. 调用服务

```bash
# 启动滑动检测
ros2 service call /hub_0/start_slip_detection papillarray_interfaces/srv/StartSlipDetection

# 发送偏置校准请求
ros2 service call /hub_0/send_bias_request papillarray_interfaces/srv/BiasRequest
```

## 依赖

- `rclcpp` — ROS 2 C++ 客户端库
- `std_msgs` — ROS 2 标准消息
- `papillarray_interfaces` — PapillArray 自定义接口
- `libPTSDK.a` — Contactile 官方 PTSDK 静态库（已包含在 `lib/` 目录，支持 x86_64 和 ARM 多平台）

## 数据流

```
串口数据 → PTSDKListener
              │
              ├─ 解析为 PTSDKSensor 对象（每个物理传感器一个）
              │
              └─ updateData() (按 sampling_rate 定时触发)
                       │
                       ├─ 读取每个传感器的全局力/力矩
                       ├─ 读取每个 pillar 的位移/力/接触/滑动状态
                       ├─ 读取摩擦系数估计和目标抓取力
                       │
                       └─ 发布 SensorState 消息到对应 Topic
```

## 日志

驱动运行日志可通过 ROS 2 日志系统查看。SDK 层的 CSV 数据日志默认写入 `~/.ros/Logs/` 目录。
