#!/usr/bin/env python3
"""真实抓包对照脚本的离线测试。"""

from __future__ import annotations

import pathlib
import struct
import sys
import unittest

import numpy as np

# 仓库当前未把 python_ws 安装成包，测试时补上模块搜索路径即可复用现有脚本布局。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pts_protocol import ParsedPacket
from pts_protocol_compare import compare_rows, flatten_packet, parse_capture_packets

_START = bytes([0x55, 0x66, 0x77, 0x88])
_END = bytes([0xAA, 0xBB, 0xCC, 0xDD])
_TYPE_HUB = 1
_TYPE_PILLAR = 3
_TYPE_GLOBAL = 4
_INDEX_SIZE = 2


def _with_checksum(payload: bytes) -> bytes:
    checksum = sum(payload) & 0xFFFF
    return payload + checksum.to_bytes(2, "little")


def _build_packet_data() -> bytes:
    hub_block = (7).to_bytes(4, "little") + (123456).to_bytes(8, "little")

    pillar_block = bytearray()
    pillar_block.extend((1).to_bytes(2, "little"))
    pillar_block.extend((4).to_bytes(2, "little"))
    pillar_block.extend((1).to_bytes(2, "little"))
    pillar_block.extend((4).to_bytes(2, "little"))
    pillar_block.extend((2).to_bytes(2, "little"))
    pillar_block.extend(struct.pack("<6f", 1.0, 2.0, 3.0, 0.1, 0.2, 0.3))

    global_block = bytearray()
    global_block.extend((1).to_bytes(2, "little"))
    global_block.extend((4).to_bytes(2, "little"))
    global_block.extend((2).to_bytes(2, "little"))
    global_block.extend(struct.pack("<6f", 4.0, 5.0, 6.0, 0.4, 0.5, 0.6))

    hub_offset = 13
    pillar_offset = hub_offset + len(hub_block)
    global_offset = pillar_offset + len(pillar_block)

    payload = bytearray()
    payload.append(_INDEX_SIZE)
    payload.extend(_TYPE_HUB.to_bytes(2, "little"))
    payload.extend(hub_offset.to_bytes(_INDEX_SIZE, "little"))
    payload.extend(_TYPE_PILLAR.to_bytes(2, "little"))
    payload.extend(pillar_offset.to_bytes(_INDEX_SIZE, "little"))
    payload.extend(_TYPE_GLOBAL.to_bytes(2, "little"))
    payload.extend(global_offset.to_bytes(_INDEX_SIZE, "little"))
    payload.extend(hub_block)
    payload.extend(pillar_block)
    payload.extend(global_block)
    return _with_checksum(bytes(payload))


class FlattenPacketTest(unittest.TestCase):
    def test_flattens_protocol_packet_to_sdk_like_columns(self) -> None:
        packet = ParsedPacket(
            packet_counter=1,
            timestamp_us=321,
            pillar_forces=[np.array([[1.0, 2.0, 3.0]])],
            pillar_displacements=[np.array([[0.1, 0.2, 0.3]])],
            global_forces=[np.array([4.0, 5.0, 6.0])],
            global_torques=[np.array([0.4, 0.5, 0.6])],
        )

        row = flatten_packet(packet)

        self.assertEqual(row["T_us"], 321)
        self.assertEqual(row["S0_P0_DX"], 0.1)
        self.assertEqual(row["S0_P0_FZ"], 3.0)
        self.assertEqual(row["S0_G_TX"], 0.4)
        self.assertEqual(row["S0_G_FY"], 5.0)


class ParseCapturePacketsTest(unittest.TestCase):
    def test_replays_raw_capture_and_extracts_packets(self) -> None:
        capture = b"noise" + _START + _build_packet_data() + _END + b"tail"

        packets = parse_capture_packets(capture)

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].timestamp_us, 123456)
        self.assertEqual(packets[0].global_forces[0][2], 6.0)


class CompareRowsTest(unittest.TestCase):
    def test_reports_zero_mismatch_for_equal_rows(self) -> None:
        protocol_rows = [
            {
                "T_us": 10,
                "S0_G_FX": 1.0,
                "S0_G_FY": 2.0,
            }
        ]
        sdk_rows = [
            {
                "T_us": "10",
                "S0_G_FX": "1.0",
                "S0_G_FY": "2.0",
                "Unused": "0",
            }
        ]

        summary, mismatches = compare_rows(protocol_rows, sdk_rows, abs_tol=1e-6)

        self.assertEqual(summary["matched_timestamp_count"], 1)
        self.assertEqual(summary["mismatch_count"], 0)
        self.assertEqual(mismatches, [])

    def test_reports_field_difference_above_tolerance(self) -> None:
        protocol_rows = [{"T_us": 10, "S0_G_FX": 1.0}]
        sdk_rows = [{"T_us": "10", "S0_G_FX": "1.2"}]

        summary, mismatches = compare_rows(protocol_rows, sdk_rows, abs_tol=0.01)

        self.assertEqual(summary["mismatch_count"], 1)
        self.assertEqual(summary["max_abs_diff_field"], "S0_G_FX")
        self.assertEqual(mismatches[0]["T_us"], 10)
        self.assertEqual(mismatches[0]["field"], "S0_G_FX")


if __name__ == "__main__":
    unittest.main()
