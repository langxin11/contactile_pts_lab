#!/usr/bin/env python3
"""对无负载采集数据做功率谱密度分析，观察噪声频段分布。

用于确定软件一阶低通滤波的截止频率：先看噪声在哪个频段，
再结合"要保住多少真实信号"来定 fc。

采集前提（必须在无负载、不触碰、环境稳定的情况下记录）:
    1. 连接后先发 bias 清零，等读数稳定。
    2. 以 1000 Hz 采样记录 10–60 s，保持传感器无负载。
    3. 导出为含 T_us 时间戳列的 CSV（与 protocol.csv / sdk.csv 同格式）。

使用方式（在 python_ws 目录运行）:
    uv run --extra plot python noise_psd_analysis.py \
        ../data/protocol_compare/<id>/protocol.csv \
        --sensor 0

输出:
    在 CSV 同目录生成 <name>_psd.png（PSD 曲线）和
    <name>_psd_cumulative.png（截止频率 vs 残余噪声能量），
    并在终端打印各频段噪声占比，辅助选 fc。
"""

from __future__ import annotations

import pathlib
import sys
from typing import Annotated

import numpy as np
import typer

app = typer.Typer(no_args_is_help=True)

HARDWARE_ANTIALIAS_CUTOFF_HZ = 338.8  # 手册 PTS_2.1_SPEC §5.1，1000 Hz 采样下
HARDWARE_ANTIALIAS_M3DB_HZ = 235.0  # 手册图 5.1，-3dB 点
DEFAULT_SENSOR = 0
DEFAULT_NPERSEG = 1024


def load_timeseries(csv_path: pathlib.Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """读取时序 CSV，返回 `(T_us, 列名->数组)`。

    Args:
        csv_path: 与 protocol.csv / sdk.csv 同格式的 CSV 路径。

    Returns:
        `(时间戳 µs, 各列数值数组)`。

    Raises:
        ValueError: CSV 无 T_us 列或数据为空时抛出。
    """
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    if "T_us" not in header:
        raise ValueError("CSV 缺少 T_us 列，无法推断采样率")
    data = np.loadtxt(csv_path, delimiter=",", skiprows=1, dtype=np.float64)
    if data.ndim != 2 or data.shape[0] < 32:
        raise ValueError("CSV 数据点过少（至少需要 32 行）")
    columns = {name: data[:, idx] for idx, name in enumerate(header)}
    return columns["T_us"], columns


def infer_sampling_rate(t_us: np.ndarray) -> tuple[float, bool]:
    """由时间戳中位数差推断采样率，并检查时间间隔是否均匀。

    Args:
        t_us: 时间戳，单位 µs，shape=(N,)。

    Returns:
        `(采样率 Hz, 是否均匀)`。
    """
    diff_us = np.diff(t_us)
    valid = diff_us[diff_us > 0]
    if valid.size == 0:
        raise ValueError("时间戳没有正间隔，无法推断采样率")
    median_us = np.median(valid)
    fs = 1e6 / median_us
    # 允许 ±20% 抖动，超出视为丢帧/不均匀
    uniform = bool(np.mean(np.abs(valid - median_us) > 0.2 * median_us) < 0.01)
    return float(fs), uniform


def detrend_signal(signal: np.ndarray) -> np.ndarray:
    """去除线性趋势与直流分量，避免低频泄漏污染谱估计。

    Args:
        signal: 原始信号，shape=(N,)。

    Returns:
        去趋势后的零均值信号，shape=(N,)。
    """
    idx = np.arange(signal.size, dtype=np.float64)
    slope, intercept = np.polyfit(idx, signal, 1)
    return signal - (slope * idx + intercept) - float(np.mean(signal - (slope * idx + intercept)))


def welch_psd(signal: np.ndarray, fs: float, nperseg: int) -> tuple[np.ndarray, np.ndarray]:
    """numpy 实现的 Welch 平均周期图（单边功率谱密度，单位²/Hz）。

    与 scipy.signal.welch 的单边默认行为一致：Hann 窗、50% 重叠、
    平均后乘以 2 得到单边谱。

    Args:
        signal: 去趋势后的零均值信号，shape=(N,)。
        fs: 采样率，单位 Hz。
        nperseg: 每段样本数，决定频率分辨率 ≈ fs/nperseg。

    Returns:
        `(频率 Hz, PSD 单位²/Hz)`。
    """
    nperseg = min(nperseg, signal.size)
    window = np.hanning(nperseg)
    normalization = np.sum(window**2)
    hop = nperseg // 2
    nseg = 1 + (signal.size - nperseg) // hop
    frequencies = np.fft.rfftfreq(nperseg, d=1.0 / fs)
    psd = np.zeros(frequencies.size, dtype=np.float64)
    for i in range(nseg):
        segment = signal[i * hop : i * hop + nperseg] * window
        spectrum = np.fft.rfft(segment)
        psd += np.abs(spectrum) ** 2 / normalization
    psd /= nseg
    psd[1:-1] *= 2.0  # 单边谱（DC 与奈奎斯特项不乘 2）
    psd /= fs  # 转为单位²/Hz
    return frequencies, psd


def band_noise_rms(psd: np.ndarray, frequencies: np.ndarray, f_lo: float, f_hi: float) -> float:
    """计算频带 [f_lo, f_hi] 内的 RMS 噪声。

    Args:
        psd: 功率谱密度，单位²/Hz。
        frequencies: 频率轴，单位 Hz。
        f_lo: 频带下限，单位 Hz。
        f_hi: 频带上限，单位 Hz。

    Returns:
        频带内信号标准差（与原始信号同单位）。
    """
    mask = (frequencies >= f_lo) & (frequencies <= f_hi)
    df = frequencies[1] - frequencies[0]
    return float(np.sqrt(np.sum(psd[mask] * df)))


def choose_cutoff_from_cumulative(
    psd: np.ndarray, frequencies: np.ndarray, target_removed_pct: float
) -> float:
    """找到理想低通可移除指定高频噪声占比的最高截止频率。

    把 [f, fs/2] 的能量看作理想砖墙低通会移除的部分。在满足目标占比的
    候选中选最高的 f，避免不必要地压低有效带宽。

    Args:
        psd: 功率谱密度，单位²/Hz。
        frequencies: 频率轴，单位 Hz。
        target_removed_pct: 期望移除的高频噪声能量百分比，范围 (0, 100]。

    Returns:
        满足目标的最高候选截止频率，单位 Hz。

    Raises:
        ValueError: 输入 shape 不一致、频点过少或目标占比越界时抛出。
    """
    if psd.shape != frequencies.shape or frequencies.size < 2:
        raise ValueError("PSD 与频率轴 shape 必须一致且至少包含 2 个频点")
    if not 0.0 < target_removed_pct <= 100.0:
        raise ValueError("target_removed_pct 必须在 (0, 100] 范围内")
    df = frequencies[1] - frequencies[0]
    total = float(np.sum(psd * df))
    if total <= 0.0:
        return float(frequencies[0])
    removable_energy = np.flip(np.cumsum(np.flip(psd * df)))
    target_energy = total * target_removed_pct / 100.0
    candidates = np.flatnonzero(removable_energy >= target_energy)
    return float(frequencies[candidates[-1]])


def render_psd_plots(
    csv_path: pathlib.Path,
    fs: float,
    uniform: bool,
    channels: list[tuple[str, np.ndarray]],
) -> pathlib.Path:
    """绘制 PSD 与累计残余噪声两张图，返回主图路径。

    Args:
        csv_path: 源 CSV 路径，图片输出到其同目录。
        fs: 采样率，单位 Hz。
        uniform: 时间戳是否均匀。
        channels: `(列名, 去趋势信号)` 列表。

    Returns:
        生成的主图路径。
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import scienceplots  # noqa: F401

    nyquist = fs / 2.0
    out_dir = csv_path.parent
    stem = csv_path.stem

    colors = plt.get_cmap("tab10")
    with plt.style.context(["science", "no-latex"]):
        # —— 图 1：PSD ——
        figure, axis = plt.subplots(figsize=(7.0, 4.2), layout="constrained")
        for idx, (name, signal) in enumerate(channels):
            frequencies, psd = welch_psd(signal, fs, DEFAULT_NPERSEG)
            axis.loglog(frequencies[1:], psd[1:], color=colors(idx % 10), label=name)
        axis.axvline(nyquist, color="0.3", linestyle=":", linewidth=1.0)
        axis.text(
            nyquist * 0.98,
            axis.get_ylim()[1] * 0.9,
            f"Nyquist {nyquist:.0f} Hz",
            ha="right",
            fontsize=8,
            color="0.2",
        )
        axis.axvline(HARDWARE_ANTIALIAS_M3DB_HZ, color="tab:red", linestyle="--", linewidth=1.0)
        axis.axvline(HARDWARE_ANTIALIAS_CUTOFF_HZ, color="tab:red", linestyle=":", linewidth=1.0)
        axis.text(
            HARDWARE_ANTIALIAS_M3DB_HZ,
            axis.get_ylim()[0] * 1.2,
            "硬件抗混叠 -3dB 235Hz",
            fontsize=8,
            color="tab:red",
        )
        axis.text(
            HARDWARE_ANTIALIAS_CUTOFF_HZ,
            axis.get_ylim()[1] * 0.5,
            "338.8Hz",
            fontsize=8,
            color="tab:red",
            rotation=90,
        )
        axis.set_xlabel("Frequency (Hz)")
        axis.set_ylabel(r"PSD $(\mathrm{unit}^2/\mathrm{Hz})$")
        axis.set_title(f"{csv_path.name}  PSD（fs={fs:.0f} Hz）")
        axis.legend(fontsize="x-small")
        figure.savefig(out_dir / f"{stem}_psd.png", dpi=200)
        plt.close(figure)

        # —— 图 2：理想低通可移除的高频噪声 ——
        figure, axis = plt.subplots(figsize=(7.0, 4.2), layout="constrained")
        for idx, (name, signal) in enumerate(channels):
            frequencies, psd = welch_psd(signal, fs, DEFAULT_NPERSEG)
            df = frequencies[1] - frequencies[0]
            removable = np.flip(np.cumsum(np.flip(psd * df)))
            total = removable[0] if removable[0] > 0.0 else 1.0
            axis.semilogx(
                frequencies[1:],
                removable[1:] / total * 100.0,
                color=colors(idx % 10),
                label=name,
            )
        axis.axhline(95.0, color="0.5", linestyle=":", linewidth=0.8)
        axis.axhline(99.0, color="0.5", linestyle=":", linewidth=0.8)
        axis.set_xlabel("Candidate cutoff fc (Hz)")
        axis.set_ylabel("Ideally removable noise above fc (%)")
        axis.set_title("理想低通可移除的 fc 以上噪声占比")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(fontsize="x-small")
        cumulative_path = out_dir / f"{stem}_psd_cumulative.png"
        figure.savefig(cumulative_path, dpi=200)
        plt.close(figure)

    timestamp_status = "均匀" if uniform else "存在抖动/丢帧，结果仅供参考"
    typer.echo(f"提示: 时间戳{timestamp_status}（中位间隔 {1e6 / fs:.0f} µs）")
    return out_dir / f"{stem}_psd.png"


def run_noise_analysis(
    csv_path: pathlib.Path,
    sensor: int,
    columns: list[str] | None,
) -> pathlib.Path:
    """执行噪声 PSD 分析主流程。

    Args:
        csv_path: 时序 CSV 路径。
        sensor: 传感器索引，0 或 1。
        columns: 要分析的列名；None 时自动选全局三轴力。

    Returns:
        生成的主图路径。

    Raises:
        ValueError: 数据或配置无效时抛出。
    """
    t_us, all_columns = load_timeseries(csv_path)
    fs, uniform = infer_sampling_rate(t_us)

    if columns is None or len(columns) == 0:
        candidates = [f"S{sensor}_G_{axis}" for axis in ("FX", "FY", "FZ")]
        columns = [candidate for candidate in candidates if candidate in all_columns]
        if not columns:
            columns = list(all_columns.keys())[1:3]

    missing = [c for c in columns if c not in all_columns]
    if missing:
        raise ValueError(f"CSV 缺少列: {', '.join(missing)}")

    channels: list[tuple[str, np.ndarray]] = []
    for name in columns:
        signal = detrend_signal(all_columns[name])
        rms = float(np.std(signal))
        channels.append((name, signal))
        typer.echo(f"{name:<10} RMS = {rms:.6g}（总噪声水平）")

    # 分频段噪声占比（0–10 Hz 主要是漂移/温度；>200 Hz 是可滤掉的高频噪声）
    bands = [
        (0.0, 10.0, "0–10 Hz（漂移/温度，低通滤不掉）"),
        (10.0, 50.0, "10–50 Hz（慢变化噪声）"),
        (50.0, 235.0, "50–235 Hz（有效频带内噪声）"),
        (235.0, fs / 2.0, "235 Hz–Nyquist（硬件抗混叠以上，软件可压）"),
    ]
    for name, signal in channels:
        frequencies, psd = welch_psd(signal, fs, DEFAULT_NPERSEG)
        parts = [(label, band_noise_rms(psd, frequencies, lo, hi)) for lo, hi, label in bands]
        total_rms = float(np.sqrt(sum(p[1] ** 2 for p in parts)))
        desc = " | ".join(
            f"{label} {part_rms / total_rms * 100:.1f}%" if total_rms > 0.0 else f"{label} 0.0%"
            for label, part_rms in parts
        )
        typer.echo(f"{name:<10} 分频段 RMS 占比: {desc}")

    for name, signal in channels:
        frequencies, psd = welch_psd(signal, fs, DEFAULT_NPERSEG)
        fc_95pct = choose_cutoff_from_cumulative(psd, frequencies, 95.0)
        fc_99pct = choose_cutoff_from_cumulative(psd, frequencies, 99.0)
        typer.echo(
            f"{name:<10} 理想低通候选: fc≈{fc_95pct:.0f} Hz 可移除 95% 高频噪声, "
            f"fc≈{fc_99pct:.0f} Hz 可移除 99%"
        )

    return render_psd_plots(csv_path, fs, uniform, channels)


@app.command()
def analyze(
    csv_path: Annotated[
        pathlib.Path,
        typer.Argument(help="时序 CSV 路径（protocol.csv / sdk.csv 格式）"),
    ],
    sensor: Annotated[int, typer.Option("--sensor", "-s", help="传感器索引 0/1")] = DEFAULT_SENSOR,
    column: Annotated[
        list[str] | None,
        typer.Option("--column", "-c", help="指定分析列，可多次传入"),
    ] = None,
) -> None:
    """分析无负载采集数据的噪声频谱，辅助选择软件低通截止频率。"""
    try:
        main_path = run_noise_analysis(csv_path, sensor, column)
    except OSError as exc:
        typer.secho(f"错误: 无法读写文件: {exc}", err=True)
        raise typer.Exit(1) from exc
    except (ImportError, ValueError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"PSD 图: {main_path}")
    typer.echo(f"累计残余噪声图: {main_path.with_name(main_path.stem + '_psd_cumulative.png')}")


if __name__ == "__main__":
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
