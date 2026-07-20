# Contactile PTS Lab

Ubuntu 24.04 x86_64 环境下 Contactile PTS（PapillArray）触觉传感器的 C++ / Python / ROS2 实验环境。

## 硬件

| 设备 | 说明 |
|------|------|
| 传感器 | Contactile PTS（型号见传感器标签） |
| 连接 | USB / 串口 |
| 主机 | Ubuntu 24.04 x86_64 |

## 目录结构

```
├── vendor/C++LIN/            原厂 C++ SDK 只读副本
├── vendor/PythonLIN/         原厂 Python wheel 只读副本
├── vendor/ROS2/              原厂 ROS2 包只读副本
├── cpp_ws/                   C++ 实验区
├── python_ws/                Python 实验区 (uv + Python 3.10)
├── ros2_ws/                  ROS2 实验区 (colcon)
├── config/                   统一配置 (YAML)
├── scripts/                  一键运行脚本
├── udev/                     udev 规则
├── data/                     实验数据归档
├── models/                   3D STEP 模型
└── docs/                     手册 + 笔记
```

## 快速开始

```bash
# 1. 一键初始化（编译 C++、安装 Python 环境、编译 ROS2）
bash scripts/setup.sh

# 2. 检查硬件连接
bash scripts/check_usb.sh

# 3. 选择链路运行

# C++
bash scripts/run_cpp.sh

# Python：纯串口协议（默认，不依赖原厂 wheel）
bash scripts/run_python.sh quick_read_serial

# Python：原厂 wheel
bash scripts/run_python.sh quick_read_sdk

# ROS2
bash scripts/run_ros2.sh --real
```

## Python 两种读取方式

```bash
cd python_ws

# 纯串口协议：不安装原厂 wheel
uv sync
uv run python quick_read_serial.py --help

# 原厂 SDK：安装 cp310 wheel
uv sync --extra sdk
uv run --extra sdk python quick_read_sdk.py --help

# GUI 同时依赖原厂 wheel
uv sync --extra gui
uv run --extra gui python pts_vis.py --help
```

`pts_protocol_compare.py` 用于让两种实现读取同一批字节并进行对照验证，不作为日常读取入口。

## 三条链路对比

| | C++ | Python | ROS2 |
|------|-----|--------|------|
| 入口 | `cpp_ws/src/minimal_reader.cpp` | `quick_read_serial.py` 或 `quick_read_sdk.py` | ROS2 topic |
| SDK | `libPTSDK.a` + 头文件 | 纯 `pyserial` 协议或 `cp310` wheel | 同 C++ |
| Python 版本 | — | 纯串口 >=3.10；wheel 为 3.10 | 系统 3.12 |
| 波特率 | 9600 | 115200 | 9600 |
| 适用场景 | 最低延迟, 嵌入式部署 | 快速原型, 数据分析 | 机器人系统集成 |

## 参数速查

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `port` | `/dev/ttyACM0` | 串口设备 |
| `baud_rate` | 9600 (C++/ROS2) / 115200 (Python) | 波特率 |
| `sensor_count` | 1 | 连接的传感器数量 |
| `bias_on_startup` | true | 启动时自动零点校准 |

## 串口权限

```bash
sudo usermod -aG dialout $USER
# 注销并重新登录生效
```

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 连接失败 | 设备未插入或权限不足 | `ls /dev/ttyACM*` + 检查 dialout 组 |
| Python import 失败 | 未激活 venv 或 wheel 未安装 | `source python_ws/.venv/bin/activate` |
| 无负载读数不为零 | Bias 时有负载 | 重启节点或调用 bias 服务 |
| colcon 找不到 catkin_pkg | uv python 干扰 | 加 `-DPython3_EXECUTABLE=/usr/bin/python3` |
