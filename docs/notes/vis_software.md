# 可视化软件 (PTSVIS) 笔记

> 基于原厂手册 PTSVIS_2.1_MAN_MAR23 的中文总结。

---

## 1. 概述

PTSVIS 是原厂提供的 **Java GUI 可视化软件**，用于：
- 传感器安装后的基本功能验证
- 实时数据可视化演示
- 数据记录到 CSV

**注意**：该软件是 **Windows 可执行文件** (`PTSVIS_2.1.exe`)，在 Linux 上无法直接运行。Linux 用户应使用 C++ / Python / ROS2 SDK。

---

## 2. 文件位置

| 文件 | 路径 |
|------|------|
| 可执行文件 | `vendor/...` 原 U 盘 `SOFTWARE/VIS/PTSVIS_2.1.exe` |
| 配置文件 | `SOFTWARE/VIS/config.dat` |

---

## 3. GUI 功能分区

### 3.1 传感器可视化（顶视图）

- 左上角：SEN0 传感器；右上角：SEN1 传感器
- 每个柱显示为 2D 图形：
  - **灰色** = 未接触；**白色** = 已接触（阈值 0.2 N）
  - 十字准线表示柱顶位置，随 X/Y 位移移动
  - 灰色圆圈大小表示 Z 位移量
- 可点击 **Rotate** 按钮将传感器视图顺时针旋转 90°

### 3.2 数据显示区

可切换显示：
- **单柱 3D 位移**（文本或曲线）
- **单柱 3D 力**（文本或曲线）
- **全局 3D 力 + 全局 3D 力矩**（文本或曲线）

曲线颜色：
- X 轴 = 黄色
- Y 轴 = 绿色
- Z 轴 = 蓝色

### 3.3 滑动检测与摩擦显示

- 启动滑动检测后，柱体周围显示彩色圆环表示滑动状态
- 当前摩擦估计值显示在传感器对面

### 3.4 内部温度

- 显示在传感器可视化左下角

---

## 4. 控制功能

| 功能 | 操作 |
|------|------|
| 连接/断开串口 | 选择 COM 端口 → Connect / Disconnect |
| Bias 传感器 | 点击 Bias Sensors 按钮（快捷键显示在按钮旁） |
| 启动/停止滑动检测 | Start Slip Detection / Stop Slip Detection |
| 开始/停止记录 | Start Log / Stop and Save |
| 调整记录采样率 | 下拉选择（仅在非记录状态时可用） |
| 调整曲线 Y 轴范围 | Toggle Graph Y-Range 按钮 |

---

## 5. 日志文件

| 项目 | 说明 |
|------|------|
| 位置 | `VIS/Logs/`（与可执行文件同级） |
| 命名格式 | `LOG_YYMMDD_hhmmss.csv` |
| 格式 | CSV，ASCII 文本 |

### 日志数据列顺序

日志包含非常完整的数据，列顺序如下（以 S0 为例）：

| 列号 | 名称 | 说明 |
|------|------|------|
| 1 | `T_us` | 时间戳 (µs) |
| 2-4 | `S0_P0_DX/Y/Z` | 柱 0 位移 (mm) |
| 5-7 | `S0_P0_FX/Y/Z` | 柱 0 力 (N) |
| ... | ... | 柱 1~8 同上模式 |
| 53-55 | `S0_P8_FX/Y/Z` | 柱 8 力 |
| 56-58 | `S0_GG_FX/Y/Z` | 全局力 (N) |
| 59-61 | `S0_GG_TX/Y/Z` | 全局力矩 (N·mm) |
| 62 | `S0_isSDActive` | 滑动检测激活标志 |
| 63 | `S0_isRefLoad` | 参考柱加载标志 |
| 64-79 | `S0_P0~P8_isInContact/slipState` | 接触与滑动状态 |
| 80 | `S0_FrictionEst` | 摩擦估计 |
| 81+ | `S1_...` | 传感器 1 的相同结构 |

> 力矩参考点为**中心柱 P4 的当前顶端位置**。

---

## 6. Linux 替代方案

由于 PTSVIS 无 Linux 版本，建议：

1. **快速验证**：使用 `cpp_ws/minimal_reader` 或 `python_ws/quick_read` 打印数据
2. **实时可视化**：基于 Python (matplotlib/plotly) 或 ROS2 (rviz/rqt) 自行开发可视化
3. **数据记录**：SDK 的 `isLogging=True` 会生成与 PTSVIS 格式相同的 CSV
