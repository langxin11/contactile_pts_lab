#!/bin/bash
set -euo pipefail

# 运行 ROS2 节点
# 用法:
#   bash scripts/run_ros2.sh --mock     模拟模式（无硬件）
#   bash scripts/run_ros2.sh --real     真实硬件模式

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 加载 ROS2 环境
if [ -f "${PROJECT_ROOT}/ros2_ws/install/setup.bash" ]; then
    source "${PROJECT_ROOT}/ros2_ws/install/setup.bash"
else
    echo "错误: 未找到 ros2_ws/install/setup.bash"
    echo "请先运行: bash scripts/setup.sh"
    exit 1
fi

MODE="${1:-}"

case "${MODE}" in
    --mock)
        echo "启动 ROS2 模拟节点..."
        ros2 run contactile_driver mock_publisher
        ;;
    --real)
        echo "启动 ROS2 真实硬件节点..."
        ros2 launch contactile_driver contactile.launch.py
        ;;
    *)
        echo "用法: bash scripts/run_ros2.sh [--mock | --real]"
        exit 1
        ;;
esac
