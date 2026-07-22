# Contactile PapillArray ROS 2 驱动

本仓库提供 Contactile PapillArray 触觉传感器的 ROS 2 消息接口，以及两套可互换的串口
驱动。下游节点只依赖统一的 Topic、Message 和 Service，可以在不修改业务代码的情况下切换
原厂 PTSDK 驱动或自研纯 Python 协议驱动。

## 仓库结构

| Package | 类型 | 说明 |
|---------|------|------|
| `papillarray_interfaces` | `ament_cmake` | 定义 `SensorState`、`PillarState` 消息和三个控制服务 |
| `papillarray_ros2_v2` | C++ | 使用 Contactile 原厂 PTSDK 静态库读取传感器 |
| `papillarray_serial_driver` | Python | 直接解析 PTS v2.0 串口协议，不依赖原厂 SDK 运行库 |

两套驱动发布相同的消息并提供相同的服务，但不能同时占用同一个串口，也不应同时向同名
Topic 发布数据。

## 环境与依赖

当前开发环境：

- Ubuntu 24.04 x86_64
- ROS 2 Jazzy
- Python 3.10/3.12
- `colcon`、`rosdep`

安装系统依赖前，应先正确安装并加载 ROS 2：

```bash
source /opt/ros/jazzy/setup.bash
```

## 获取与构建

在目标项目的 ROS 2 工作区中 clone 本仓库：

```bash
mkdir -p ~/ros2_contactile/src
cd ~/ros2_contactile/src
git clone https://github.com/langxin11/contactile-papillarray-ros2.git
```

安装 ROS 依赖：

```bash
cd ~/ros2_contactile
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

如果只使用自研 Python 串口驱动，不需要原厂 PTSDK：

```bash
colcon build \
  --packages-select papillarray_interfaces papillarray_serial_driver \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

构建原厂 C++ 驱动前，需要从已获授权的 Contactile SDK 中提供 x86_64
`libPTSDK.a`。静态库不随 Git 仓库分发，可以复制到
`papillarray_ros2_v2/lib/libPTSDK.a`，或者显式指定路径：

```bash
colcon build \
  --packages-select papillarray_interfaces papillarray_ros2_v2 \
  --cmake-args \
    -DPython3_EXECUTABLE=/usr/bin/python3 \
    -DPTSDK_LIBRARY=/absolute/path/to/libPTSDK.a
source install/setup.bash
```

如果静态库缺失，CMake 会给出明确错误。Python 串口驱动的构建和运行不受影响。

每次打开新终端都需要重新加载 ROS 2 和工作区环境：

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_contactile/install/setup.bash
```

## 选择驱动

### 自研 Python 串口驱动

默认使用 `/dev/ttyACM0`、115200 baud、2 个传感器和 500 Hz 采样率：

```bash
ros2 launch papillarray_serial_driver papillarray_serial.launch.py
```

自定义参数：

```bash
ros2 launch papillarray_serial_driver papillarray_serial.launch.py \
  com_port:=/dev/ttyACM1 \
  baud_rate:=115200 \
  n_sensors:=1 \
  sampling_rate:=500
```

该驱动会在运行中断线后自动重连，并在重连成功后重新设置采样率。

### 原厂 PTSDK C++ 驱动

默认使用 `/dev/ttyACM0`、9600 baud、2 个传感器和 500 Hz 采样率：

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py
```

自定义参数：

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  com_port:=/dev/ttyACM1 \
  baud_rate:=9600 \
  n_sensors:=1 \
  sampling_rate:=500
```

使用哪套驱动时，Controller 固件的串口波特率必须与 launch 参数一致。

原厂 SDK 的 Linux 日志存在生成 `000` 权限文件的问题，因此 C++ 节点禁用了 SDK 内置
日志。需要记录以滑移状态为主的时间序列 CSV 时，显式指定日志目录：

```bash
ros2 launch papillarray_ros2_v2 papillarray.launch.py \
  log_dir:=$HOME/contactile_logs
```

默认日志包含所有 pillar 的接触状态和 `slip_state`；增加
`csv_pillar_detail:=true` 后才会追加逐 pillar 位移和力。

## Topic 与消息

每个传感器发布一个独立 Topic：

```text
/hub_<hub_id>/sensor_<sensor_id>
```

默认配置会发布：

```text
/hub_0/sensor_0
/hub_0/sensor_1
```

消息类型为 `papillarray_interfaces/msg/SensorState`，包含：

- Controller 时间戳；
- 每根 pillar 的三维位移、三维力、接触状态和滑移状态；
- 传感器全局三维力与三维力矩；
- 摩擦估计、目标抓握力和滑移检测状态。

查看数据和发布频率：

```bash
ros2 topic echo /hub_0/sensor_0
ros2 topic hz /hub_0/sensor_0
```

## Service

| 服务 | 类型 | 说明 |
|------|------|------|
| `/hub_0/send_bias_request` | `papillarray_interfaces/srv/BiasRequest` | 执行零点偏置校准 |
| `/hub_0/start_slip_detection` | `papillarray_interfaces/srv/StartSlipDetection` | 启动滑移检测 |
| `/hub_0/stop_slip_detection` | `papillarray_interfaces/srv/StopSlipDetection` | 停止滑移检测 |

调用示例：

```bash
ros2 service call /hub_0/start_slip_detection \
  papillarray_interfaces/srv/StartSlipDetection "{}"

ros2 service call /hub_0/stop_slip_detection \
  papillarray_interfaces/srv/StopSlipDetection "{}"
```

执行 Bias 前必须确认所有传感器完全无负载，并在调用后约 2 s 内保持无负载：

```bash
ros2 service call /hub_0/send_bias_request \
  papillarray_interfaces/srv/BiasRequest "{}"
```

错误的带载 Bias 会把当前受力状态当作零点，导致后续测量产生系统性偏差。

## 常见问题

### 找不到串口

检查设备是否存在：

```bash
ls -l /dev/ttyACM*
```

如果设备存在但当前用户无权访问，请确认用户属于 `dialout` 组，并在修改组成员后重新登录。

### 收不到数据

依次检查：

1. Controller 是否已供电并通过 USB 连接；
2. `com_port` 是否指向正确设备；
3. launch 中的 `baud_rate` 是否与 Controller 固件一致；
4. `n_sensors` 是否与数据包中的实际传感器数量一致；
5. 是否有另一套驱动或进程正在占用同一个串口。

## 测试

构建后运行接口与自研驱动的离线测试：

```bash
colcon test --packages-select papillarray_interfaces papillarray_serial_driver
colcon test-result --verbose
```

测试不访问真实硬件，覆盖协议校验、多传感器解析、消息映射、控制命令和断线重连。

## 许可说明

`papillarray_ros2_v2` 包含经过兼容性修复的 Contactile PTSDK 头文件，但 Git 仓库不包含
原厂静态库。使用者需要自行提供已获授权的 `libPTSDK.a`；在公开发布或二次分发原厂文件前，
仍需要先确认 Contactile SDK 的许可条款。
