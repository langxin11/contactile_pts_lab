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

# Python
bash scripts/run_python.sh quick_read

# ROS2
bash scripts/run_ros2.sh --real
```

## 三条链路对比

| | C++ | Python | ROS2 |
|------|-----|--------|------|
| 入口 | `cpp_ws/src/minimal_reader.cpp` | `python_ws/quick_read.py` | ROS2 topic |
| SDK | `libPTSDK.a` + 头文件 | `cp310` wheel | 同 C++ |
| Python 版本 | — | 3.10 (wheel 约束) | 系统 3.12 |
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
