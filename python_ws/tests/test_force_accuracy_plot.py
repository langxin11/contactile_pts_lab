#!/usr/bin/env python3
"""离线准确性绘图脚本测试。"""

from __future__ import annotations

import csv
import pathlib
import sys

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from force_accuracy_plot import (
    PlotConfig,
    app,
    load_measurement_columns,
    load_plot_config,
    load_protocol_columns,
    plot_accuracy,
)


def _write_csv(csv_path: pathlib.Path) -> None:
    """写入两个确定性质量点，供离线绘图测试复用。"""
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "mass_g",
                "expected_force_n",
                "measured_pressure_n",
                "std_force_n",
                "protocol_measured_pressure_n",
                "protocol_std_force_n",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "mass_g": 100,
                    "expected_force_n": 0.980665,
                    "measured_pressure_n": 0.98,
                    "std_force_n": 0.01,
                    "protocol_measured_pressure_n": 0.979,
                    "protocol_std_force_n": 0.011,
                },
                {
                    "mass_g": 200,
                    "expected_force_n": 1.96133,
                    "measured_pressure_n": 1.95,
                    "std_force_n": 0.02,
                    "protocol_measured_pressure_n": 1.949,
                    "protocol_std_force_n": 0.021,
                },
            ]
        )


def test_load_plot_config() -> None:
    """仓库 YAML 应启用自动钩子所需的 IEEE 单栏配置。"""
    config_path = pathlib.Path(__file__).resolve().parents[2] / "config/force_accuracy.yaml"

    config = load_plot_config(config_path)

    assert config.styles == ("science", "ieee", "no-latex")
    assert config.dpi == 300
    assert config.filename == "mass_vs_normal_force.png"
    assert config.marker_size == pytest.approx(2.5)


def test_load_measurement_columns(tmp_path: pathlib.Path) -> None:
    """绘图脚本应能独立读取测量脚本生成的核心列。"""
    csv_path = tmp_path / "measurements.csv"
    _write_csv(csv_path)

    masses, expected, measured, standard_deviation = load_measurement_columns(csv_path)

    assert masses.tolist() == [100.0, 200.0]
    assert expected.tolist() == pytest.approx([0.980665, 1.96133])
    assert measured.tolist() == pytest.approx([0.98, 1.95])
    assert standard_deviation.tolist() == pytest.approx([0.01, 0.02])


def test_load_protocol_columns(tmp_path: pathlib.Path) -> None:
    """同字节回放列应作为第二组绘图数据读取。"""
    csv_path = tmp_path / "measurements.csv"
    _write_csv(csv_path)

    columns = load_protocol_columns(csv_path)

    assert columns is not None
    measured, standard_deviation = columns
    assert measured.tolist() == pytest.approx([0.979, 1.949])
    assert standard_deviation.tolist() == pytest.approx([0.011, 0.021])


def test_plot_accuracy_generates_png_when_plot_extra_available(tmp_path: pathlib.Path) -> None:
    """安装 plot extra 时应真正生成非空 IEEE 单栏 PNG。"""
    pytest.importorskip("scienceplots")
    csv_path = tmp_path / "measurements.csv"
    _write_csv(csv_path)
    config = PlotConfig(
        styles=("science", "ieee", "no-latex"),
        dpi=100,
        filename="result.png",
        marker_size=3.5,
    )

    output_path = plot_accuracy(csv_path, config)

    assert output_path == tmp_path / "result.png"
    assert output_path.stat().st_size > 0


def test_plot_cli_help_is_offline() -> None:
    """绘图 CLI 帮助不应读取 CSV 或连接硬件。"""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "CSV_PATH" in result.stdout
    assert "--config" in result.stdout
