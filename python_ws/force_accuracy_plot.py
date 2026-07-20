#!/usr/bin/env python3
"""离线绘制质量—法向压力准确性曲线。

使用方式（在 python_ws 目录运行）:
    uv run --extra plot python force_accuracy_plot.py \
        ../data/force_accuracy/measurements.csv \
        --config ../config/force_accuracy.yaml
"""

from __future__ import annotations

import csv
import pathlib
import sys
from dataclasses import dataclass
from typing import Annotated

import numpy as np
import typer
import yaml

DEFAULT_CONFIG_PATH = pathlib.Path("../config/force_accuracy.yaml")
REQUIRED_COLUMNS = {
    "mass_g",
    "expected_force_n",
    "measured_pressure_n",
    "std_force_n",
}

app = typer.Typer(no_args_is_help=True)


@dataclass(frozen=True)
class PlotConfig:
    """离线绘图配置。

    Args:
        styles: Matplotlib/SciencePlots 样式应用顺序。
        dpi: PNG 输出分辨率，单位 dpi。
        filename: 输出图片文件名。
        marker_size: 实测点直径，单位 pt。
        fit: 是否对有效点绘制线性最小二乘拟合。
    """

    styles: tuple[str, ...]
    dpi: int
    filename: str
    marker_size: float
    fit: bool = True


def load_plot_config(config_path: pathlib.Path) -> PlotConfig:
    """读取 YAML 中的绘图配置。

    Args:
        config_path: 实验 YAML 路径。

    Returns:
        经过校验的绘图配置。

    Raises:
        OSError: 配置文件无法读取时抛出。
        ValueError: YAML 结构或绘图字段无效时抛出。
    """
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        plot = raw["plot"]
        styles = tuple(str(style) for style in plot["styles"])
        dpi = int(plot["dpi"])
        filename = str(plot["filename"])
        marker_size = float(plot["marker_size"])
        fit = bool(plot.get("fit", True))
        if not styles:
            raise ValueError("plot.styles 不能为空")
        if dpi <= 0:
            raise ValueError("plot.dpi 必须大于 0")
        if marker_size <= 0:
            raise ValueError("plot.marker_size 必须大于 0")
        if pathlib.Path(filename).name != filename:
            raise ValueError("plot.filename 只能是文件名，不能包含目录")
        return PlotConfig(
            styles=styles, dpi=dpi, filename=filename, marker_size=marker_size, fit=fit
        )
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"绘图配置结构或字段无效: {exc}") from exc


def load_measurement_columns(
    csv_path: pathlib.Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """读取绘图所需的测量列。

    Args:
        csv_path: 测量脚本生成的 CSV 路径。

    Returns:
        `(质量 g, 理论压力 N, 实测压力 N, 标准差 N)`，各数组 shape=(N,)。

    Raises:
        OSError: CSV 无法读取时抛出。
        ValueError: CSV 为空、缺列或包含无效数值时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"CSV 缺少字段: {', '.join(sorted(missing))}")
        rows = list(reader)
    if not rows:
        raise ValueError("CSV 没有测量数据")
    try:
        masses = np.array([float(row["mass_g"]) for row in rows], dtype=np.float64)
        expected = np.array([float(row["expected_force_n"]) for row in rows], dtype=np.float64)
        measured = np.array([float(row["measured_pressure_n"]) for row in rows], dtype=np.float64)
        standard_deviation = np.array([float(row["std_force_n"]) for row in rows], dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"CSV 包含无效数值: {exc}") from exc
    if not all(np.all(np.isfinite(values)) for values in (masses, expected, measured)):
        raise ValueError("质量、理论压力或实测压力包含非有限数值")
    return masses, expected, measured, standard_deviation


def load_protocol_columns(
    csv_path: pathlib.Path,
) -> tuple[np.ndarray, np.ndarray] | None:
    """读取可选的自研协议压力和标准差列。

    Args:
        csv_path: 测量脚本生成的 CSV 路径。

    Returns:
        `(自研协议压力 N, 标准差 N)`，各数组 shape=(N,)；旧版 CSV
        没有相应字段或本次回放没有完整结果时返回 None。

    Raises:
        OSError: CSV 无法读取时抛出。
        ValueError: 自研协议字段包含无效数值时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        if not {"protocol_measured_pressure_n", "protocol_std_force_n"} <= fieldnames:
            return None
        rows = list(reader)
    try:
        measured = np.array(
            [float(row["protocol_measured_pressure_n"]) for row in rows], dtype=np.float64
        )
        standard_deviation = np.array(
            [float(row["protocol_std_force_n"]) for row in rows], dtype=np.float64
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"CSV 自研协议列包含无效数值: {exc}") from exc
    if not np.all(np.isfinite(measured)):
        return None
    return measured, standard_deviation


def load_inclusion_mask(csv_path: pathlib.Path, row_count: int) -> np.ndarray:
    """读取逻辑排除标记，兼容没有该字段的旧版 CSV。

    Args:
        csv_path: 测量脚本生成的 CSV 路径。
        row_count: 调用方已读取的 CSV 行数。

    Returns:
        是否纳入绘图和统计的布尔数组，shape=(N,)。

    Raises:
        OSError: CSV 无法读取时抛出。
        ValueError: 标记数量或取值无效时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if "included" not in set(reader.fieldnames or []):
            return np.ones(row_count, dtype=bool)
        rows = list(reader)
    if len(rows) != row_count:
        raise ValueError("CSV 行数在读取期间发生变化")
    values = [row["included"].strip().lower() for row in rows]
    if any(value not in {"true", "false"} for value in values):
        raise ValueError("included 字段只能是 true 或 false")
    return np.array([value == "true" for value in values], dtype=bool)


def fit_linear_response(masses_g: np.ndarray, pressures_n: np.ndarray) -> tuple[float, float, float]:
    """对有效质量点做线性最小二乘拟合。

    Args:
        masses_g: 质量，单位 g，shape=(N,)。
        pressures_n: 法向压力，单位 N，shape=(N,)。

    Returns:
        `(斜率 N/g, 截距 N, R²)`。

    Raises:
        ValueError: 有效点少于两个，或质量值缺少变化时抛出。
    """
    if masses_g.size < 2 or np.unique(masses_g).size < 2:
        raise ValueError("线性拟合至少需要两个不同质量的有效点")
    slope_n_per_g, intercept_n = np.polyfit(masses_g, pressures_n, 1)
    fitted = slope_n_per_g * masses_g + intercept_n
    residual_sum = float(np.sum((pressures_n - fitted) ** 2))
    total_sum = float(np.sum((pressures_n - np.mean(pressures_n)) ** 2))
    r_squared = 1.0 if total_sum == 0.0 else 1.0 - residual_sum / total_sum
    return float(slope_n_per_g), float(intercept_n), r_squared
def plot_accuracy(csv_path: pathlib.Path, config: PlotConfig) -> pathlib.Path:
    """根据测量 CSV 生成 IEEE 单栏准确性曲线。

    Args:
        csv_path: 测量脚本生成的 CSV 路径。
        config: 绘图样式与输出配置。

    Returns:
        生成的图片路径。

    Raises:
        OSError: CSV 或图片无法读写时抛出。
        ValueError: 测量数据无效时抛出。
    """
    masses, expected, measured, standard_deviation = load_measurement_columns(csv_path)
    protocol_columns = load_protocol_columns(csv_path)
    included = load_inclusion_mask(csv_path, len(masses))
    if not np.any(included):
        raise ValueError("所有记录都已排除，无法绘图")

    # 延迟导入让测量环境无需安装绘图库，只有 plot extra 才加载这些依赖。
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scienceplots  # noqa: F401

    order = np.argsort(masses)
    with plt.style.context(list(config.styles)):
        figure, axis = plt.subplots()
        axis.errorbar(
            masses[included],
            measured[included],
            yerr=standard_deviation[included],
            fmt="o",
            markersize=config.marker_size,
            elinewidth=0.8,
            capthick=0.8,
            capsize=2,
            label="Official SDK",
        )
        if np.any(~included):
            axis.errorbar(
                masses[~included],
                measured[~included],
                yerr=standard_deviation[~included],
                fmt="x",
                color="0.55",
                markersize=config.marker_size,
                elinewidth=0.8,
                capthick=0.8,
                capsize=2,
                label="Excluded",
            )
        if protocol_columns is not None:
            protocol_measured, protocol_std = protocol_columns
            axis.errorbar(
                masses[included],
                protocol_measured[included],
                yerr=protocol_std[included],
                fmt="s",
                markerfacecolor="none",
                markersize=config.marker_size,
                elinewidth=0.8,
                capthick=0.8,
                capsize=2,
                label="Serial protocol",
            )
        axis.plot(masses[order], expected[order], label="Theoretical $F=mg$")
        if config.fit and np.unique(masses[included]).size >= 2:
            slope, intercept, r_squared = fit_linear_response(
                masses[included], measured[included]
            )
            fit_masses = np.sort(masses[included])
            axis.plot(
                fit_masses,
                slope * fit_masses + intercept,
                linestyle="--",
                linewidth=1.0,
                label=f"SDK fit (k={slope:.5f} N/g, $R^2$={r_squared:.4f})",
            )
            if protocol_columns is not None:
                protocol_slope, protocol_intercept, protocol_r_squared = (
                    fit_linear_response(masses[included], protocol_measured[included])
                )
                axis.plot(
                    fit_masses,
                    protocol_slope * fit_masses + protocol_intercept,
                    linestyle=":",
                    linewidth=1.0,
                    label=(
                        f"Protocol fit (k={protocol_slope:.5f} N/g, "
                        f"$R^2$={protocol_r_squared:.4f})"
                    ),
                )
        axis.set_xlabel("Mass (g)")
        axis.set_ylabel("Normal pressure (N)")
        axis.grid(True, alpha=0.3)
        axis.legend()
        figure.tight_layout()
        output_path = csv_path.parent / config.filename
        figure.savefig(output_path, dpi=config.dpi)
        plt.close(figure)
    return output_path


@app.command()
def plot(
    csv_path: Annotated[pathlib.Path, typer.Argument(help="测量 CSV 路径")],
    config_path: Annotated[pathlib.Path, typer.Option("--config", "-c")] = DEFAULT_CONFIG_PATH,
) -> None:
    """读取测量 CSV，并生成 IEEE 单栏质量—法向压力曲线。"""
    try:
        config = load_plot_config(config_path)
        output_path = plot_accuracy(csv_path, config)
    except OSError as exc:
        typer.secho(f"错误: 无法读写文件: {exc}", err=True)
        raise typer.Exit(1) from exc
    except (ImportError, ValueError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"绘图完成: {output_path}")


if __name__ == "__main__":
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
