#!/usr/bin/env python3
"""旧协议模块入口的兼容性测试。"""

import pathlib
import sys

# python_ws 尚未作为脚本集合安装，兼容入口仍从工作区根目录加载。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from papillarray_pts.protocol import (
    ParsedPacket as InstalledParsedPacket,
    PTSProtocolReader as InstalledPTSProtocolReader,
    parse_packet as installed_parse_packet,
    verify_checksum as installed_verify_checksum,
)
from papillarray_serial_driver import (
    ParsedPacket as DriverParsedPacket,
    PTSProtocolReader as DriverPTSProtocolReader,
)

from pts_protocol import ParsedPacket, PTSProtocolReader, parse_packet, verify_checksum


def test_legacy_protocol_module_reexports_installed_implementation() -> None:
    """python_ws 的旧导入路径应指向共享核心包 papillarray_pts 与驱动导出的实现。"""
    assert PTSProtocolReader is InstalledPTSProtocolReader
    assert ParsedPacket is InstalledParsedPacket
    assert parse_packet is installed_parse_packet
    assert verify_checksum is installed_verify_checksum
    assert PTSProtocolReader is DriverPTSProtocolReader
    assert ParsedPacket is DriverParsedPacket
