#!/usr/bin/env python3
"""纯 Python 串口读取入口的离线测试。"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
from typer.testing import CliRunner

# 仓库当前未把 python_ws 安装成包，测试时补上模块搜索路径即可复用脚本入口。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pts_protocol import ParsedPacket
from quick_read_serial import app, print_global_forces


class _PacketReader:
    """返回固定协议包，避免测试访问真实串口。"""

    def __init__(self, packet: ParsedPacket) -> None:
        self._packet = packet

    def read_packet(self) -> ParsedPacket:
        """返回固定协议包。

        Returns:
            测试构造的协议包。
        """
        return self._packet


def _packet() -> ParsedPacket:
    """构造包含一个传感器的最小协议包。

    Returns:
        可供读取入口消费的测试数据包。
    """
    return ParsedPacket(
        packet_counter=1,
        timestamp_us=123,
        pillar_forces=[np.empty((0, 3))],
        pillar_displacements=[np.empty((0, 3))],
        global_forces=[np.array([1.0, 2.0, 3.0])],
        global_torques=[np.array([0.1, 0.2, 0.3])],
    )


def test_print_global_forces_outputs_selected_sensor(capsys: pytest.CaptureFixture[str]) -> None:
    """纯协议入口应输出时间戳和 sensor frame 三轴力。"""
    print_global_forces(_PacketReader(_packet()), samples=1, sensor_index=0)

    output = capsys.readouterr().out
    assert "123" in output
    assert "1.0000" in output
    assert "2.0000" in output
    assert "3.0000" in output


def test_print_global_forces_rejects_missing_sensor() -> None:
    """请求数据包中不存在的传感器时应给出明确错误。"""
    with pytest.raises(ValueError, match="仅包含 1 个传感器"):
        print_global_forces(_PacketReader(_packet()), samples=1, sensor_index=1)


def test_cli_help_does_not_access_hardware() -> None:
    """CLI 帮助可离线执行，作为参数声明的最小回归测试。"""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--port" in result.stdout
    assert "--sensor" in result.stdout
