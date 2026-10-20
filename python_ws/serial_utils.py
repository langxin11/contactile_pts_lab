#!/usr/bin/env python3
"""串口设备节点的等待工具。

USB 插入后控制器固件启动 + 枚举需要 1~2 s（实测见
docs/notes/usb_connection_timing.md），入口脚本若在节点出现前启动会直接失败，
统一在此提供有界等待。
"""

from __future__ import annotations

import os
import time

# 实测插入到 /dev/ttyACM0 出现约 1~2 s，5 s 默认值给足裕量且超时代价可控。
DEFAULT_WAIT_SEC = 5.0
# 轮询间隔 50 ms：对枚举延迟的感知误差远小于固件启动时间本身。
DEVICE_POLL_SEC = 0.05


def wait_for_serial_device(port: str, wait_sec: float) -> bool:
    """等待串口设备节点出现，覆盖 USB 热插拔后的枚举延迟。

    Args:
        port: 串口设备路径，如 /dev/ttyACM0 或 udev 软链接 /dev/contactile_pts。
        wait_sec: 最长等待时间，单位 s；小于等于 0 时只检查一次不等待。

    Returns:
        True 表示节点已出现；False 表示等待超时仍不存在。
    """
    deadline = time.monotonic() + max(wait_sec, 0.0)
    while True:
        if os.path.exists(port):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(DEVICE_POLL_SEC)
