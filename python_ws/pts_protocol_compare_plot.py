#!/usr/bin/env python3
"""离线绘制 PTS Type 5/6 与官方 SDK 日志的对比图。

滑移对比图以逐字段时间序列为主：每个子图将协议解析值与 SDK 值叠绘，
便于直接观察滑移状态切换及摩擦估计的时序差异。

使用方式（在 python_ws 目录运行）:
    uv run --extra plot python pts_protocol_compare_plot.py \
        ../data/protocol_compare/<时间戳>/protocol.csv \
        --sdk-csv ../data/protocol_compare/<时间戳>/sdk.csv
"""

from __future__ import annotations

import csv
import math
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True)
DEFAULT_OUTPUT_NAME = "slip_difference.png"


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def load_protocol_rows(csv_path: pathlib.Path) -> list[dict[str, float]]:
    """读取协议 CSV 的数值列，剔除空值与非有限值所在的行。

    Args:
        csv_path: ``pts_protocol_compare.py`` 写出的 protocol.csv 路径。

    Returns:
        协议行列表；含空字符串 / NaN / Inf 的行会被跳过并告警。

    Raises:
        OSError: CSV 无法读取时抛出。
        ValueError: CSV 的数值列格式错误或无可读行时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    if not raw_rows:
        raise ValueError(f"协议 CSV 为空: {csv_path}")

    result: list[dict[str, float]] = []
    skipped_empty = 0
    for row in raw_rows:
        converted: dict[str, float] = {}
        ts_label = row.get("T_us", "?")
        for name, value in row.items():
            if value is None:
                continue
            stripped = value.strip()
            if not stripped:
                skipped_empty += 1
                typer.secho(
                    f"警告: T_us={ts_label} 字段 '{name}' 为空值，已跳过该字段",
                    fg=typer.colors.YELLOW,
                )
                converted = {}
                break
            try:
                converted[name] = float(stripped)
            except ValueError:
                typer.secho(
                    f"警告: T_us={ts_label} 字段 '{name}' 值 '{stripped}' 无法转为浮点数，"
                    f"已跳过整行",
                    fg=typer.colors.YELLOW,
                )
                converted = {}
                break
        if converted:
            result.append(converted)
    if skipped_empty:
        typer.secho(
            f"提示: 共 {skipped_empty} 个空值单元格被跳过",
            fg=typer.colors.YELLOW,
        )
    if not result:
        raise ValueError(f"协议 CSV 无有效数值行: {csv_path}")
    return result


def load_sdk_rows(csv_path: pathlib.Path) -> list[dict[str, str]]:
    """读取 SDK CSV，并保留原始字符串以按字段进行数值转换。

    Args:
        csv_path: 官方 SDK 导出的 CSV 路径。

    Returns:
        SDK CSV 行列表。

    Raises:
        OSError: CSV 无法读取时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# 对齐数据结构
# ---------------------------------------------------------------------------


@dataclass
class _AlignedData:
    """按时间戳对齐后的协议与 SDK 滑动字段数据。"""

    timestamps_us: list[int] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    protocol_matrix: list[list[float]] = field(default_factory=list)  # [field][time]
    sdk_matrix: list[list[float]] = field(default_factory=list)
    diff_matrix: list[list[float]] = field(default_factory=list)
    skipped_count: int = 0


def _is_slip_field(field: str) -> bool:
    """判断是否为可绘制的滑动/摩擦相关字段。"""
    return (
        "slipState" in field
        or "isSDActive" in field
        or "isRefLoaded" in field
        or field.endswith("_FRIC")
    )


def align_slip_data(
    protocol_rows: list[dict[str, float]], sdk_rows: list[dict[str, str]]
) -> _AlignedData:
    """按时间戳对齐协议与 SDK 数据，返回三份矩阵（协议值、SDK 值、差异）。

    含 NaN/Inf 的时间戳整体跳过；字段缺失 (KeyError) 与数值转换失败 (ValueError)
    分别计入跳过计数并告警。

    Raises:
        ValueError: 无可对齐时间戳或无可绘制字段时抛出。
    """
    protocol_by_ts = {int(row["T_us"]): row for row in protocol_rows if "T_us" in row}
    sdk_by_ts = {int(row["T_us"]): row for row in sdk_rows if row.get("T_us")}
    common_timestamps = sorted(protocol_by_ts.keys() & sdk_by_ts.keys())
    if not common_timestamps:
        raise ValueError("没有可对齐的时间戳，无法绘图")

    first_protocol_row = protocol_by_ts[common_timestamps[0]]
    first_sdk_row = sdk_by_ts[common_timestamps[0]]
    fields = sorted(
        field
        for field in first_protocol_row
        if field != "T_us" and field in first_sdk_row and _is_slip_field(field)
    )
    if not fields:
        raise ValueError("SDK CSV 不含可绘制的滑动字段")

    typer.echo(f"可绘制滑动字段 ({len(fields)}): {', '.join(fields)}")

    n_fields = len(fields)
    timestamps: list[int] = []
    protocol_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    sdk_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    diff_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    skipped_value = 0
    skipped_keyerror = 0

    for timestamp in common_timestamps:
        protocol_row = protocol_by_ts[timestamp]
        sdk_row = sdk_by_ts[timestamp]
        try:
            p_vals = [float(protocol_row[f]) for f in fields]
            s_vals = [float(sdk_row[f]) for f in fields]
        except KeyError:
            skipped_keyerror += 1
            if skipped_keyerror == 1:
                typer.secho(
                    f"警告: T_us={timestamp} 缺少字段，将跳过（仅提示一次）",
                    fg=typer.colors.YELLOW,
                )
            continue
        except (TypeError, ValueError):
            skipped_value += 1
            continue

        if not all(
            math.isfinite(p) and math.isfinite(s)
            for p, s in zip(p_vals, s_vals)
        ):
            skipped_value += 1
            continue

        timestamps.append(timestamp)
        for fi in range(n_fields):
            protocol_matrix[fi].append(p_vals[fi])
            sdk_matrix[fi].append(s_vals[fi])
            diff_matrix[fi].append(p_vals[fi] - s_vals[fi])

    if not timestamps:
        raise ValueError("所有可对齐滑动数据均含 NaN/Inf 或无效值，无法绘图")

    total_skipped = skipped_value + skipped_keyerror
    if skipped_keyerror:
        typer.secho(
            f"警告: {skipped_keyerror} 个时间戳因字段缺失被跳过",
            fg=typer.colors.YELLOW,
        )
    return _AlignedData(
        timestamps_us=timestamps,
        fields=fields,
        protocol_matrix=protocol_matrix,
        sdk_matrix=sdk_matrix,
        diff_matrix=diff_matrix,
        skipped_count=total_skipped,
    )


def build_slip_difference_matrix(
    protocol_rows: list[dict[str, float]], sdk_rows: list[dict[str, str]]
) -> tuple[list[int], list[str], list[list[float]], int]:
    """构建滑移字段的协议减 SDK 差异矩阵。

    Args:
        protocol_rows: 协议 CSV 行。
        sdk_rows: SDK CSV 行。

    Returns:
        时间戳（us）、字段名、``shape=(字段数, 时间点数)`` 差异矩阵及跳过数。
    """
    aligned = align_slip_data(protocol_rows, sdk_rows)
    return (
        aligned.timestamps_us,
        aligned.fields,
        aligned.diff_matrix,
        aligned.skipped_count,
    )


def _align_fields(
    protocol_rows: list[dict[str, float]],
    sdk_rows: list[dict[str, str]],
    fields: list[str],
) -> _AlignedData:
    """按时间戳对齐指定字段，返回协议值、SDK 值、差异三份矩阵。

    Args:
        protocol_rows: 协议 CSV 行。
        sdk_rows: SDK CSV 行。
        fields: 需要对齐的字段名列表。

    Returns:
        对齐后的数据，含三份矩阵。

    Raises:
        ValueError: 无可对齐时间戳或字段全部缺失时抛出。
    """
    protocol_by_ts = {int(row["T_us"]): row for row in protocol_rows if "T_us" in row}
    sdk_by_ts = {int(row["T_us"]): row for row in sdk_rows if row.get("T_us")}
    common_timestamps = sorted(protocol_by_ts.keys() & sdk_by_ts.keys())
    if not common_timestamps:
        raise ValueError("没有可对齐的时间戳")

    n_fields = len(fields)
    timestamps: list[int] = []
    protocol_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    sdk_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    diff_matrix: list[list[float]] = [[] for _ in range(n_fields)]
    skipped = 0

    for timestamp in common_timestamps:
        protocol_row = protocol_by_ts[timestamp]
        sdk_row = sdk_by_ts[timestamp]
        try:
            p_vals = [float(protocol_row[f]) for f in fields]
            s_vals = [float(sdk_row[f]) for f in fields]
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if not all(
            math.isfinite(p) and math.isfinite(s)
            for p, s in zip(p_vals, s_vals)
        ):
            skipped += 1
            continue
        timestamps.append(timestamp)
        for fi in range(n_fields):
            protocol_matrix[fi].append(p_vals[fi])
            sdk_matrix[fi].append(s_vals[fi])
            diff_matrix[fi].append(p_vals[fi] - s_vals[fi])

    if not timestamps:
        raise ValueError("无可用的对齐数据")

    return _AlignedData(
        timestamps_us=timestamps,
        fields=fields,
        protocol_matrix=protocol_matrix,
        sdk_matrix=sdk_matrix,
        diff_matrix=diff_matrix,
        skipped_count=skipped,
    )


# ---------------------------------------------------------------------------
# 辅助统计
# ---------------------------------------------------------------------------


def _field_sort_key(aligned: _AlignedData, field_idx: int) -> float:
    """返回该字段的最大绝对差异，用于排序。"""
    row = aligned.diff_matrix[field_idx]
    return max(abs(v) for v in row) if row else 0.0


def _sorted_field_indices(aligned: _AlignedData) -> list[int]:
    """按最大绝对差异降序排列的字段索引。"""
    return sorted(
        range(len(aligned.fields)),
        key=lambda i: _field_sort_key(aligned, i),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# 绘图
# ---------------------------------------------------------------------------


def plot_slip_differences(
    protocol_rows: list[dict[str, float]],
    sdk_rows: list[dict[str, str]],
    output_path: pathlib.Path,
) -> tuple[pathlib.Path, int]:
    """以逐字段时间序列绘制协议与 SDK 的滑移结果对比。

    Args:
        protocol_rows: 协议 CSV 行。
        sdk_rows: SDK CSV 行。
        output_path: 输出 PNG 路径。

    Returns:
        ``(输出路径, 跳过的非有限时间戳数)``。

    Raises:
        RuntimeError: 缺少或无法导入 plot extra 时抛出。
        ValueError: 无可绘制数据时抛出。
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import scienceplots  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("绘图需要 plot extra，请使用 `uv run --extra plot` 运行") from exc

    typer.echo("正在对齐协议与 SDK 数据 ...")
    aligned = align_slip_data(protocol_rows, sdk_rows)

    elapsed_sec = [ts / 1_000_000 for ts in aligned.timestamps_us]
    n_fields = len(aligned.fields)

    # 差异明显的字段优先排在前面，方便先定位值得关注的曲线。
    sorted_indices = _sorted_field_indices(aligned)
    n_cols = 2 if n_fields > 1 else 1
    n_rows = math.ceil(n_fields / n_cols)

    with plt.style.context(["science", "ieee", "no-latex"]):
        fig, axes = plt.subplots(
            n_rows,
            n_cols,
            figsize=(7.0, max(2.8, n_rows * 2.25)),
            squeeze=False,
        )
        cmap_ts = plt.get_cmap("tab10")
        for rank, fi in enumerate(sorted_indices):
            ax = axes.flat[rank]
            color = cmap_ts(rank % 10)
            ax.plot(
                elapsed_sec, aligned.protocol_matrix[fi],
                color=color, linewidth=0.9, label="Protocol",
            )
            ax.plot(
                elapsed_sec, aligned.sdk_matrix[fi],
                color=color, linewidth=0.8, linestyle="--",
                alpha=0.75, label="SDK",
            )
            ax.set_title(aligned.fields[fi], fontsize=7)
            ax.set_xlabel("Time (s)", fontsize=6)
            ax.set_ylabel("Value", fontsize=6)
            _fmt_time_axis(ax, nbins=4)
            ax.tick_params(labelsize=5)
            ax.legend(fontsize=5, frameon=False)

        for ax in axes.flat[n_fields:]:
            ax.remove()

        fig.suptitle("Slip Signals: Protocol vs SDK", fontsize=10)
        fig.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)

    return output_path, aligned.skipped_count


# ---------------------------------------------------------------------------
# Global-force / pillar 信号绘图
# ---------------------------------------------------------------------------

AXIS_COLORS = {"X": "#d62728", "Y": "#2ca02c", "Z": "#1f77b4"}


def _fmt_time_axis(ax: "plt.Axes", nbins: int = 6) -> None:  # type: ignore[name-defined]  # noqa: F821
    """强制 x 轴以普通十进制秒数显示，杜绝 IEEE 样式的科学计数法/offset。

    Args:
        ax: 目标 Axes。
        nbins: 最大刻度数（pillar 子图用 3-4 个即可）。
    """
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=nbins))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}"))


def _setup_matplotlib() -> None:
    """初始化 matplotlib Agg 后端与 scienceplots 样式。"""
    import matplotlib

    matplotlib.use("Agg")
    import scienceplots  # noqa: F401


def _plot_global_force(
    protocol_rows: list[dict[str, float]],
    sdk_rows: list[dict[str, str]],
    output_path: pathlib.Path,
    sensors: tuple[int, ...] = (0, 1),
) -> pathlib.Path:
    """绘制每个传感器的全局力 (GFX, GFY, GFZ) 时间序列，协议实线 + SDK 虚线。

    Args:
        protocol_rows: 协议 CSV 行。
        sdk_rows: SDK CSV 行。
        output_path: 输出 PNG 路径。
        sensors: 需要绘制的传感器编号。

    Returns:
        输出路径。
    """
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    _setup_matplotlib()
    n_sensors = len(sensors)
    typer.echo(f"绘制传感器 {list(sensors)} 的全局力 ...")

    with plt.style.context(["science", "ieee", "no-latex"]):
        fig = plt.figure(figsize=(3.5 * n_sensors, 3.5))
        gs = gridspec.GridSpec(1, n_sensors, wspace=0.35)

        for col, sensor_id in enumerate(sensors):
            axes_names = [f"S{sensor_id}_G_F{a}" for a in ("X", "Y", "Z")]
            aligned = _align_fields(protocol_rows, sdk_rows, axes_names)

            t_sec = [
                ts / 1_000_000
                for ts in aligned.timestamps_us
            ]
            ax = fig.add_subplot(gs[0, col])
            for fi, field in enumerate(aligned.fields):
                axis_letter = field[-1]  # X, Y, Z
                color = AXIS_COLORS.get(axis_letter, "black")
                ax.plot(
                    t_sec, aligned.protocol_matrix[fi],
                    color=color, linewidth=0.8, label=f"GF{axis_letter} (proto)",
                )
                ax.plot(
                    t_sec, aligned.sdk_matrix[fi],
                    color=color, linewidth=0.6, linestyle="--", alpha=0.6,
                    label=f"GF{axis_letter} (SDK)",
                )
            ax.set_title(f"Sensor {sensor_id} Global Force")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Force (N)")
            _fmt_time_axis(ax)
            ax.legend(fontsize=5, frameon=False)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
    return output_path


def _plot_pillar_grid(
    protocol_rows: list[dict[str, float]],
    sdk_rows: list[dict[str, str]],
    output_path: pathlib.Path,
    sensor: int = 0,
    field_type: str = "force",
    n_pillars: int = 9,
) -> pathlib.Path:
    """3×3 网格绘制每个柱子的力或位移时间序列（协议实线 + SDK 虚线）。

    Args:
        protocol_rows: 协议 CSV 行。
        sdk_rows: SDK CSV 行。
        output_path: 输出 PNG 路径。
        sensor: 传感器编号。
        field_type: ``"force"`` 或 ``"disp"``。
        n_pillars: 柱子数量（默认 9，铺成 3×3）。

    Returns:
        输出路径。
    """
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    _setup_matplotlib()

    prefix = "F" if field_type == "force" else "D"
    ylabel = "Force (N)" if field_type == "force" else "Displacement (mm)"
    plot_label = "force" if field_type == "force" else "displacement"

    typer.echo(f"绘制 Sensor {sensor} 的 3×3 pillar {plot_label} 网格 ...")

    with plt.style.context(["science", "ieee", "no-latex"]):
        fig = plt.figure(figsize=(10.5, 7.5))
        gs = gridspec.GridSpec(3, 3, wspace=0.30, hspace=0.45)

        for pillar in range(n_pillars):
            row, col = divmod(pillar, 3)
            axes_names = [f"S{sensor}_P{pillar}_{prefix}{a}" for a in ("X", "Y", "Z")]
            aligned = _align_fields(protocol_rows, sdk_rows, axes_names)

            t_sec = [
                ts / 1_000_000
                for ts in aligned.timestamps_us
            ]
            ax = fig.add_subplot(gs[row, col])
            for fi, field in enumerate(aligned.fields):
                axis_letter = field[-1]
                color = AXIS_COLORS.get(axis_letter, "black")
                ax.plot(
                    t_sec, aligned.protocol_matrix[fi],
                    color=color, linewidth=0.5, label=f"{prefix}{axis_letter} (proto)",
                )
                ax.plot(
                    t_sec, aligned.sdk_matrix[fi],
                    color=color, linewidth=0.4, linestyle="--", alpha=0.5,
                    label=f"{prefix}{axis_letter} (SDK)",
                )
            ax.set_title(f"P{pillar}", fontsize=8)
            ax.set_xlabel("Time (s)", fontsize=6)
            ax.set_ylabel(ylabel, fontsize=6)
            _fmt_time_axis(ax, nbins=4)
            ax.tick_params(labelsize=5)
            ax.legend(fontsize=4, frameon=False, loc="upper right")

        fig.suptitle(
            f"Sensor {sensor} — Pillar {plot_label.title()} ({prefix}X/{prefix}Y/{prefix}Z)",
            fontsize=10,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command()
def plot(
    protocol_csv: Annotated[pathlib.Path, typer.Argument(help="protocol.csv 路径")],
    sdk_csv: Annotated[pathlib.Path, typer.Option("--sdk-csv", help="SDK CSV 路径")],
    output: Annotated[pathlib.Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """一键绘制全部对比图：滑移时间序列、全局力、3×3 pillar 力/位移。"""
    out_dir = (output or protocol_csv.parent / DEFAULT_OUTPUT_NAME).parent

    typer.echo(f"--- 载入协议 CSV: {protocol_csv}")
    protocol_rows = load_protocol_rows(protocol_csv)
    typer.echo(f"协议行数: {len(protocol_rows)}")

    typer.echo(f"--- 载入 SDK CSV: {sdk_csv}")
    sdk_rows = load_sdk_rows(sdk_csv)
    typer.echo(f"SDK 行数: {len(sdk_rows)}")

    results: list[tuple[str, pathlib.Path | None, str | None]] = []
    # (label, path-or-None, error-or-None)

    # (1) 滑移时间序列
    try:
        path, skipped = plot_slip_differences(
            protocol_rows, sdk_rows, out_dir / DEFAULT_OUTPUT_NAME,
        )
        results.append(("滑移时间序列", path, None))
        if skipped:
            typer.secho(
                f"  提示: 已跳过 {skipped} 个含 NaN/Inf 的时间戳",
                fg=typer.colors.YELLOW,
            )
    except Exception as exc:
        results.append(("滑移时间序列", None, str(exc)))

    # (2) 全局力
    try:
        path = _plot_global_force(
            protocol_rows, sdk_rows, out_dir / "global_force.png", sensors=(0, 1),
        )
        results.append(("全局力", path, None))
    except Exception as exc:
        results.append(("全局力", None, str(exc)))

    # (3)-(6) pillar 力/位移 × 两个传感器
    for sensor_id in (0, 1):
        for ftype, label in (("force", "pillar force"), ("disp", "pillar disp")):
            try:
                fname = f"pillar_{'force' if ftype == 'force' else 'disp'}_S{sensor_id}.png"
                path = _plot_pillar_grid(
                    protocol_rows, sdk_rows, out_dir / fname,
                    sensor=sensor_id, field_type=ftype,
                )
                results.append((f"S{sensor_id} {label}", path, None))
            except Exception as exc:
                results.append((f"S{sensor_id} {label}", None, str(exc)))

    typer.echo("\n=== 绘图结果 ===")
    for label, path, error in results:
        if error:
            typer.secho(f"  {label}: 失败 — {error}", fg=typer.colors.RED)
        else:
            typer.echo(f"  {label}: {path}")


@app.command()
def global_force(
    protocol_csv: Annotated[pathlib.Path, typer.Argument(help="protocol.csv 路径")],
    sdk_csv: Annotated[pathlib.Path, typer.Option("--sdk-csv", help="SDK CSV 路径")],
    output: Annotated[pathlib.Path | None, typer.Option("--output", "-o")] = None,
    sensor: Annotated[str, typer.Option("--sensor", "-s", help="传感器编号，逗号分隔")] = "0,1",
) -> None:
    """绘制传感器全局力 (GFX/GFY/GFZ) 时间序列，协议 vs SDK 叠绘。"""
    output_path = output or protocol_csv.parent / "global_force.png"
    sensor_ids = tuple(int(s.strip()) for s in sensor.split(","))

    typer.echo(f"--- 载入协议 CSV: {protocol_csv}")
    protocol_rows = load_protocol_rows(protocol_csv)
    typer.echo(f"--- 载入 SDK CSV: {sdk_csv}")
    sdk_rows = load_sdk_rows(sdk_csv)

    try:
        result_path = _plot_global_force(protocol_rows, sdk_rows, output_path, sensors=sensor_ids)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"--- 绘图完成: {result_path}")


@app.command()
def pillar(
    protocol_csv: Annotated[pathlib.Path, typer.Argument(help="protocol.csv 路径")],
    sdk_csv: Annotated[pathlib.Path, typer.Option("--sdk-csv", help="SDK CSV 路径")],
    output: Annotated[pathlib.Path | None, typer.Option("--output", "-o")] = None,
    sensor: Annotated[int, typer.Option("--sensor", "-s", help="传感器编号")] = 0,
    field_type: Annotated[str, typer.Option("--field-type", "-t", help="force 或 disp")] = "force",
) -> None:
    """3×3 网格绘制每个柱子的力或位移时间序列，协议 vs SDK 叠绘。

    使用示例:
        uv run --extra plot python pts_protocol_compare_plot.py pillar \\
            protocol.csv --sdk-csv sdk.csv -s 0 -t force
    """
    if field_type not in ("force", "disp"):
        typer.secho("错误: --field-type 只能是 force 或 disp", err=True)
        raise typer.Exit(1)

    suffix = "force" if field_type == "force" else "disp"
    default_name = f"pillar_{suffix}_S{sensor}.png"
    output_path = output or protocol_csv.parent / default_name

    typer.echo(f"--- 载入协议 CSV: {protocol_csv}")
    protocol_rows = load_protocol_rows(protocol_csv)
    typer.echo(f"--- 载入 SDK CSV: {sdk_csv}")
    sdk_rows = load_sdk_rows(sdk_csv)

    try:
        result_path = _plot_pillar_grid(
            protocol_rows, sdk_rows, output_path, sensor=sensor, field_type=field_type,
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"--- 绘图完成: {result_path}")


_KNOWN_COMMANDS = {"plot", "global-force", "pillar"}
_HELP_FLAGS = {"--help", "--install-completion", "--show-completion"}


def _looks_like_csv_path(arg: str) -> bool:
    """判断参数是否像 CSV 路径而非子命令名。"""
    return arg.endswith(".csv") or arg.startswith("/") or arg.startswith(".")


if __name__ == "__main__":
    # 兼容旧用法: 不带子命令时默认走 plot
    argv = sys.argv[1:]
    if argv and argv[0] not in _KNOWN_COMMANDS and argv[0] not in _HELP_FLAGS:
        if _looks_like_csv_path(argv[0]):
            sys.argv.insert(1, "plot")
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
