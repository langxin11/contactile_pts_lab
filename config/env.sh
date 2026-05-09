#!/bin/bash
# Contactile PTS Lab 环境变量
# 使用: source config/env.sh

# 项目根目录
export CONTACTILE_PTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# C++ SDK 路径
export CONTACTILE_CPP_INCLUDE="${CONTACTILE_PTS_ROOT}/vendor/C++LIN/Include"
export CONTACTILE_CPP_LIB="${CONTACTILE_PTS_ROOT}/vendor/C++LIN/Library"

# Python 虚拟环境 (如果存在)
if [ -d "${CONTACTILE_PTS_ROOT}/python_ws/.venv" ]; then
    export VIRTUAL_ENV="${CONTACTILE_PTS_ROOT}/python_ws/.venv"
    export PATH="${VIRTUAL_ENV}/bin:${PATH}"
fi

# ROS2 工作空间 (如果已编译)
if [ -f "${CONTACTILE_PTS_ROOT}/ros2_ws/install/setup.bash" ]; then
    source "${CONTACTILE_PTS_ROOT}/ros2_ws/install/setup.bash"
fi

echo "[env.sh] Contactile PTS Lab 环境已加载"
echo "  ROOT: ${CONTACTILE_PTS_ROOT}"
echo "  C++ Include: ${CONTACTILE_CPP_INCLUDE}"
echo "  C++ Lib: ${CONTACTILE_CPP_LIB}"
