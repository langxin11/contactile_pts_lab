#!/usr/bin/env python3
"""噪声功率谱分析工具的离线测试。"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from noise_psd_analysis import (
    app,
    choose_cutoff_from_cumulative,
    infer_sampling_rate,
    welch_psd,
)


def test_infers_uniform_sampling_rate() -> None:
    """时间戳中位间隔应转换为 Hz，并标记均匀采样。"""
    timestamps_us = np.arange(100, dtype=np.float64) * 1_000.0

    sampling_rate_hz, uniform = infer_sampling_rate(timestamps_us)

    assert sampling_rate_hz == pytest.approx(1_000.0)
    assert uniform is True


def test_welch_psd_detects_sine_peak() -> None:
    """功率谱主峰应落在输入正弦波频率附近。"""
    sampling_rate_hz = 1_000.0
    time_s = np.arange(4_096, dtype=np.float64) / sampling_rate_hz
    signal = np.sin(2.0 * np.pi * 50.0 * time_s)

    frequencies, psd = welch_psd(signal, sampling_rate_hz, nperseg=1_024)

    peak_frequency_hz = frequencies[int(np.argmax(psd))]
    assert peak_frequency_hz == pytest.approx(50.0, abs=1.0)


def test_selects_highest_cutoff_meeting_removal_target() -> None:
    """候选频率应是仍能移除目标能量的最高频点。"""
    frequencies = np.array([0.0, 1.0, 2.0, 3.0])
    psd = np.ones(4)

    cutoff_hz = choose_cutoff_from_cumulative(psd, frequencies, 50.0)

    assert cutoff_hz == pytest.approx(2.0)


def test_rejects_invalid_removal_target() -> None:
    """噪声移除占比必须是有效百分比。"""
    with pytest.raises(ValueError, match="target_removed_pct"):
        choose_cutoff_from_cumulative(np.ones(2), np.arange(2), 0.0)


def test_cli_help_runs_without_input_data() -> None:
    """CLI 帮助不应读取 CSV 或生成图片。"""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "CSV" in result.stdout
