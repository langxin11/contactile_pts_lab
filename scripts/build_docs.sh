#!/bin/bash
set -euo pipefail

# Contactile PTS Lab 文档编译脚本
# 用法: bash scripts/build_docs.sh [--serve]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCS_DIR="${PROJECT_ROOT}/docs"
BUILD_DIR="${DOCS_DIR}/_build/html"

echo "========================================"
echo "Contactile PTS Lab 文档编译 (Sphinx)"
echo "========================================"

cd "${PROJECT_ROOT}/python_ws"

# 确保 Sphinx 依赖可用并编译
uv run --group dev sphinx-build -b html "${DOCS_DIR}" "${BUILD_DIR}"

echo ""
echo "  ✓ 文档编译成功！本地浏览入口:"
echo "    file://${BUILD_DIR}/index.html"
echo ""

if [[ "${1:-}" == "--serve" ]]; then
    echo "启动本地文档预览服务器 (http://localhost:8000)..."
    uv run python -m http.server 8000 --directory "${BUILD_DIR}"
fi
