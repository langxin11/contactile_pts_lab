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
from pts_protocol_compare import (
    _ByteSequenceFilter,
    compare_rows,
    flatten_packet,
    parse_capture_packets,
)
from pts_protocol_compare_plot import build_slip_difference_matrix

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

    def test_flattens_type_5_and_type_6_to_sdk_log_columns(self) -> None:
        """只有厂商日志实际提供的滑动字段才参与后续逐帧对照。"""
        packet = ParsedPacket(
            packet_counter=1,
            timestamp_us=321,
            pillar_forces=[np.array([[1.0, 2.0, 3.0]])],
            pillar_displacements=[np.array([[0.1, 0.2, 0.3]])],
            global_forces=[np.array([4.0, 5.0, 6.0])],
            global_torques=[np.array([0.4, 0.5, 0.6])],
            pillar_slip_states=[np.array([3], dtype=np.int8)],
            pillar_friction_estimates=[np.array([0.72])],
            slip_detection_active=[True],
            reference_pillar_loaded=[True],
            sensor_friction_estimates=[0.68],
            target_grip_forces=[12.5],
        )

        row = flatten_packet(packet)

        self.assertEqual(row["S0_P0_slipState"], 3)
        self.assertEqual(row["S0_P0_FRIC"], 0.72)
        self.assertEqual(row["S0_isSDActive"], 1)
        self.assertEqual(row["S0_isRefLoaded"], 1)
        self.assertEqual(row["S0_FRIC"], 0.68)
        self.assertEqual(row["S0_TARGET_GRIP_N"], 12.5)


class ParseCapturePacketsTest(unittest.TestCase):
    def test_replays_raw_capture_and_extracts_packets(self) -> None:
        capture = b"noise" + _START + _build_packet_data() + _END + b"tail"

        packets = parse_capture_packets(capture)

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].timestamp_us, 123456)
        self.assertEqual(packets[0].global_forces[0][2], 6.0)


class SlipPlotDataTest(unittest.TestCase):
    def test_builds_matrix_for_sdk_visible_slip_fields(self) -> None:
        """绘图数据只包含 SDK 日志可交叉验证的滑动字段。"""
        protocol_rows = [
            {
                "T_us": 10,
                "S0_P0_slipState": 2,
                "S0_isSDActive": 1,
                "S0_isRefLoaded": 1,
                "S0_FRIC": 0.65,
                "S0_TARGET_GRIP_N": 12.0,
            },
            {
                "T_us": 20,
                "S0_P0_slipState": 3,
                "S0_isSDActive": 1,
                "S0_isRefLoaded": 1,
                "S0_FRIC": 0.70,
                "S0_TARGET_GRIP_N": 13.0,
            },
        ]
        sdk_rows = [
            {
                "T_us": "10",
                "S0_P0_slipState": "2",
                "S0_isSDActive": "1",
                "S0_isRefLoaded": "1",
                "S0_FRIC": "0.60",
            },
            {
                "T_us": "20",
                "S0_P0_slipState": "2",
                "S0_isSDActive": "1",
                "S0_isRefLoaded": "1",
                "S0_FRIC": "0.65",
            },
        ]

        timestamps, fields, differences, skipped_count = build_slip_difference_matrix(
            protocol_rows, sdk_rows
        )

        self.assertEqual(timestamps, [10, 20])
        self.assertEqual(fields, ["S0_FRIC", "S0_P0_slipState", "S0_isRefLoaded", "S0_isSDActive"])
        self.assertAlmostEqual(differences[0][0], 0.05)
        self.assertEqual(differences[1], [0.0, 1.0])
        self.assertEqual(skipped_count, 0)

    def test_skips_nonfinite_timestamps_before_plotting(self) -> None:
        """NaN/Inf 只舍弃对应时间戳，不能使整张图警告刷屏或失效。"""
        protocol_rows = [
            {"T_us": 10, "S0_FRIC": 0.6},
            {"T_us": 20, "S0_FRIC": float("inf")},
        ]
        sdk_rows = [{"T_us": "10", "S0_FRIC": "0.5"}, {"T_us": "20", "S0_FRIC": "0.6"}]

        timestamps, _fields, differences, skipped_count = build_slip_difference_matrix(
            protocol_rows, sdk_rows
        )

        self.assertEqual(timestamps, [10])
        self.assertAlmostEqual(differences[0][0], 0.1)
        self.assertEqual(skipped_count, 1)


class SdkHeartbeatFilterTest(unittest.TestCase):
    def test_filters_split_sdk_heartbeat_and_keeps_warning(self) -> None:
        """原厂 INF 心跳跨读取块出现时也不能泄漏到终端。"""
        sequence_filter = _ByteSequenceFilter(b"INF: Still sampling...\n")

        output = sequence_filter.feed(b"INF: Still sam")
        output += sequence_filter.feed(b"pling...\nWRN: keep\n")
        output += sequence_filter.finish()

        self.assertEqual(output, b"WRN: keep\n")


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
