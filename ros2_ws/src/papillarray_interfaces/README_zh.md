# papillarray_interfaces

PapillArray 触觉传感器的 ROS 2 接口定义包，包含自定义消息 (`.msg`) 和服务 (`.srv`)。

## 包说明

本包是纯接口层，不包含任何运行时节点。它定义了 `papillarray_ros2_v2` 驱动节点所使用的数据类型，其他需要与传感器数据交互的 ROS 2 包也应依赖本包。

## 自定义消息

### PillarState (`msg/PillarState.msg`)

单个触点的状态信息。PapillArray 传感器表面由多个弹性柱状体 (pillar) 组成，每个 pillar 可独立感知三维位移和三维力。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int64` | 触点编号 |
| `dx` | `float32` | X 方向位移 |
| `dy` | `float32` | Y 方向位移 |
| `dz` | `float32` | Z 方向位移 |
| `fx` | `float32` | X 方向力 |
| `fy` | `float32` | Y 方向力 |
| `fz` | `float32` | Z 方向力（法向力） |
| `in_contact` | `bool` | 是否处于接触状态 |
| `slip_state` | `int64` | 滑动状态 |

**滑动状态常量**（定义于 `PTSDKConstants.h`）：

| 值 | 宏定义 | 含义 |
|----|--------|------|
| `-2` | `INELIGIBLE` | 滑动检测启动时该 pillar 未接触 |
| `-1` | `LOST_CONTACT` | 原先在接触，现已失去接触 |
| `1` | `CONTACT_AT_START` | 滑动检测启动时处于接触 |
| `2` | `TLOADING` | 正在承受切向加载 |
| `3` | `SLIPPED` | 已发生滑动 |

### SensorState (`msg/SensorState.msg`)

单个传感器的完整状态，包含所有 pillar 的数据以及全局力/力矩信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| `header` | `std_msgs/Header` | 标准 ROS 消息头（时间戳和坐标系） |
| `tus` | `int64` | 传感器时间戳（微秒） |
| `pillars` | `PillarState[]` | 所有触点的状态数组 |
| `gfx` | `float32` | 全局合力 X 分量 |
| `gfy` | `float32` | 全局合力 Y 分量 |
| `gfz` | `float32` | 全局合力 Z 分量（法向合力） |
| `gtx` | `float32` | 全局合力矩 X 分量 |
| `gty` | `float32` | 全局合力矩 Y 分量 |
| `gtz` | `float32` | 全局合力矩 Z 分量 |
| `friction_est` | `float32` | 摩擦系数估计值（无估计时为 -1） |
| `target_grip_force` | `float32` | 目标抓取力（无摩擦估计时为 -1） |
| `is_sd_active` | `bool` | 滑动检测是否激活 |
| `is_ref_loaded` | `bool` | 参考载荷是否已加载 |
| `is_contact` | `bool` | 传感器是否与物体接触（任一 pillar 接触即为 true） |

## 自定义服务

### BiasRequest (`srv/BiasRequest.srv`)

发送偏置请求，用于传感器零位校准。

- **请求**：无
- **响应**：`bool result` — 操作是否成功

### StartSlipDetection (`srv/StartSlipDetection.srv`)

启动滑动检测功能。激活后传感器将持续监测各 pillar 的滑动状态，结果反映在 `PillarState.slip_state` 字段中。

- **请求**：无
- **响应**：`bool result` — 操作是否成功

### StopSlipDetection (`srv/StopSlipDetection.srv`)

停止滑动检测功能。

- **请求**：无
- **响应**：`bool result` — 操作是否成功

## 服务名称

驱动节点 (`papillarray_ros2_v2`) 会在以下命名空间暴露服务（其中 `{hub_id}` 为集线器 ID，默认为 `0`）：

- `/hub_{hub_id}/send_bias_request` — 偏置请求
- `/hub_{hub_id}/start_slip_detection` — 启动滑动检测
- `/hub_{hub_id}/stop_slip_detection` — 停止滑动检测

## 依赖

- `std_msgs` — ROS 2 标准消息
- `rosidl_default_generators` — 接口代码生成工具
- `ament_cmake` — 构建系统

## 构建

本包作为 ROS 2 工作空间的一部分构建：

```bash
cd ros2_ws
colcon build --packages-select papillarray_interfaces
source install/setup.bash
```
