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
├── ros2_ws/                  ROS2 实验区 (colcon，src 为 Git submodule)
├── config/                   统一配置 (YAML)
├── scripts/                  一键运行脚本
├── udev/                     udev 规则
├── data/                     实验数据归档
├── models/                   3D STEP 模型
└── docs/                     手册 + 笔记
```

## 快速开始

```bash
# 首次克隆时同时初始化 ROS2 源码子模块
git clone --recurse-submodules git@github.com:langxin11/contactile_pts_lab.git

# 已有工作副本只需执行一次
git submodule update --init --recursive

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

`pts_protocol_compare.py` 提供串口中继与离线协议解析能力，让两种实现读取同一批字节，
不作为日常读取入口。

### 质量—法向压力准确性实验

测量与绘图已解耦。默认配置会在测量结束并释放串口后，以独立子进程自动调用绘图钩子：

```bash
cd python_ws
uv run --extra experiment python force_accuracy_measure.py \
  --config ../config/force_accuracy.yaml
```

如只采集 CSV，把 YAML 中的 `plot.auto` 改为 `false`，然后运行：

```bash
uv run --extra measurement python force_accuracy_measure.py \
  --config ../config/force_accuracy.yaml
```

每次测量都会创建独立的时间戳会话目录。已有 CSV 可以随时单独重绘，例如：

```bash
uv run --extra plot python force_accuracy_plot.py \
  ../data/force_accuracy/20260720_120000_000000/measurements.csv \
  --config ../config/force_accuracy.yaml
```

测量脚本从 YAML 读取串口、传感器和稳定判据。真实串口字节会被中继给官方 SDK，
同时原样保存为 `capture_raw.bin`；测量结束后，自研串口解析器按相同的控制器时间戳稳定窗口
离线计算第二组结果，因此两条链路比较的是同一次放置、同一批数据，而不是两次独立实验。
`measurements.csv` 同时保存 SDK、自研协议及两者差值，图中以圆点表示 `Official SDK`，
空心方块表示 `Serial protocol`。

每个质量点都会原子更新 CSV。输入 `q` 并回车后，脚本先保存数据、释放串口，再按
`plot.auto` 调用绘图脚本；绘图失败只会输出警告，不影响 CSV。原厂 SDK 的
`INF: Still sampling...` 会被过滤，其他警告和错误保留。绘图采用 SciencePlots 的 IEEE
单栏样式。

若发现质量放错或物体放置错误，可在下一次输入或放置确认时输入 `u` 撤销最近一条有效记录，
或输入 `d <记录号>`（如 `d 3`）逻辑排除指定记录。CSV 会保留原始数值并写入 `included=false`

默认测量顺序由 YAML 的 `measurement.target_masses_g` 决定；数组元素是电子秤的实际质量，
重复元素表示在该质量下重复测量。临时补点或组合质量可使用 `--interactive`，在终端逐项输入。

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
