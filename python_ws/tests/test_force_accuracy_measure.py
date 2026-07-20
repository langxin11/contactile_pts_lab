#!/usr/bin/env python3
"""质量—压力测量脚本的离线测试。"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np
import pytest
from typer.testing import CliRunner

# 测试只加载计算与 CLI 声明，不导入官方 SDK，也不访问真实串口。
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from force_accuracy_measure import (
    SDK_HEARTBEAT_MESSAGE,
    Measurement,
    _ByteSequenceFilter,
    analyze_window,
    app,
    enrich_protocol_measurements,
    load_experiment_config,
    parse_mass_input,
    run_plot_hook,
)


def test_parse_mass_input_accepts_user_value() -> None:
    """质量应由用户在每轮提示中自由输入。"""
    assert parse_mass_input(" 125.5 ") == pytest.approx(125.5)


def test_parse_mass_input_recognizes_quit() -> None:
    """大小写 q 都应结束记录过程。"""
    assert parse_mass_input("q") is None
    assert parse_mass_input(" Q ") is None


def test_parse_mass_input_rejects_negative_value() -> None:
    """负质量没有物理意义，应在连接硬件前拒绝。"""
    with pytest.raises(ValueError, match="非负"):
        parse_mass_input("-1")


def test_analyze_window_returns_mean_noise_and_drift() -> None:
    """稳定性指标应使用控制器时间戳计算，避免主机调度抖动影响结果。"""
    timestamps_us = np.array([0.0, 1_000_000.0, 2_000_000.0])
    forces_n = np.array([1.0, 1.01, 1.02])

    mean_n, std_n, drift_n_per_sec = analyze_window(timestamps_us, forces_n)

    assert mean_n == pytest.approx(1.01)
    assert std_n == pytest.approx(0.01)
    assert drift_n_per_sec == pytest.approx(0.01)


def test_load_experiment_config_resolves_relative_output(tmp_path: pathlib.Path) -> None:
    """相对输出目录应以 YAML 所在目录为基准，而不是依赖启动目录。"""
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        """connection:
  port: /dev/test
  baud_rate: 115200
  rate_hz: 500
  sensor_index: 1
measurement:
  normal_axis: z
  compression_sign: -1
  target_masses_g: [39, 39, 100]
stability:
  window_sec: 2.0
  timeout_sec: 15.0
  std_threshold_n: 0.02
  drift_threshold_n_per_sec: 0.01
output:
  directory: results
plot:
  auto: false
""",
        encoding="utf-8",
    )

    config = load_experiment_config(config_path)

    assert config.port == "/dev/test"
    assert config.sensor_index == 1
    assert config.compression_sign == -1
    assert config.target_masses_g == (39.0, 39.0, 100.0)
    assert config.output_dir == tmp_path / "results"
    assert config.auto_plot is False


def test_enrich_protocol_measurements_uses_same_timestamp_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """自研协议必须只统计 SDK 稳定窗口内的同一批控制器帧。"""
    packets = [
        type("Packet", (), {"timestamp_us": 99, "global_forces": [np.array([0.0, 0.0, 9.0])]})(),
        type("Packet", (), {"timestamp_us": 100, "global_forces": [np.array([0.0, 0.0, 1.0])]})(),
        type("Packet", (), {"timestamp_us": 200, "global_forces": [np.array([0.0, 0.0, 3.0])]})(),
        type("Packet", (), {"timestamp_us": 201, "global_forces": [np.array([0.0, 0.0, 9.0])]})(),
    ]
    monkeypatch.setattr("force_accuracy_measure.parse_capture_packets", lambda payload: packets)
    capture_path = tmp_path / "capture_raw.bin"
    capture_path.write_bytes(b"raw")
    measurement = Measurement(
        record_id=1,
        timestamp="2026-07-20T12:00:00+08:00",
        sensor_index=0,
        mass_g=200.0,
        expected_force_n=1.96133,
        raw_normal_force_n=2.0,
        measured_pressure_n=2.0,
        std_force_n=0.1,
        drift_n_per_sec=0.0,
        error_n=0.03867,
        relative_error_percent=1.97,
        sample_count=2,
        settle_time_sec=2.0,
        window_start_us=100,
        window_end_us=200,
    )

    enriched = enrich_protocol_measurements([measurement], capture_path, 0, 2, 1)[0]

    assert enriched.protocol_measured_pressure_n == pytest.approx(2.0)
    assert enriched.protocol_std_force_n == pytest.approx(np.sqrt(2.0))
    assert enriched.sdk_protocol_diff_n == pytest.approx(0.0)
    assert enriched.protocol_sample_count == 2


def test_sdk_heartbeat_filter_handles_split_chunks() -> None:
    """原厂心跳即使跨管道读取块，也应被移除且不吞掉其他日志。"""
    sequence_filter = _ByteSequenceFilter(SDK_HEARTBEAT_MESSAGE)

    output = sequence_filter.feed(b"prompt> INF: Still sam")
    output += sequence_filter.feed(b"pling...\nWRN: keep this\n")
    output += sequence_filter.finish()

    assert output == b"prompt> WRN: keep this\n"


def test_sdk_stdout_filter_preserves_prompt_and_warning() -> None:
    """文件描述符过滤应只删除心跳，并在结束后恢复 stdout。"""
    code = (
        "import os; "
        "from force_accuracy_measure import _SdkStdoutFilter; "
        "f = _SdkStdoutFilter(); f.start(); "
        r"os.write(1, b'INF: Still sampling.'); "
        "print('prompt> ', end='', flush=True); "
        r"os.write(1, b'..\nWRN: keep\n'); "
        "f.stop(); print('restored')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=pathlib.Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "INF: Still sampling" not in result.stdout
    assert result.stdout == "prompt> WRN: keep\nrestored\n"


def test_plot_hook_failure_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """绘图子进程失败只能返回 False，不能破坏已保存的测量流程。"""
    monkeypatch.setattr(
        "force_accuracy_measure.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=[], returncode=1),
    )

    succeeded = run_plot_hook(tmp_path / "measurements.csv", tmp_path / "config.yaml")

    assert succeeded is False


def test_cli_help_does_not_import_sdk_or_access_hardware() -> None:
    """CLI 参数可在无传感器环境离线检查。"""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--config" in result.stdout
    assert "--interactive" in result.stdout
