# papillarray_ros2_v2

PapillArray 触觉传感器的 ROS 2 驱动节点，通过串口与传感器集线器通信，实时发布触觉数据并暴露控制服务。

## 包说明

本包是 PapillArray 传感器在 ROS 2 环境下的核心驱动。仓库包含 Ubuntu x86_64 使用的
Contactile 官方 PTSDK 静态库 (`libPTSDK.a`)，通过串口与传感器硬件通信，并将采集到的
位移、力、力矩、摩擦系数、滑动状态等数据以 ROS 2 Topic 形式发布，同时提供偏置校准和
滑动检测等服务接口。仓库应保持私有；公开或二次分发前仍需确认原厂 SDK 许可。

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
| `log_dir` | 空字符串 | CSV 日志目录；为空时关闭日志 |
| `csv_pillar_detail` | `false` | 是否追加逐 pillar 位移和力；接触与滑移状态始终记录 |

## 快速开始

### 1. 确认运行平台

仓库已经包含 Ubuntu x86_64 使用的静态库：

```text
papillarray_ros2_v2/lib/libPTSDK.a
```

在 ARM 或其他平台上，需要换用对应架构的已授权 PTSDK 静态库，并在构建时传入绝对路径：

```bash
colcon build --packages-select papillarray_interfaces papillarray_ros2_v2 \
  --cmake-args -DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a
```

缺少静态库时，CMake 会停止并给出上述配置提示，不会等到链接阶段才失败。

### 2. 编译

```bash
cd ros2_ws
colcon build --packages-select papillarray_interfaces papillarray_ros2_v2
source install/setup.bash
```

### 3. 启动（默认参数）

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py
```

### 4. 自定义参数启动

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  com_port:=/dev/ttyACM1 \
  sampling_rate:=1000 \
  n_sensors:=1
```

### 5. 查看传感器数据

```bash
# 查看传感器 0 的实时数据
ros2 topic echo /hub_0/sensor_0

# 查看数据发布频率
ros2 topic hz /hub_0/sensor_0
```

### 6. 调用服务

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
- `libPTSDK.a` — Contactile 官方 PTSDK x86_64 静态库，已包含在 `lib/` 目录

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

## CSV 时间序列日志

原厂 SDK 日志在当前 Linux 版本中可能生成权限为 `000` 的文件，因此节点默认禁用 SDK
日志，改用自身的可配置 CSV 写入器。CSV 默认关闭；启用示例：

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  log_dir:=$HOME/contactile_logs
```

默认 CSV 每个传感器、每个采样时刻写一行，包含：

- Controller 时间戳和 ROS 时间戳；
- 全局力、全局力矩、摩擦估计和目标抓握力；
- 滑移检测状态；
- 所有 pillar 的接触状态和 `slip_state`。

需要同时保存逐 pillar 位移和力时使用：

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  log_dir:=$HOME/contactile_logs \
  csv_pillar_detail:=true
```

日志文件权限设置为 `0600`，仅当前用户可读写。为了限制 500 Hz 采集回调中的磁盘开销，
写入使用标准流缓存，并每 500 行主动刷新一次。
