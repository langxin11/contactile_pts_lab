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
        layout: 面板布局模式。
            - "grid" (默认): 单文件左 1 右 2（左: 准确性, 右上: 残差, 右下: 百分比误差）。
            - "stacked": 单文件上下双面板（准确性 + 残差）。
            - "separate": 三张独立图片（准确性、残差、百分比误差）。
        group_stats: 同一质量多次测量时是否 overlay 组均值。
    """

    styles: tuple[str, ...]
    dpi: int
    filename: str
    marker_size: float
    fit: bool = True
    layout: str = "grid"
    group_stats: bool = True


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
        layout = str(plot.get("layout", "grid"))
        group_stats = bool(plot.get("group_stats", True))
        if layout not in {"grid", "stacked", "separate"}:
            raise ValueError("plot.layout 必须是 grid / stacked / separate 之一")
        if not styles:
            raise ValueError("plot.styles 不能为空")
        if dpi <= 0:
            raise ValueError("plot.dpi 必须大于 0")
        if marker_size <= 0:
            raise ValueError("plot.marker_size 必须大于 0")
        if pathlib.Path(filename).name != filename:
            raise ValueError("plot.filename 只能是文件名，不能包含目录")
        return PlotConfig(
            styles=styles,
            dpi=dpi,
            filename=filename,
            marker_size=marker_size,
            fit=fit,
            layout=layout,
            group_stats=group_stats,
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


@dataclass(frozen=True)
class GroupStats:
    """单个质量点的重复测量统计。"""

    mass_g: float
    count: int
    mean_n: float
    between_sample_std_n: float


def compute_group_stats(
    masses_g: np.ndarray, measured_n: np.ndarray, included: np.ndarray
) -> list[GroupStats]:
    """对同一质量的多次测量计算组均值和组间标准差。

    与 load_measurement_columns 返回的 std_force_n（窗口内短期稳定性）
    不同，组间标准差反映同一质量下独立复测的散布程度（repeatability）。

    Args:
        masses_g: 质量值，shape=(N,)。
        measured_n: 实测法向压力，shape=(N,)。
        included: 纳入标记，shape=(N,)。

    Returns:
        每个出现 >1 次的质量一个条目，按质量升序。
    """
    unique_masses = np.unique(masses_g)
    result: list[GroupStats] = []
    for mass in unique_masses:
        mask = (masses_g == mass) & included
        if np.sum(mask) < 2:
            continue
        values = measured_n[mask]
        result.append(
            GroupStats(
                mass_g=float(mass),
                count=int(np.sum(mask)),
                mean_n=float(np.mean(values)),
                between_sample_std_n=float(np.std(values, ddof=1)),
            )
        )
    return result


def _draw_pct_error_panel(
    axis: "matplotlib.axes.Axes",  # noqa: F821  # 惰性导入，运行时通过 forward-ref 解析
    masses: np.ndarray,
    expected: np.ndarray,
    measured: np.ndarray,
    standard_deviation: np.ndarray,
    included: np.ndarray,
    protocol_measured: np.ndarray | None,
    protocol_std: np.ndarray | None,
    config: PlotConfig,
) -> None:
    """在给定 Axes 上绘制相对误差百分比散点图，含 ±1% / ±5% 参考带。"""
    pct_err = (measured - expected) / expected * 100.0
    pct_std = standard_deviation / expected * 100.0

    axis.errorbar(
        masses[included],
        pct_err[included],
        yerr=pct_std[included],
        fmt="o",
        markersize=config.marker_size,
        elinewidth=0.8,
        capthick=0.8,
        capsize=2,
        label="Official SDK",
    )
    if protocol_measured is not None and protocol_std is not None:
        protocol_pct_err = (protocol_measured - expected) / expected * 100.0
        protocol_pct_std = protocol_std / expected * 100.0
        axis.errorbar(
            masses[included],
            protocol_pct_err[included],
            yerr=protocol_pct_std[included],
            fmt="s",
            markerfacecolor="none",
            markersize=config.marker_size,
            elinewidth=0.8,
            capthick=0.8,
            capsize=2,
            label="Serial protocol",
        )
    if np.any(~included):
        axis.errorbar(
            masses[~included],
            pct_err[~included],
            yerr=pct_std[~included],
            fmt="x",
            color="0.55",
            markersize=config.marker_size,
            elinewidth=0.8,
            capthick=0.8,
            capsize=2,
            label="Excluded",
        )

    for band_pct, style, alpha_val in [
        (0.0, {"color": "0.3", "linewidth": 0.8}, 1.0),
        (1.0, {"color": "0.55", "linewidth": 0.6, "linestyle": ":"}, 0.6),
        (5.0, {"color": "0.7", "linewidth": 0.5, "linestyle": ":"}, 0.4),
    ]:
        for sign in (-1, 1):
            axis.axhline(band_pct * sign, alpha=alpha_val, **style)

    x_min, x_max = np.min(masses), np.max(masses)
    axis.set_xlim([x_min * 0.9, x_max * 1.1])
    axis.set_xlabel("Mass (g)")
    axis.set_ylabel("Relative error (%)")
    axis.grid(True, alpha=0.3)
    axis.legend(fontsize="x-small")


def _write_percentage_error_plot(
    csv_dir: pathlib.Path,
    filename: str,
    masses: np.ndarray,
    expected: np.ndarray,
    measured: np.ndarray,
    standard_deviation: np.ndarray,
    included: np.ndarray,
    protocol_measured: np.ndarray | None,
    protocol_std: np.ndarray | None,
    config: PlotConfig,
) -> pathlib.Path:
    """生成独立的相对误差百分比散点图（separate 布局用）。

    Returns:
        生成的图片路径。
    """
    import matplotlib.pyplot as plt

    stem = pathlib.Path(filename).stem
    suffix = pathlib.Path(filename).suffix or ".png"
    pct_filename = f"{stem}_pct_error{suffix}"

    figure, axis = plt.subplots()
    _draw_pct_error_panel(
        axis, masses, expected, measured, standard_deviation,
        included, protocol_measured, protocol_std, config,
    )
    figure.tight_layout()
    output_path = csv_dir / pct_filename
    figure.savefig(output_path, dpi=config.dpi)
    plt.close(figure)
    return output_path
def _draw_accuracy_panel(
    axis: "matplotlib.axes.Axes",  # noqa: F821  # 惰性导入，运行时通过 forward-ref 解析
    masses: np.ndarray,
    expected: np.ndarray,
    measured: np.ndarray,
    standard_deviation: np.ndarray,
    included: np.ndarray,
    protocol_measured: np.ndarray | None,
    protocol_std: np.ndarray | None,
    config: PlotConfig,
) -> None:
    """在给定 Axes 上绘制准确性主图（不含残差）。"""
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
    if protocol_measured is not None and protocol_std is not None:
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

    order = np.argsort(masses)
    axis.plot(masses[order], expected[order], label="Theoretical $F=mg$")

    # —— 分组统计 overlay ——
    if config.group_stats:
        groups = compute_group_stats(masses, measured, included)
        if groups:
            g_mass = np.array([g.mass_g for g in groups])
            g_mean = np.array([g.mean_n for g in groups])
            g_std = np.array([g.between_sample_std_n for g in groups])
            axis.errorbar(
                g_mass,
                g_mean,
                yerr=g_std,
                fmt="D",
                markersize=config.marker_size * 2.0,
                markerfacecolor="tab:blue",
                markeredgecolor="0.2",
                markeredgewidth=1.0,
                elinewidth=1.2,
                capthick=1.2,
                capsize=3,
                zorder=10,
                label=(
                    f"Group mean (n≥2, "
                    f"N={sum(g.count for g in groups)} pts in {len(groups)} groups)"
                ),
            )
        if protocol_measured is not None and protocol_std is not None:
            proto_groups = compute_group_stats(masses, protocol_measured, included)
            if proto_groups:
                pg_mass = np.array([g.mass_g for g in proto_groups])
                pg_mean = np.array([g.mean_n for g in proto_groups])
                pg_std = np.array([g.between_sample_std_n for g in proto_groups])
                axis.errorbar(
                    pg_mass,
                    pg_mean,
                    yerr=pg_std,
                    fmt="D",
                    markersize=config.marker_size * 2.0,
                    markerfacecolor="none",
                    markeredgecolor="tab:orange",
                    markeredgewidth=1.0,
                    elinewidth=1.2,
                    capthick=1.2,
                    capsize=3,
                    zorder=9,
                    label="Protocol group mean (n≥2)",
                )

    # —— 线性拟合 ——
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
        if protocol_measured is not None and protocol_std is not None:
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
    axis.legend(fontsize="small")


def _draw_residual_panel(
    axis: "matplotlib.axes.Axes",  # noqa: F821  # 惰性导入，运行时通过 forward-ref 解析
    masses: np.ndarray,
    expected: np.ndarray,
    measured: np.ndarray,
    standard_deviation: np.ndarray,
    included: np.ndarray,
    protocol_measured: np.ndarray | None,
    protocol_std: np.ndarray | None,
    config: PlotConfig,
) -> None:
    """在给定 Axes 上绘制残差子图 (实测-理论，N)。"""
    residual_n = measured - expected
    residual_std_n = standard_deviation

    axis.axhline(0, color="0.3", linewidth=0.8, zorder=1)
    axis.errorbar(
        masses[included],
        residual_n[included],
        yerr=residual_std_n[included],
        fmt="o",
        markersize=config.marker_size,
        elinewidth=0.8,
        capthick=0.8,
        capsize=2,
        label="Official SDK",
    )
    if protocol_measured is not None and protocol_std is not None:
        protocol_residual = protocol_measured - expected
        axis.errorbar(
            masses[included],
            protocol_residual[included],
            yerr=protocol_std[included],
            fmt="s",
            markerfacecolor="none",
            markersize=config.marker_size,
            elinewidth=0.8,
            capthick=0.8,
            capsize=2,
            label="Serial protocol",
        )
    if np.any(~included):
        axis.errorbar(
            masses[~included],
            residual_n[~included],
            yerr=residual_std_n[~included],
            fmt="x",
            color="0.55",
            markersize=config.marker_size,
            elinewidth=0.8,
            capthick=0.8,
            capsize=2,
            label="Excluded",
        )

    axis.set_xlabel("Mass (g)")
    axis.set_ylabel("Residual (N)")
    axis.grid(True, alpha=0.3)
    axis.legend(fontsize="x-small")


def plot_accuracy(csv_path: pathlib.Path, config: PlotConfig) -> pathlib.Path:
    """根据测量 CSV 生成准确性曲线。

    三种布局模式（通过 config.layout 控制）:
      - "grid":     单文件左 1 右 2（左: 准确性, 右上: 残差, 右下: 百分比误差）。
      - "stacked":  单文件上下双面板（准确性 + 残差）。
      - "separate": 三张独立图片，文件名分别追加 _residual / _pct_error。

    Args:
        csv_path: 测量脚本生成的 CSV 路径。
        config: 绘图样式与输出配置。

    Returns:
        生成的主图路径。

    Raises:
        OSError: CSV 或图片无法读写时抛出。
        ValueError: 测量数据无效时抛出。
    """
    masses, expected, measured, standard_deviation = load_measurement_columns(csv_path)
    protocol_columns = load_protocol_columns(csv_path)
    protocol_measured: np.ndarray | None = None
    protocol_std: np.ndarray | None = None
    if protocol_columns is not None:
        protocol_measured, protocol_std = protocol_columns
    included = load_inclusion_mask(csv_path, len(masses))
    if not np.any(included):
        raise ValueError("所有记录都已排除，无法绘图")

    # 延迟导入让测量环境无需安装绘图库，只有 plot extra 才加载这些依赖。
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scienceplots  # noqa: F401

    stem = pathlib.Path(config.filename).stem
    suffix = pathlib.Path(config.filename).suffix or ".png"
    out_dir = csv_path.parent

    with plt.style.context(list(config.styles)):
        if config.layout == "grid":
            # 左 1 右 2: 左列准确性子图占两行，右列上下分别为残差和百分比误差
            figure = plt.figure(figsize=(7.0, 4.5), layout="constrained")
            gs = figure.add_gridspec(
                2, 2, width_ratios=[1.4, 1], height_ratios=[1, 1],
                hspace=0.05, wspace=0.05,
            )
            ax_acc = figure.add_subplot(gs[:, 0])
            ax_res = figure.add_subplot(gs[0, 1])
            ax_pct = figure.add_subplot(gs[1, 1])

            _draw_accuracy_panel(
                ax_acc, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            _draw_residual_panel(
                ax_res, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            _draw_pct_error_panel(
                ax_pct, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )

            output_path = out_dir / config.filename
            figure.savefig(output_path, dpi=config.dpi)
            plt.close(figure)

        elif config.layout == "stacked":
            figure, (ax_acc, ax_res) = plt.subplots(
                2, 1, sharex=True, figsize=(3.5, 4.8), height_ratios=[2.5, 1],
            )
            _draw_accuracy_panel(
                ax_acc, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            _draw_residual_panel(
                ax_res, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            figure.tight_layout()
            output_path = out_dir / config.filename
            figure.savefig(output_path, dpi=config.dpi)
            plt.close(figure)

        else:  # "separate": 三张独立图片
            # 准确性主图
            figure, ax_acc = plt.subplots()
            _draw_accuracy_panel(
                ax_acc, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            figure.tight_layout()
            output_path = out_dir / config.filename
            figure.savefig(output_path, dpi=config.dpi)
            plt.close(figure)

            # 残差图
            figure, ax_res = plt.subplots()
            _draw_residual_panel(
                ax_res, masses, expected, measured, standard_deviation,
                included, protocol_measured, protocol_std, config,
            )
            figure.tight_layout()
            res_path = out_dir / f"{stem}_residual{suffix}"
            figure.savefig(res_path, dpi=config.dpi)
            plt.close(figure)
            typer.echo(f"残差图: {res_path}")

            # 百分比误差图
            pct_path = _write_percentage_error_plot(
                out_dir, config.filename, masses, expected, measured,
                standard_deviation, included, protocol_measured, protocol_std, config,
            )
            typer.echo(f"百分比误差图: {pct_path}")

    return output_path


@app.command()
def plot(
    csv_path: Annotated[pathlib.Path, typer.Argument(help="测量 CSV 路径")],
    config_path: Annotated[pathlib.Path, typer.Option("--config", "-c")] = DEFAULT_CONFIG_PATH,
) -> None:
    """读取测量 CSV 并生成质量—法向压力准确性曲线（支持 grid/stacked/separate 三种布局）。"""
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
