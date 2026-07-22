#!/usr/bin/env python3
"""交互采集物体质量与 Contactile PTS 法向压力。

使用方式（在 python_ws 目录运行）:
    uv run --extra experiment python force_accuracy_measure.py \
        --config ../config/force_accuracy.yaml

查看参数:
    uv run --extra experiment python force_accuracy_measure.py --help
"""

from __future__ import annotations

import csv
import os
import pathlib
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Annotated, Any, TextIO

import numpy as np
import typer
import yaml

from pts_protocol_compare import SerialTeeRelay, parse_capture_packets

DEFAULT_SENSOR_COUNT = 2
STANDARD_GRAVITY_M_PER_SEC2 = 9.80665
BYTE_SIZE_CHAR = "\u0008"
PARITY_NONE = 0
FIRST_SAMPLE_TIMEOUT_SEC = 5.0
FIRST_SAMPLE_POLL_SEC = 0.01
DEFAULT_CONFIG_PATH = pathlib.Path("../config/force_accuracy.yaml")

app = typer.Typer(no_args_is_help=True)

SDK_HEARTBEAT_MESSAGE = b"INF: Still sampling...\n"


class _ByteSequenceFilter:
    """跨读取块删除一个精确字节序列，同时立即转发其他内容。"""

    def __init__(self, target: bytes) -> None:
        self._target = target
        self._pending = bytearray()

    def feed(self, data: bytes) -> bytes:
        """过滤一个字节块，并保留可能跨块的目标前缀。"""
        output = bytearray()
        for value in data:
            self._pending.append(value)
            while self._pending and not self._target.startswith(self._pending):
                output.append(self._pending[0])
                del self._pending[0]
            if self._pending == self._target:
                self._pending.clear()
        return bytes(output)

    def finish(self) -> bytes:
        """返回流结束时尚未匹配成目标的字节。"""
        remaining = bytes(self._pending)
        self._pending.clear()
        return remaining


class _SdkStdoutFilter:
    """分流 Python 交互输出，并过滤原厂后台线程心跳。"""

    def __init__(self) -> None:
        self._saved_stdout_fd: int | None = None
        self._original_stdout: TextIO | None = None
        self._terminal_stdout: TextIO | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """仅把文件描述符 1 接到过滤器，Python stdout 仍直达原终端。"""
        if self._saved_stdout_fd is not None:
            return
        original_stdout = sys.stdout
        original_stdout.flush()
        read_fd, write_fd = os.pipe()
        saved_stdout_fd = os.dup(1)
        terminal_fd = os.dup(saved_stdout_fd)
        terminal_stdout = os.fdopen(
            terminal_fd,
            "w",
            buffering=1,
            encoding=getattr(original_stdout, "encoding", None) or "utf-8",
            errors=getattr(original_stdout, "errors", None) or "strict",
        )
        thread = threading.Thread(
            target=self._relay,
            args=(read_fd, saved_stdout_fd),
            daemon=True,
        )
        thread.start()
        os.dup2(write_fd, 1)
        os.close(write_fd)

        self._saved_stdout_fd = saved_stdout_fd
        self._original_stdout = original_stdout
        self._terminal_stdout = terminal_stdout
        self._thread = thread
        sys.stdout = terminal_stdout

    def stop(self) -> None:
        """恢复 stdout，并等待过滤线程转发完剩余原生日志。"""
        if self._saved_stdout_fd is None:
            return
        if self._terminal_stdout is not None:
            self._terminal_stdout.flush()
        saved_stdout_fd = self._saved_stdout_fd
        os.dup2(saved_stdout_fd, 1)
        if self._original_stdout is not None:
            sys.stdout = self._original_stdout
        if self._terminal_stdout is not None:
            self._terminal_stdout.close()
        if self._thread is not None:
            self._thread.join()
        os.close(saved_stdout_fd)
        self._saved_stdout_fd = None
        self._original_stdout = None
        self._terminal_stdout = None
        self._thread = None

    @staticmethod
    def _write_all(fd: int, data: bytes) -> None:
        """完整写出过滤后的字节，避免短写截断终端文本。"""
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])

    def _relay(self, read_fd: int, output_fd: int) -> None:
        """从 stdout 管道读取并过滤原厂心跳。"""
        sequence_filter = _ByteSequenceFilter(SDK_HEARTBEAT_MESSAGE)
        try:
            while chunk := os.read(read_fd, 4096):
                self._write_all(output_fd, sequence_filter.feed(chunk))
            self._write_all(output_fd, sequence_filter.finish())
        finally:
            os.close(read_fd)


@dataclass(frozen=True)
class ExperimentConfig:
    """质量—压力实验配置。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        rate_hz: 控制器采样率，单位 Hz。
        sensor_index: 串口所连接控制器中的传感器索引。
        normal_axis: sensor frame 法向轴 x/y/z。
        compression_sign: 把法向力换算成正压力的符号。
        target_masses_g: 默认测量顺序中的实际质量，单位 g；重复值表示重复测量。
        window_sec: 稳定判断窗口长度，单位 s。
        timeout_sec: 单点等待稳定的最长时间，单位 s。
        std_threshold_n: 稳定窗口最大标准差，单位 N。
        drift_threshold_n_per_sec: 稳定窗口最大绝对漂移，单位 N/s。
        output_dir: CSV 输出目录。
        auto_plot: 测量结束后是否调用离线绘图钩子。
    """

    port: str
    baud_rate: int
    rate_hz: int
    sensor_index: int
    normal_axis: str
    compression_sign: int
    target_masses_g: tuple[float, ...]
    window_sec: float
    timeout_sec: float
    std_threshold_n: float
    drift_threshold_n_per_sec: float
    output_dir: pathlib.Path
    auto_plot: bool


def load_experiment_config(config_path: pathlib.Path) -> ExperimentConfig:
    """读取质量—压力实验 YAML。

    Args:
        config_path: YAML 配置文件路径。

    Returns:
        经过类型转换的实验配置；相对输出路径以配置文件目录为基准。

    Raises:
        OSError: 配置文件无法读取时抛出。
        ValueError: YAML 结构或字段值无效时抛出。
    """
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        connection = raw["connection"]
        stability = raw["stability"]
        measurement = raw["measurement"]
        output = raw["output"]
        plot = raw["plot"]
        target_masses_g = tuple(float(mass_g) for mass_g in measurement["target_masses_g"])
        if any(not np.isfinite(mass_g) or mass_g < 0 for mass_g in target_masses_g):
            raise ValueError("measurement.target_masses_g 必须都是有限的非负数值")
        output_dir = pathlib.Path(output["directory"])
        if not output_dir.is_absolute():
            output_dir = (config_path.resolve().parent / output_dir).resolve()
        return ExperimentConfig(
            port=str(connection["port"]),
            baud_rate=int(connection["baud_rate"]),
            rate_hz=int(connection["rate_hz"]),
            sensor_index=int(connection["sensor_index"]),
            normal_axis=str(measurement["normal_axis"]).lower(),
            compression_sign=int(measurement["compression_sign"]),
            target_masses_g=target_masses_g,
            window_sec=float(stability["window_sec"]),
            timeout_sec=float(stability["timeout_sec"]),
            std_threshold_n=float(stability["std_threshold_n"]),
            drift_threshold_n_per_sec=float(stability["drift_threshold_n_per_sec"]),
            output_dir=output_dir,
            auto_plot=bool(plot["auto"]),
        )
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"实验配置结构或字段无效: {exc}") from exc


@dataclass(frozen=True)
class Measurement:
    """一个稳定质量点的测量结果。

    Args:
        record_id: 会话内单调递增的记录编号，用于追溯和逻辑排除。
        timestamp: 主机记录时间，ISO 8601 格式。
        sensor_index: 串口所连接控制器中的传感器索引。
        mass_g: 电子秤测得质量，单位 g。
        expected_force_n: 标准重力下的理论压力，单位 N。
        raw_normal_force_n: sensor frame 法向轴原始均值，单位 N。
        measured_pressure_n: 按受压符号换算后的压力，单位 N。
        std_force_n: 稳定窗口标准差，单位 N。
        drift_n_per_sec: 稳定窗口线性漂移，单位 N/s。
        error_n: 实测压力减理论压力，单位 N。
        relative_error_percent: 相对理论压力的误差，单位 %。
        sample_count: 稳定窗口内有效帧数。
        settle_time_sec: 从开始测量到稳定的时间，单位 s。
        window_start_us: 稳定窗口起始控制器时间戳，单位 µs。
        window_end_us: 稳定窗口结束控制器时间戳，单位 µs。
        elapsed_s: 从首个测量窗口起始到本窗口起始的相对时间，单位 s。
        protocol_raw_normal_force_n: 自研协议解析的法向力均值，单位 N。
        protocol_measured_pressure_n: 自研协议换算后的压力，单位 N。
        protocol_std_force_n: 自研协议窗口标准差，单位 N。
        protocol_error_n: 自研协议实测压力减理论压力，单位 N。
        sdk_protocol_diff_n: SDK 压力减自研协议压力，单位 N。
        protocol_sample_count: 自研协议匹配的样本数。
        included: 是否纳入绘图和统计。
        exclusion_reason: 逻辑排除原因；保留原始记录以支持实验追溯。
    """

    record_id: int
    timestamp: str
    sensor_index: int
    mass_g: float
    expected_force_n: float
    raw_normal_force_n: float
    measured_pressure_n: float
    std_force_n: float
    drift_n_per_sec: float
    error_n: float
    relative_error_percent: float
    sample_count: int
    settle_time_sec: float
    window_start_us: int
    window_end_us: int
    elapsed_s: float = 0.0
    protocol_raw_normal_force_n: float = float("nan")
    protocol_measured_pressure_n: float = float("nan")
    protocol_std_force_n: float = float("nan")
    protocol_error_n: float = float("nan")
    sdk_protocol_diff_n: float = float("nan")
    protocol_sample_count: int = 0
    included: bool = True
    exclusion_reason: str = ""


def parse_mass_input(value: str) -> float | None:
    """解析用户输入的质量或退出命令。

    Args:
        value: 终端输入；`q` 表示结束，否则应为非负质量，单位 g。

    Returns:
        质量值，单位 g；输入 `q` 时返回 None。

    Raises:
        ValueError: 输入不是 `q` 或非负数值时抛出。
    """
    normalized = value.strip().lower()
    if normalized == "q":
        return None
    try:
        mass_g = float(normalized)
    except ValueError as exc:
        raise ValueError("请输入非负质量数值，或输入 q 退出") from exc
    if not np.isfinite(mass_g) or mass_g < 0:
        raise ValueError("质量必须是有限的非负数值")
    return mass_g

def parse_record_command(value: str) -> tuple[str, int | None] | None:
    """解析会话中的撤销或逻辑排除命令。

    Args:
        value: 终端输入；`u` 撤销最近有效记录，`d <记录号>` 排除指定记录。

    Returns:
        `(命令, 记录号)`；不属于记录管理命令时返回 None。

    Raises:
        ValueError: `d` 命令缺少有效的正整数记录号时抛出。
    """
    parts = value.strip().lower().split()
    if parts == ["u"]:
        return "undo", None
    if not parts or parts[0] != "d":
        return None
    if len(parts) != 2:
        raise ValueError("排除命令格式为 d <记录号>，例如 d 3")
    try:
        record_id = int(parts[1])
    except ValueError as exc:
        raise ValueError("记录号必须是正整数，例如 d 3") from exc
    if record_id <= 0:
        raise ValueError("记录号必须是正整数，例如 d 3")
    return "exclude", record_id


def exclude_measurement(
    measurements: list[Measurement], record_id: int, reason: str
) -> tuple[list[Measurement], Measurement]:
    """逻辑排除一个已记录质量点，并保留原始数据以供审计。

    Args:
        measurements: 本会话的全部测量记录。
        record_id: 要排除的会话记录编号。
        reason: 人工排除原因。

    Returns:
        更新后的记录列表和刚被排除的记录。

    Raises:
        ValueError: 记录不存在、已经排除，或原因为空时抛出。
    """
    if not reason.strip():
        raise ValueError("排除原因不能为空")
    for index, measurement in enumerate(measurements):
        if measurement.record_id != record_id:
            continue
        if not measurement.included:
            raise ValueError(f"记录 {record_id} 已经排除")
        excluded = replace(measurement, included=False, exclusion_reason=reason)
        updated = [*measurements]
        updated[index] = excluded
        return updated, excluded
    raise ValueError(f"未找到记录 {record_id}")


def exclude_latest_measurement(measurements: list[Measurement]) -> tuple[list[Measurement], Measurement]:
    """逻辑撤销最近一条有效记录。

    Args:
        measurements: 本会话的全部测量记录。

    Returns:
        更新后的记录列表和刚被撤销的记录。

    Raises:
        ValueError: 当前没有有效记录可撤销时抛出。
    """
    for measurement in reversed(measurements):
        if measurement.included:
            return exclude_measurement(measurements, measurement.record_id, "撤销：质量或放置错误")
    raise ValueError("当前没有可撤销的有效记录")

def analyze_window(
    timestamps_us: np.ndarray,
    forces_n: np.ndarray,
) -> tuple[float, float, float]:
    """计算稳定窗口的均值、标准差和漂移。

    Args:
        timestamps_us: 控制器时间戳，单位 µs，shape=(N,)。
        forces_n: sensor frame 法向力，单位 N，shape=(N,)。

    Returns:
        `(均值 N, 标准差 N, 漂移 N/s)`。

    Raises:
        ValueError: 样本不足或时间戳没有递增跨度时抛出。
    """
    if timestamps_us.size < 2 or forces_n.size != timestamps_us.size:
        raise ValueError("稳定窗口至少需要两个相互对应的样本")
    elapsed_sec = (timestamps_us - timestamps_us[0]) / 1_000_000.0
    if elapsed_sec[-1] <= 0:
        raise ValueError("稳定窗口时间戳必须递增")
    slope_n_per_sec = float(np.polyfit(elapsed_sec, forces_n, 1)[0])
    return float(np.mean(forces_n)), float(np.std(forces_n, ddof=1)), slope_n_per_sec


def collect_stable_force(
    sensor: Any,
    axis_index: int,
    rate_hz: int,
    window_sec: float,
    timeout_sec: float,
    std_threshold_n: float,
    drift_threshold_n_per_sec: float,
) -> tuple[float, float, float, int, float, int, int]:
    """持续读取 SDK 缓存，直到法向力窗口满足稳定条件。

    Args:
        sensor: 官方 SDK 的 PTSDKSensor 数据容器。
        axis_index: sensor frame 法向轴索引，0/1/2 对应 x/y/z。
        rate_hz: 控制器采样率，单位 Hz。
        window_sec: 稳定判断窗口长度，单位 s。
        timeout_sec: 等待稳定的最长时间，单位 s。
        std_threshold_n: 稳定窗口允许的最大标准差，单位 N。
        drift_threshold_n_per_sec: 稳定窗口允许的最大绝对漂移，单位 N/s。

    Returns:
        `(均值 N, 标准差 N, 漂移 N/s, 样本数, 稳定耗时 s, 起始 µs, 结束 µs)`。

    Raises:
        TimeoutError: 指定时间内读数未达到稳定条件时抛出。
        ValueError: 稳定参数无效时抛出。
    """
    if window_sec <= 0 or timeout_sec <= 0:
        raise ValueError("window 和 timeout 必须大于 0")
    if std_threshold_n < 0 or drift_threshold_n_per_sec < 0:
        raise ValueError("稳定阈值不能为负数")

    window_samples = max(2, round(window_sec * rate_hz))
    samples: deque[tuple[int, float]] = deque(maxlen=window_samples)
    started_at = time.monotonic()
    last_timestamp_us = -1
    poll_sec = max(0.0002, 0.5 / rate_hz)

    while time.monotonic() - started_at < timeout_sec:
        timestamp_us = int(sensor.getTimestamp_us())
        if timestamp_us > 0 and timestamp_us != last_timestamp_us:
            force = sensor.getGlobalForce()  # shape=(3,), sensor frame，单位 N。
            samples.append((timestamp_us, float(force[axis_index])))
            last_timestamp_us = timestamp_us
        if len(samples) == window_samples:
            timestamps = np.array([sample[0] for sample in samples], dtype=np.float64)
            forces = np.array([sample[1] for sample in samples], dtype=np.float64)
            mean_n, std_n, drift_n_per_sec = analyze_window(timestamps, forces)
            if std_n <= std_threshold_n and abs(drift_n_per_sec) <= drift_threshold_n_per_sec:
                return (
                    mean_n,
                    std_n,
                    drift_n_per_sec,
                    len(samples),
                    time.monotonic() - started_at,
                    int(timestamps[0]),
                    int(timestamps[-1]),
                )
        time.sleep(poll_sec)
    raise TimeoutError(f"{timeout_sec:.1f} s 内读数未稳定")


def build_session_dir(output_root: pathlib.Path) -> pathlib.Path:
    """创建不会覆盖旧实验的时间戳会话目录。

    Args:
        output_root: 所有实验会话的根目录。

    Returns:
        本次实验新建的时间戳目录。

    Raises:
        OSError: 目录无法创建，或极端情况下目录名冲突时抛出。
    """
    session_name = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    session_dir = output_root / session_name
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir


def enrich_protocol_measurements(
    measurements: list[Measurement],
    capture_path: pathlib.Path,
    sensor_index: int,
    axis_index: int,
    compression_sign: int,
) -> list[Measurement]:
    """用同一稳定时间窗内的原始抓包补齐自研协议结果。

    Args:
        measurements: 官方 SDK 已记录的稳定测量点。
        capture_path: 控制器到主机方向的原始字节抓包路径。
        sensor_index: 要分析的传感器索引。
        axis_index: sensor frame 法向轴索引，0/1/2 对应 x/y/z。
        compression_sign: 把法向力换算成正压力的符号，取 -1 或 1。

    Returns:
        按控制器时间戳窗口补齐自研协议字段的新测量列表。

    Raises:
        OSError: 原始抓包无法读取时抛出。
        ValueError: 抓包内容无法按协议解析时抛出。
    """
    if not measurements or not capture_path.exists():
        return measurements
    packets = parse_capture_packets(capture_path.read_bytes())
    enriched: list[Measurement] = []
    for measurement in measurements:
        values = [
            float(packet.global_forces[sensor_index][axis_index])
            for packet in packets
            if measurement.window_start_us <= packet.timestamp_us <= measurement.window_end_us
            and sensor_index < len(packet.global_forces)
        ]
        if not values:
            enriched.append(measurement)
            continue
        raw_normal_force_n = float(np.mean(values))
        std_force_n = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        measured_pressure_n = compression_sign * raw_normal_force_n
        enriched.append(
            replace(
                measurement,
                protocol_raw_normal_force_n=raw_normal_force_n,
                protocol_measured_pressure_n=measured_pressure_n,
                protocol_std_force_n=std_force_n,
                protocol_error_n=measured_pressure_n - measurement.expected_force_n,
                sdk_protocol_diff_n=measurement.measured_pressure_n - measured_pressure_n,
                protocol_sample_count=len(values),
            )
        )
    return enriched


def save_measurements(
    measurements: list[Measurement], output_dir: pathlib.Path
) -> pathlib.Path | None:
    """把已有测量点写入 CSV。

    Args:
        measurements: 当前会话已完成的测量点。
        output_dir: CSV 输出目录。

    Returns:
        写入的 CSV 路径；没有测量点时返回 None。
    """
    if not measurements:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "measurements.csv"
    temporary_path = output_dir / "measurements.csv.tmp"
    with temporary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(measurements[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(measurement) for measurement in measurements)
    # 先完整写临时文件再替换，避免中断时留下半个 CSV。
    temporary_path.replace(csv_path)
    return csv_path


def run_plot_hook(csv_path: pathlib.Path, config_path: pathlib.Path) -> bool:
    """在独立进程中调用离线绘图脚本。

    Args:
        csv_path: 测量 CSV 路径。
        config_path: 实验 YAML 路径。

    Returns:
        绘图进程成功时返回 True。
    """
    plot_script = pathlib.Path(__file__).with_name("force_accuracy_plot.py")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(plot_script),
                str(csv_path),
                "--config",
                str(config_path),
            ],
            check=False,
        )
    except OSError as exc:
        typer.secho(f"警告: 无法启动绘图钩子: {exc}；CSV 已安全保存: {csv_path}", err=True)
        return False
    if result.returncode != 0:
        typer.secho(
            f"警告: 自动绘图失败（退出码 {result.returncode}），CSV 已安全保存: {csv_path}",
            err=True,
        )
        return False
    return True


def _sdk_sampling_rate(sdk: Any, rate_hz: int) -> int:
    """把采样率映射为官方 SDK 常量。"""
    rate_map = {
        100: sdk.PTSDKConstants.SAMP_RATE_100,
        250: sdk.PTSDKConstants.SAMP_RATE_250,
        500: sdk.PTSDKConstants.SAMP_RATE_500,
        1000: sdk.PTSDKConstants.SAMP_RATE_1000,
    }
    try:
        return rate_map[rate_hz]
    except KeyError as exc:
        raise ValueError("rate 仅支持 100/250/500/1000 Hz") from exc


def _wait_for_first_sample(sensor: Any, timeout_sec: float) -> None:
    """等待 SDK 后台线程收到首帧，避免对未初始化缓存执行 Bias 后测量。"""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if int(sensor.getTimestamp_us()) > 0:
            return
        time.sleep(FIRST_SAMPLE_POLL_SEC)
    raise TimeoutError(f"{timeout_sec:.1f} s 内未收到第一帧有效数据")


def run_accuracy_session(
    port: str,
    baud_rate: int,
    rate_hz: int,
    sensor_index: int,
    normal_axis: str,
    compression_sign: int,
    window_sec: float,
    timeout_sec: float,
    std_threshold_n: float,
    drift_threshold_n_per_sec: float,
    output_dir: pathlib.Path,
    auto_plot: bool,
    config_path: pathlib.Path,
    target_masses_g: tuple[float, ...],
    interactive: bool,
) -> int:
    """连接官方 SDK 并运行交互式质量—压力测量会话。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        rate_hz: 控制器采样率，单位 Hz。
        sensor_index: 串口所连接控制器中的传感器索引。
        normal_axis: sensor frame 法向轴 x/y/z。
        compression_sign: 把法向力换算成正压力的符号，取 -1 或 1。
        window_sec: 稳定判断窗口长度，单位 s。
        timeout_sec: 单点等待稳定的最长时间，单位 s。
        std_threshold_n: 稳定窗口最大标准差，单位 N。
        drift_threshold_n_per_sec: 稳定窗口最大绝对漂移，单位 N/s。
        output_dir: 所有实验会话的根目录；本次结果写入其时间戳子目录。
        auto_plot: 测量结束后是否自动调用绘图钩子。
        config_path: 绘图钩子复用的 YAML 配置路径。
        target_masses_g: 默认测量顺序中的实际质量，单位 g。
        interactive: 是否忽略默认质量数组，改为在终端逐项输入质量。

    Returns:
        进程退出码，0 表示正常结束。
    """
    if not os.path.exists(port):
        typer.secho(f"错误: 设备 {port} 不存在，请检查连接和权限", err=True)
        return 1
    if not 0 <= sensor_index < DEFAULT_SENSOR_COUNT:
        typer.secho(f"错误: sensor 必须在 0..{DEFAULT_SENSOR_COUNT - 1} 之间", err=True)
        return 1
    if normal_axis not in {"x", "y", "z"}:
        typer.secho("错误: normal-axis 仅支持 x/y/z", err=True)
        return 1
    if compression_sign not in {-1, 1}:
        typer.secho("错误: compression-sign 仅支持 -1 或 1", err=True)
        return 1

    try:
        import PTSDK_CXX_Pybind as sdk
    except ImportError:
        typer.secho("错误: 缺少官方 SDK，请使用 uv run --extra experiment 运行", err=True)
        return 1

    sensors = tuple(sdk.PTSDKSensor() for _ in range(DEFAULT_SENSOR_COUNT))
    sensor = sensors[sensor_index]
    listener = sdk.PTSDKListener(logFlag=False)
    for registered_sensor in sensors:
        # Hub 默认可能同时输出 SEN0/SEN1，全部注册可避免 SDK 解析异常。
        listener.addSensor(registered_sensor)

    session_dir = build_session_dir(output_dir)
    capture_path = session_dir / "capture_raw.bin"
    relay = SerialTeeRelay(port=port, baud_rate=baud_rate, capture_path=capture_path)
    relay_started = False
    connected = False
    measurements: list[Measurement] = []
    stdout_filter = _SdkStdoutFilter()
    stdout_filter.start()
    axis_index = {"x": 0, "y": 1, "z": 2}[normal_axis]
    try:
        relay_started = True
        relay.start()
        if relay.virtual_port is None:
            raise RuntimeError("串口中继未创建虚拟端口")
        result = listener.connectAndStartListening(
            relay.virtual_port, baud_rate, PARITY_NONE, BYTE_SIZE_CHAR, True
        )
        if result != 0:
            raise RuntimeError(f"无法连接串口，错误码 {result}")
        connected = True
        listener.setSamplingRate(_sdk_sampling_rate(sdk, rate_hz))
        _wait_for_first_sample(sensor, FIRST_SAMPLE_TIMEOUT_SEC)
        typer.echo(f"已连接 SEN{sensor_index}，法向轴为 {normal_axis}")

        confirmation = (
            input("请确认传感器完全空载，按 Enter 执行 Bias；输入 q 退出: ").strip().lower()
        )
        if confirmation == "q":
            return 0
        if not listener.sendBiasRequest():
            raise RuntimeError("Bias 请求失败")
        typer.echo("Bias 完成。测量期间请勿再次置零。")

        session_start_us: int | None = None
        scheduled_index = 0
        if not interactive:
            typer.echo(f"将按配置依次测量 {len(target_masses_g)} 个质量点；使用 --interactive 可手动输入。")
        while True:
            if interactive:
                try:
                    user_input = input(
                        "输入质量（g）；u 撤销上一条；d <记录号> 排除；q 保存并退出: "
                    )
                    command = parse_record_command(user_input)
                    if command is not None:
                        if command[0] == "undo":
                            measurements, excluded = exclude_latest_measurement(measurements)
                        else:
                            assert command[1] is not None
                            measurements, excluded = exclude_measurement(
                                measurements, command[1], "人工排除：质量或放置错误"
                            )
                        save_measurements(measurements, session_dir)
                        typer.echo(f"已排除记录 {excluded.record_id}: {excluded.mass_g:g} g")
                        continue
                    mass_g = parse_mass_input(user_input)
                except ValueError as exc:
                    typer.secho(f"输入错误: {exc}", err=True)
                    continue
                if mass_g is None:
                    break
            else:
                if scheduled_index >= len(target_masses_g):
                    break
                mass_g = target_masses_g[scheduled_index]
                typer.echo(f"第 {scheduled_index + 1}/{len(target_masses_g)} 个质量点: {mass_g:g} g")

            confirmation = input(
                f"请将 {mass_g:g} g 物体放到传感器固定位置，放稳后按 Enter；"
                "u 撤销上一条；d <记录号> 排除；q 退出: "
            ).strip()
            try:
                command = parse_record_command(confirmation)
                if command is not None:
                    if command[0] == "undo":
                        measurements, excluded = exclude_latest_measurement(measurements)
                        if not interactive and scheduled_index > 0:
                            scheduled_index -= 1
                    else:
                        assert command[1] is not None
                        measurements, excluded = exclude_measurement(
                            measurements, command[1], "人工排除：质量或放置错误"
                        )
                    save_measurements(measurements, session_dir)
                    typer.echo(f"已排除记录 {excluded.record_id}: {excluded.mass_g:g} g")
                    continue
            except ValueError as exc:
                typer.secho(f"输入错误: {exc}", err=True)
                continue
            confirmation = confirmation.lower()
            if confirmation == "q":
                break
            typer.echo("正在等待读数稳定……")
            try:
                (
                    mean_n,
                    std_n,
                    drift_n_per_sec,
                    sample_count,
                    settle_time_sec,
                    window_start_us,
                    window_end_us,
                ) = collect_stable_force(
                    sensor,
                    axis_index,
                    rate_hz,
                    window_sec,
                    timeout_sec,
                    std_threshold_n,
                    drift_threshold_n_per_sec,
                )
            except TimeoutError as exc:
                typer.secho(f"警告: {exc}，本质量点未记录，请调整物体后重试", err=True)
                continue

            expected_force_n = mass_g / 1000.0 * STANDARD_GRAVITY_M_PER_SEC2
            measured_pressure_n = compression_sign * mean_n
            error_n = measured_pressure_n - expected_force_n
            relative_error_percent = (
                error_n / expected_force_n * 100.0 if expected_force_n else float("nan")
            )
            if session_start_us is None:
                session_start_us = window_start_us
            elapsed_s = (window_start_us - session_start_us) / 1_000_000.0
            measurement = Measurement(
                record_id=len(measurements) + 1,
                timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                sensor_index=sensor_index,
                mass_g=mass_g,
                expected_force_n=expected_force_n,
                raw_normal_force_n=mean_n,
                measured_pressure_n=measured_pressure_n,
                std_force_n=std_n,
                drift_n_per_sec=drift_n_per_sec,
                error_n=error_n,
                relative_error_percent=relative_error_percent,
                sample_count=sample_count,
                settle_time_sec=settle_time_sec,
                window_start_us=window_start_us,
                window_end_us=window_end_us,
                elapsed_s=elapsed_s,
            )
            measurements.append(measurement)
            save_measurements(measurements, session_dir)
            typer.echo(
                f"已记录 #{measurement.record_id}: {mass_g:g} g -> {measured_pressure_n:.4f} N "
                f"(理论 {expected_force_n:.4f} N, 标准差 {std_n:.4f} N)"
            )
            typer.echo("请移除物体；发现质量或放置错误可输入 u 或 d <记录号>。")
            if not interactive:
                scheduled_index += 1
    except PermissionError:
        typer.secho(f"错误: 没有权限访问 {port}，请检查 dialout 组权限", err=True)
        return 1
    except (EOFError, KeyboardInterrupt):
        # 终端关闭或 Ctrl-C 时仍保存已完成测量并进入统一串口释放路径。
        typer.secho("测量已中止，正在保存已有结果", err=True)
        return 130
    except (OSError, RuntimeError, ValueError, TimeoutError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        return 1
    finally:
        # 每项清理独立执行，避免某个第三方释放接口异常后真实串口仍被占用。
        if connected:
            try:
                listener.stopListeningAndDisconnect()
                typer.echo("SDK 已释放虚拟串口")
            except Exception as exc:
                # pybind 异常类型不固定，只在资源回收阶段降级为警告。
                typer.secho(f"警告: SDK 虚拟串口释放失败: {exc}", err=True)
        if relay_started:
            try:
                relay.stop()
                typer.echo("真实串口已释放，原始字节抓包已关闭")
            except Exception as exc:
                # 中继内部含串口、PTY 与文件，继续恢复 stdout 以保留可诊断输出。
                typer.secho(f"警告: 真实串口中继释放失败: {exc}", err=True)
        try:
            stdout_filter.stop()
        except OSError as exc:
            # stdout 恢复失败不应阻止已采集数据落盘。
            typer.secho(f"警告: 终端输出恢复失败: {exc}", err=True)
        try:
            measurements = enrich_protocol_measurements(
                measurements, capture_path, sensor_index, axis_index, compression_sign
            )
        except (OSError, ValueError, IndexError) as exc:
            typer.secho(f"警告: 自研协议回放失败，保留 SDK 结果: {exc}", err=True)
        csv_path = save_measurements(measurements, session_dir)
        if auto_plot and csv_path is not None:
            typer.echo("正在调用离线绘图钩子……")
            run_plot_hook(csv_path, config_path)

    typer.echo(f"测量结束，共记录 {len(measurements)} 个质量点，结果位于 {session_dir}")
    return 0


@app.command()
def measure(
    config_path: Annotated[pathlib.Path, typer.Option("--config", "-c")] = DEFAULT_CONFIG_PATH,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", help="忽略 YAML 质量数组，改为每轮在终端输入质量"),
    ] = False,
) -> None:
    """按 YAML 质量数组记录质量（g）与 sensor frame 法向压力（N）。"""
    try:
        config = load_experiment_config(config_path)
    except OSError as exc:
        typer.secho(f"错误: 无法读取配置 {config_path}: {exc}", err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc

    raise typer.Exit(
        run_accuracy_session(
            config.port,
            config.baud_rate,
            config.rate_hz,
            config.sensor_index,
            config.normal_axis,
            config.compression_sign,
            config.window_sec,
            config.timeout_sec,
            config.std_threshold_n,
            config.drift_threshold_n_per_sec,
            config.output_dir,
            config.auto_plot,
            config_path,
            config.target_masses_g,
            interactive,
        )
    )


if __name__ == "__main__":
    app()
