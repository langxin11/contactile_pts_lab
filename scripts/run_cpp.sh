#!/bin/bash
set -euo pipefail

# 运行 C++ 示例程序
# 用法: bash scripts/run_cpp.sh [extra_args]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BINARY="${PROJECT_ROOT}/cpp_ws/build/minimal_reader"

if [ ! -f "${BINARY}" ]; then
    echo "错误: 未找到 ${BINARY}"
    echo "请先运行: bash scripts/setup.sh"
    exit 1
fi

echo "运行 C++ 程序: ${BINARY}"
"${BINARY}" "$@"
