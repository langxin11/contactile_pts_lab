#!/usr/bin/env python3
"""兼容旧入口，协议实现已集中到 ROS 2 可安装模块。"""

from papillarray_serial_driver.protocol import (
    ParsedPacket,
    PTSProtocolReader,
    parse_packet,
    verify_checksum,
)

__all__ = ["PTSProtocolReader", "ParsedPacket", "parse_packet", "verify_checksum"]
