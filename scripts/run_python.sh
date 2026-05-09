#!/bin/bash
set -euo pipefail

# 运行 Python 示例程序
# 用法: bash scripts/run_python.sh [script_name] [extra_args]
# 示例: bash scripts/run_python.sh quick_read

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON_WS="${PROJECT_ROOT}/python_ws"
VENV_PYTHON="${PYTHON_WS}/.venv/bin/python"

if [ ! -f "${VENV_PYTHON}" ]; then
    echo "错误: 未找到 Python 虚拟环境"
    echo "请先运行: bash scripts/setup.sh"
    exit 1
fi

SCRIPT_NAME="${1:-quick_read.py}"
shift || true

# 自动补全 .py 后缀
if [[ ! "${SCRIPT_NAME}" == *.py ]]; then
    SCRIPT_NAME="${SCRIPT_NAME}.py"
fi

SCRIPT_PATH="${PYTHON_WS}/${SCRIPT_NAME}"

if [ ! -f "${SCRIPT_PATH}" ]; then
    echo "错误: 未找到脚本 ${SCRIPT_PATH}"
    exit 1
fi

echo "运行 Python 脚本: ${SCRIPT_PATH}"
cd "${PYTHON_WS}"
"${VENV_PYTHON}" "${SCRIPT_PATH}" "$@"
