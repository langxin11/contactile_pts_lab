#!/bin/bash
set -euo pipefail

# Contactile PTS Lab 一键初始化脚本
# 用法: bash scripts/setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "========================================"
echo "Contactile PTS Lab 初始化"
echo "========================================"

# ------------------------------------------------------------------
# 1. 检查系统依赖
# ------------------------------------------------------------------
echo ""
echo "[1/4] 检查系统依赖..."

command -v g++ >/dev/null 2>&1 || { echo "错误: 未找到 g++，请安装 build-essential"; exit 1; }
command -v cmake >/dev/null 2>&1 || { echo "错误: 未找到 cmake"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "错误: 未找到 uv，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

echo "  ✓ g++, cmake, uv 均已安装"

# ------------------------------------------------------------------
# 2. 编译 C++ 工作区
# ------------------------------------------------------------------
echo ""
echo "[2/4] 编译 C++ 工作区..."

cd "${PROJECT_ROOT}/cpp_ws"
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j"$(nproc)"

echo "  ✓ C++ 编译完成，可执行文件位于 cpp_ws/build/minimal_reader"

# ------------------------------------------------------------------
# 3. 初始化 Python 虚拟环境 (Python 3.10，适配 wheel)
# ------------------------------------------------------------------
echo ""
echo "[3/4] 初始化 Python 虚拟环境 (Python 3.10)..."

cd "${PROJECT_ROOT}/python_ws"

# 创建虚拟环境（如果已存在则复用，避免重复初始化时交互确认覆盖）
if [ -x ".venv/bin/python" ]; then
    echo "  已发现 python_ws/.venv，跳过虚拟环境创建"
else
    # 安装 Python 3.10（如果系统没有）
    if ! uv python find 3.10 >/dev/null 2>&1; then
        echo "  正在通过 uv 安装 Python 3.10..."
        uv python install 3.10
    fi

    uv venv --python 3.10 .venv
fi

# 安装原厂 wheel
echo "  正在安装 ptsdk_cxx_pybind..."
uv pip install --python .venv/bin/python "${PROJECT_ROOT}/vendor/PythonLIN/ptsdk_cxx_pybind-1.0.2-cp310-cp310-linux_x86_64.whl"

echo "  ✓ Python 环境就绪"
echo "     激活方式: source python_ws/.venv/bin/activate"

# ------------------------------------------------------------------
# 4. 编译 ROS2 工作区
# ------------------------------------------------------------------
echo ""
echo "[4/4] 编译 ROS2 工作区..."

if command -v colcon >/dev/null 2>&1; then
    cd "${PROJECT_ROOT}/ros2_ws"
    # 创建 src 中的 symlink（如果不存在）
    if [ ! -L "${PROJECT_ROOT}/ros2_ws/src/ros2_contactile_sensors" ] && [ ! -d "${PROJECT_ROOT}/ros2_ws/src/ros2_contactile_sensors" ]; then
        ln -s "${PROJECT_ROOT}/vendor/ROS2/ros2_contactile_sensors" "${PROJECT_ROOT}/ros2_ws/src/ros2_contactile_sensors"
    fi
    colcon build --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
    echo "  ✓ ROS2 编译完成"
else
    echo "  ⚠ 未找到 colcon，跳过 ROS2 编译"
    echo "     如需 ROS2，请先安装: sudo apt install python3-colcon-common-extensions"
fi

# ------------------------------------------------------------------
echo ""
echo "========================================"
echo "初始化完成！"
echo "========================================"
echo ""
echo "后续步骤:"
echo "  1. 检查硬件:   bash scripts/check_usb.sh"
echo "  2. 运行 C++:   bash scripts/run_cpp.sh"
echo "  3. 运行 Python: bash scripts/run_python.sh"
echo "  4. 运行 ROS2:  bash scripts/run_ros2.sh --mock"
echo "                bash scripts/run_ros2.sh --real"
echo ""
