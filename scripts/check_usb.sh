#!/bin/bash
set -euo pipefail

# 检查 Contactile PTS 硬件连接

echo "========================================"
echo "Contactile PTS 硬件连接检查"
echo "========================================"
echo ""

# 1. 检查串口设备
echo "[1/3] 检查串口设备..."
if ls /dev/ttyACM* 1>/dev/null 2>&1; then
    echo "  ✓ 发现串口设备:"
    ls -la /dev/ttyACM* | sed 's/^/    /'
else
    echo "  ✗ 未找到 /dev/ttyACM* 设备"
    echo "    请检查:"
    echo "      - 传感器是否通过 USB 连接到主机"
    echo "      - USB 线是否正常"
    exit 1
fi

# 2. 检查用户权限
echo ""
echo "[2/3] 检查用户权限..."
CURRENT_USER="${USER:-$(id -un)}"
if groups "${CURRENT_USER}" | grep -q '\bdialout\b'; then
    echo "  ✓ 用户 ${CURRENT_USER} 已在 dialout 组"
else
    echo "  ✗ 用户 ${CURRENT_USER} 不在 dialout 组"
    echo "    解决方法: sudo usermod -aG dialout ${CURRENT_USER}"
    echo "    然后注销并重新登录"
    exit 1
fi

# 3. 检查 udev 规则
echo ""
echo "[3/3] 检查 udev 规则..."
if [ -f "/etc/udev/rules.d/99-contactile-pts.rules" ]; then
    echo "  ✓ udev 规则已安装"
else
    echo "  ⚠ udev 规则未安装"
    echo "    安装方法: sudo cp udev/99-contactile-pts.rules /etc/udev/rules.d/"
    echo "              sudo udevadm control --reload-rules && sudo udevadm trigger"
fi

echo ""
echo "========================================"
echo "检查完成"
echo "========================================"
