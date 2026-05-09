#!/bin/bash
set -euo pipefail

# 运行 ROS2 节点
# 用法:
#   bash scripts/run_ros2.sh --mock     模拟模式（无硬件）
#   bash scripts/run_ros2.sh --real     真实硬件模式
#   bash scripts/run_ros2.sh --vis      启动 Python SDK 可视化 GUI

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 加载 ROS2 环境
if [ -f "${PROJECT_ROOT}/ros2_ws/install/setup.bash" ]; then
    # ROS2/colcon 的 setup 脚本会读取未预先定义的环境变量，临时关闭 nounset 避免误报。
    set +u
    source "${PROJECT_ROOT}/ros2_ws/install/setup.bash"
    set -u
else
    echo "错误: 未找到 ros2_ws/install/setup.bash"
    echo "请先运行: bash scripts/setup.sh"
    exit 1
fi

MODE="${1:-}"
if [ "$#" -gt 0 ]; then
    shift
fi

case "${MODE}" in
    --mock)
        echo "启动 ROS2 模拟节点..."
        ros2 topic pub --rate 50 /hub_0/sensor_0 sensor_interfaces/msg/SensorState \
            "{header: {frame_id: 'hub_0/sensor_0'}, tus: 0, pillars: [{id: 0, dx: 0.0, dy: 0.0, dz: 0.0, fx: 0.0, fy: 0.0, fz: 0.0, in_contact: false, slip_state: 0}], gfx: 0.0, gfy: 0.0, gfz: 0.0, gtx: 0.0, gty: 0.0, gtz: 0.0, friction_est: -1.0, target_grip_force: -1.0, is_sd_active: false, is_ref_loaded: false, is_contact: false}"
        ;;
    --real)
        echo "启动 ROS2 真实硬件节点..."
        ros2 launch papillarray_ros2_v2 papillarray.launch.py
        ;;
    --vis)
        echo "启动 Python SDK 可视化 GUI..."
        bash "${PROJECT_ROOT}/scripts/run_python.sh" pts_vis "$@"
        ;;
    *)
        echo "用法: bash scripts/run_ros2.sh [--mock | --real | --vis]"
        exit 1
        ;;
esac
