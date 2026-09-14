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

command -v git >/dev/null 2>&1 || { echo "错误: 未找到 git"; exit 1; }
command -v g++ >/dev/null 2>&1 || { echo "错误: 未找到 g++，请安装 build-essential"; exit 1; }
command -v cmake >/dev/null 2>&1 || { echo "错误: 未找到 cmake"; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "错误: 未找到 uv，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

echo "  ✓ git, g++, cmake, uv 均已安装"

# ------------------------------------------------------------------
# 2. 初始化 ROS2 源码子模块
# ------------------------------------------------------------------
echo ""
echo "[2/5] 初始化 ROS2 源码子模块..."

cd "${PROJECT_ROOT}"
git submodule update --init --recursive

echo "  ✓ ROS2 源码子模块已就绪"

# ------------------------------------------------------------------
# 3. 编译 C++ 工作区
# ------------------------------------------------------------------
echo ""
echo "[3/5] 编译 C++ 工作区..."

cd "${PROJECT_ROOT}/cpp_ws"
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j"$(nproc)"

echo "  ✓ C++ 编译完成，可执行文件位于 cpp_ws/build/minimal_reader"

# ------------------------------------------------------------------
# 4. 初始化 Python 虚拟环境（完整环境包含原厂 cp310 wheel）
# ------------------------------------------------------------------
echo ""
echo "[4/5] 初始化 Python 虚拟环境（Python 3.10，包含两种读取方式）..."

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

# 同步完整依赖；纯串口方式也可单独执行 uv sync，不安装原厂 wheel。
echo "  正在同步 Python 依赖..."
uv sync --extra sdk --extra gui

if ! .venv/bin/python -c "import dearpygui" >/dev/null 2>&1; then
    echo "  ⚠ 未找到 Python 可视化依赖 DearPyGui"
    echo "     如需 GUI，请运行: cd python_ws && uv sync --extra gui"
fi

echo "  ✓ Python 环境就绪"
echo "     激活方式: source python_ws/.venv/bin/activate"

# ------------------------------------------------------------------
# 5. 编译 ROS2 工作区
# ------------------------------------------------------------------
echo ""
echo "[5/5] 编译 ROS2 工作区..."

if command -v colcon >/dev/null 2>&1; then
    cd "${PROJECT_ROOT}/ros2_ws"
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
echo "  3. 运行 Python: bash scripts/run_python.sh quick_read_serial"
echo "  4. 运行 ROS2:  bash scripts/run_ros2.sh --mock"
echo "                bash scripts/run_ros2.sh --real"
echo "  5. 可视化 GUI: bash scripts/run_python.sh pts_vis（需 gui extra）"
echo ""
