#!/usr/bin/env python3
"""用真实串口抓包对照官方 SDK 与纯 Python 协议解析结果。

为什么要走 PTY 中继: 同一个串口设备不能同时被 SDK 和 pyserial 直接独占读取。这里先把
真实串口接到一个伪终端，SDK 读伪终端得到的数据与落盘的原始字节完全一致；随后再离线解析
这份抓包，才能把“协议实现是否正确”与“硬件当时是否稳定”分开看清楚。
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import pty
import select
import shutil
import sys
import threading
import time
import tty
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - 仅用于离线导入辅助函数
    typer = None

from pts_protocol import ParsedPacket, PTSProtocolReader

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_RATE_HZ = 500
DEFAULT_DURATION_SEC = 3.0
DEFAULT_SENSOR_COUNT = 2
DEFAULT_REGISTERED_SENSOR_IDS = (0, 1)
DEFAULT_TIMEOUT_SEC = 5.0
DEFAULT_ABS_TOL = 1e-5
DEFAULT_OUTPUT_ROOT = pathlib.Path(__file__).resolve().parents[1] / "data" / "protocol_compare"
DEFAULT_LOG_DIR = pathlib.Path(__file__).resolve().parent / "Logs"
DEFAULT_CHUNK_SIZE = 4096
DEFAULT_SERIAL_TIMEOUT_SEC = 0.2
DEFAULT_RELAY_POLL_SEC = 0.05
BYTE_SIZE_CHAR = "\u0008"
PARITY_NONE = 0
FIRST_SAMPLE_POLL_SEC = 0.01
SDK_LOG_PATTERN = "LOG_*.csv"

if typer is not None:
    app = typer.Typer(no_args_is_help=True)
    _PORT_OPTION = typer.Option("--port", "-p", help="串口设备路径")
    _BAUD_OPTION = typer.Option("--baud-rate", "-b", help="串口波特率")
    _RATE_OPTION = typer.Option("--rate", "-r", help="控制器采样率 Hz")
    _DURATION_OPTION = typer.Option("--duration", "-d", help="抓包持续时间 s")
    _SENSOR_COUNT_OPTION = typer.Option("--sensor-count", help="默认注册的传感器数")
    _BIAS_OPTION = typer.Option("--bias", help="抓包前执行 bias，须确保传感器无负载")
    _TIMEOUT_OPTION = typer.Option("--timeout", help="等待首帧超时时间 s")
    _ABS_TOL_OPTION = typer.Option("--abs-tol", help="协议值与 SDK CSV 的绝对误差容忍")
    _OUTPUT_ROOT_OPTION = typer.Option("--output-root", help="对照产物输出根目录")
    _LOG_DIR_OPTION = typer.Option("--log-dir", help="SDK Logs 目录")
else:  # pragma: no cover - 仅用于离线导入辅助函数
    app = None
    _PORT_OPTION = None
    _BAUD_OPTION = None
    _RATE_OPTION = None
    _DURATION_OPTION = None
    _SENSOR_COUNT_OPTION = None
    _BIAS_OPTION = None
    _TIMEOUT_OPTION = None
    _ABS_TOL_OPTION = None
    _OUTPUT_ROOT_OPTION = None
    _LOG_DIR_OPTION = None


def import_pyserial():
    """导入 pyserial，并把常见的同名错误包场景转成可读错误。

    Returns:
        pyserial 的 serial 模块。

    Raises:
        RuntimeError: 当前环境缺少 pyserial，或被无关的 serial 包覆盖时抛出。
    """
    try:
        import serial
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 pyserial，请在 python_ws 环境中安装 pyserial>=3.5") from exc

    if not hasattr(serial, "Serial"):
        module_path = getattr(serial, "__file__", "<unknown>")
        raise RuntimeError(
            "当前导入的不是 pyserial，而是其他同名 serial 包: "
            f"{module_path}。请卸载 serial 并安装 pyserial>=3.5"
        )
    return serial


@dataclass(frozen=True)
class ComparisonArtifacts:
    """一次真实抓包对照流程产出的文件集合。"""

    output_dir: pathlib.Path
    raw_capture_path: pathlib.Path
    protocol_csv_path: pathlib.Path
    sdk_csv_path: pathlib.Path
    summary_json_path: pathlib.Path
    mismatches_csv_path: pathlib.Path


class _BufferedBytesSerial:
    """把离线抓包伪装成只读串口，复用协议层现有的分帧逻辑。"""

    def __init__(self, payload: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        self._payload = payload
        self._pos = 0
        self._chunk_size = chunk_size

    def read(self, size: int) -> bytes:
        request_size = min(size, self._chunk_size)
        if self._pos >= len(self._payload):
            return b""
        end = min(self._pos + request_size, len(self._payload))
        chunk = self._payload[self._pos : end]
        self._pos = end
        return chunk


class SerialTeeRelay:
    """把真实串口双向转发到 PTY，并保存控制器发出的原始字节。"""

    def __init__(self, port: str, baud_rate: int, capture_path: pathlib.Path) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._capture_path = capture_path
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._serial = None
        self._master_fd: int | None = None
        self._slave_fd: int | None = None
        self._capture_file = None
        self.virtual_port: str | None = None

    def start(self) -> None:
        """启动真实串口与 PTY 的双向中继。"""
        serial = import_pyserial()

        self._capture_path.parent.mkdir(parents=True, exist_ok=True)
        self._capture_file = self._capture_path.open("wb")
        self._serial = serial.Serial(
            self._port,
            self._baud_rate,
            timeout=DEFAULT_SERIAL_TIMEOUT_SEC,
            write_timeout=DEFAULT_SERIAL_TIMEOUT_SEC,
        )
        self._master_fd, self._slave_fd = pty.openpty()
        tty.setraw(self._master_fd)
        tty.setraw(self._slave_fd)
        self.virtual_port = os.ttyname(self._slave_fd)

        self._threads = [
            threading.Thread(target=self._device_to_sdk_loop, daemon=True),
            threading.Thread(target=self._sdk_to_device_loop, daemon=True),
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        """停止中继并释放真实串口与 PTY。"""
        self._stop_event.set()
        if self._serial is not None:
            try:
                self._serial.cancel_read()
            except AttributeError:
                pass
            except Exception:
                pass
        for thread in self._threads:
            thread.join(timeout=1.0)
        if self._capture_file is not None and not self._capture_file.closed:
            self._capture_file.flush()
            self._capture_file.close()
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
        if self._slave_fd is not None:
            try:
                os.close(self._slave_fd)
            except OSError:
                pass
            self._slave_fd = None

    def _device_to_sdk_loop(self) -> None:
        """从真实串口读控制器字节，既转发给 SDK，也原样写入抓包文件。"""
        assert self._serial is not None
        assert self._master_fd is not None
        assert self._capture_file is not None
        while not self._stop_event.is_set():
            try:
                chunk = self._serial.read(DEFAULT_CHUNK_SIZE)
            except Exception:
                break
            if not chunk:
                continue
            try:
                os.write(self._master_fd, chunk)
                self._capture_file.write(chunk)
                self._capture_file.flush()
            except OSError:
                break

    def _sdk_to_device_loop(self) -> None:
        """转发 SDK 发出的 ASCII 控制命令，保证采样率和 bias 真正到达控制器。"""
        assert self._serial is not None
        assert self._master_fd is not None
        while not self._stop_event.is_set():
            try:
                readable, _, _ = select.select([self._master_fd], [], [], DEFAULT_RELAY_POLL_SEC)
            except (OSError, ValueError):
                break
            if not readable:
                continue
            try:
                chunk = os.read(self._master_fd, DEFAULT_CHUNK_SIZE)
            except OSError:
                break
            if not chunk:
                continue
            try:
                self._serial.write(chunk)
                self._serial.flush()
            except Exception:
                break


def wait_for_first_sample(sensor: Any, timeout_sec: float) -> int:
    """等待 SDK 后台线程解析出第一帧有效时间戳。

    Args:
        sensor: 官方 SDK 的 PTSDKSensor 对象。
        timeout_sec: 首帧等待超时时间，单位 s。

    Returns:
        第一帧时间戳，单位 us。

    Raises:
        TimeoutError: 超时仍未收到有效时间戳时抛出。
    """
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        timestamp_us = int(sensor.getTimestamp_us())
        if timestamp_us > 0:
            return timestamp_us
        time.sleep(FIRST_SAMPLE_POLL_SEC)
    raise TimeoutError(f"{timeout_sec:.1f} s 内未收到第一帧有效数据")


def parse_capture_packets(raw_capture: bytes) -> list[ParsedPacket]:
    """把抓包原始字节流按协议切帧，并解析成数据包列表。

    Args:
        raw_capture: 控制器到主机方向的完整原始字节流。

    Returns:
        解析成功的数据包列表。
    """
    reader = PTSProtocolReader(_BufferedBytesSerial(raw_capture))
    packets: list[ParsedPacket] = []
    while True:
        try:
            packets.append(reader.read_packet())
        except TimeoutError:
            return packets


def flatten_packet(packet: ParsedPacket) -> dict[str, float | int]:
    """把协议包展平成接近 SDK CSV 的列名，便于逐字段对照。"""
    row: dict[str, float | int] = {"T_us": packet.timestamp_us}
    for sensor_index in range(packet.n_sensors):
        pillar_forces = packet.pillar_forces[sensor_index]
        pillar_displacements = packet.pillar_displacements[sensor_index]
        for pillar_index in range(pillar_forces.shape[0]):
            disp = pillar_displacements[pillar_index]
            force = pillar_forces[pillar_index]
            row[f"S{sensor_index}_P{pillar_index}_DX"] = float(disp[0])
            row[f"S{sensor_index}_P{pillar_index}_DY"] = float(disp[1])
            row[f"S{sensor_index}_P{pillar_index}_DZ"] = float(disp[2])
            row[f"S{sensor_index}_P{pillar_index}_FX"] = float(force[0])
            row[f"S{sensor_index}_P{pillar_index}_FY"] = float(force[1])
            row[f"S{sensor_index}_P{pillar_index}_FZ"] = float(force[2])
        global_force = packet.global_forces[sensor_index]
        global_torque = packet.global_torques[sensor_index]
        row[f"S{sensor_index}_G_FX"] = float(global_force[0])
        row[f"S{sensor_index}_G_FY"] = float(global_force[1])
        row[f"S{sensor_index}_G_FZ"] = float(global_force[2])
        row[f"S{sensor_index}_G_TX"] = float(global_torque[0])
        row[f"S{sensor_index}_G_TY"] = float(global_torque[1])
        row[f"S{sensor_index}_G_TZ"] = float(global_torque[2])
    return row


def write_protocol_csv(rows: list[dict[str, float | int]], output_path: pathlib.Path) -> None:
    """把纯协议解析结果写成 CSV，便于直接和 SDK 日志并排看。"""
    if not rows:
        raise ValueError("协议抓包未解析出任何数据包")
    fieldnames = sorted(rows[0].keys(), key=lambda name: (name != "T_us", name))
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_sdk_rows(csv_path: pathlib.Path) -> list[dict[str, str]]:
    """读取 SDK CSV，并保留字符串形式以避免未比较字段被意外转换。"""
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def compare_rows(
    protocol_rows: list[dict[str, float | int]],
    sdk_rows: list[dict[str, str]],
    abs_tol: float,
) -> tuple[dict[str, Any], list[dict[str, float | int | str]]]:
    """按时间戳对齐协议解析结果与 SDK CSV，输出摘要和超差明细。"""
    if not protocol_rows:
        raise ValueError("协议解析结果为空，无法对照")
    if not sdk_rows:
        raise ValueError("SDK CSV 为空，无法对照")

    protocol_by_ts = {int(row["T_us"]): row for row in protocol_rows}
    sdk_by_ts = {int(row["T_us"]): row for row in sdk_rows if row.get("T_us")}
    common_timestamps = sorted(protocol_by_ts.keys() & sdk_by_ts.keys())

    mismatches: list[dict[str, float | int | str]] = []
    max_abs_diff = 0.0
    max_abs_diff_field = ""

    comparable_fields = sorted(
        field
        for field in protocol_rows[0]
        if field != "T_us" and field in sdk_rows[0]
    )
    for timestamp_us in common_timestamps:
        protocol_row = protocol_by_ts[timestamp_us]
        sdk_row = sdk_by_ts[timestamp_us]
        for field in comparable_fields:
            protocol_value = float(protocol_row[field])
            sdk_value = float(sdk_row[field])
            abs_diff = abs(protocol_value - sdk_value)
            if abs_diff > max_abs_diff:
                max_abs_diff = abs_diff
                max_abs_diff_field = field
            if abs_diff > abs_tol:
                mismatches.append(
                    {
                        "T_us": timestamp_us,
                        "field": field,
                        "protocol_value": protocol_value,
                        "sdk_value": sdk_value,
                        "abs_diff": abs_diff,
                    }
                )

    summary = {
        "protocol_packet_count": len(protocol_rows),
        "sdk_row_count": len(sdk_rows),
        "matched_timestamp_count": len(common_timestamps),
        "protocol_only_timestamps": sorted(protocol_by_ts.keys() - sdk_by_ts.keys())[:20],
        "sdk_only_timestamps": sorted(sdk_by_ts.keys() - protocol_by_ts.keys())[:20],
        "compared_field_count": len(comparable_fields),
        "abs_tolerance": abs_tol,
        "mismatch_count": len(mismatches),
        "max_abs_diff": max_abs_diff,
        "max_abs_diff_field": max_abs_diff_field,
    }
    return summary, mismatches


def pick_newest_sdk_log(log_dir: pathlib.Path, before_files: set[pathlib.Path]) -> pathlib.Path:
    """定位本次运行新生成的 SDK CSV 日志。"""
    after_files = set(log_dir.glob(SDK_LOG_PATTERN))
    new_files = sorted(after_files - before_files, key=lambda path: path.stat().st_mtime)
    if new_files:
        return new_files[-1]
    existing_files = sorted(after_files, key=lambda path: path.stat().st_mtime)
    if not existing_files:
        raise FileNotFoundError(f"{log_dir} 下未找到 SDK 日志 {SDK_LOG_PATTERN}")
    return existing_files[-1]


def ensure_typer_available() -> None:
    """在 CLI 入口统一检查 Typer 依赖，避免离线导入辅助函数时报错。"""
    if typer is None:
        raise RuntimeError("当前环境缺少 typer，请在 python_ws 虚拟环境中运行本脚本")


def build_output_dir(output_root: pathlib.Path) -> pathlib.Path:
    """生成一次采集的独立输出目录，避免覆盖旧对照结果。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def run_protocol_compare(
    port: str,
    baud_rate: int,
    rate_hz: int,
    duration_sec: float,
    sensor_count: int,
    bias: bool,
    timeout_sec: float,
    abs_tol: float,
    output_root: pathlib.Path,
    log_dir: pathlib.Path,
) -> ComparisonArtifacts:
    """执行一次真实抓包对照，并产出原始字节、协议 CSV、SDK CSV 与摘要。"""
    if sensor_count != DEFAULT_SENSOR_COUNT:
        raise ValueError(
            f"当前 hub 默认输出 SEN0/SEN1，对照脚本暂只支持 sensor_count={DEFAULT_SENSOR_COUNT}"
        )
    if duration_sec <= 0:
        raise ValueError("duration 必须 > 0")
    if abs_tol < 0:
        raise ValueError("abs_tol 必须 >= 0")
    if not os.path.exists(port):
        raise FileNotFoundError(f"设备 {port} 不存在，请检查连接和权限")

    import PTSDK_CXX_Pybind

    output_dir = build_output_dir(output_root)
    raw_capture_path = output_dir / "capture_raw.bin"
    protocol_csv_path = output_dir / "protocol.csv"
    sdk_csv_path = output_dir / "sdk.csv"
    summary_json_path = output_dir / "compare_summary.json"
    mismatches_csv_path = output_dir / "mismatches.csv"

    log_dir.mkdir(parents=True, exist_ok=True)
    logs_before = set(log_dir.glob(SDK_LOG_PATTERN))

    relay = SerialTeeRelay(port=port, baud_rate=baud_rate, capture_path=raw_capture_path)
    listener = None
    connected = False
    try:
        relay.start()
        assert relay.virtual_port is not None

        # Workaround for vendor bug: 当前 hub 默认输出 SEN0/SEN1，两者都注册才能避免 SDK 解析异常。
        sen0 = PTSDK_CXX_Pybind.PTSDKSensor()
        sen1 = PTSDK_CXX_Pybind.PTSDKSensor()
        sensors = (sen0, sen1)
        listener = PTSDK_CXX_Pybind.PTSDKListener(logFlag=True)
        for registered_sensor_id in DEFAULT_REGISTERED_SENSOR_IDS:
            listener.addSensor(sensors[registered_sensor_id])

        res = listener.connectAndStartListening(
            relay.virtual_port,
            baud_rate,
            PARITY_NONE,
            BYTE_SIZE_CHAR,
            True,
        )
        if res != 0:
            raise RuntimeError(f"SDK 无法连接中继串口 {relay.virtual_port}，错误码 {res}")
        connected = True

        if bias:
            if not listener.sendBiasRequest():
                raise RuntimeError("SDK Bias 请求失败")

        rate_map = {
            100: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_100,
            250: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_250,
            500: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500,
            1000: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_1000,
        }
        try:
            listener.setSamplingRate(rate_map[rate_hz])
        except KeyError as exc:
            raise ValueError("rate 仅支持 100/250/500/1000 Hz") from exc

        wait_for_first_sample(sensors[0], timeout_sec)
        time.sleep(duration_sec)
    finally:
        # 异常退出也要先让 SDK 释放监听线程，再关闭真实串口，避免控制器设备被占用。
        if connected and listener is not None:
            listener.stopListeningAndDisconnect()
        relay.stop()

    sdk_log_path = pick_newest_sdk_log(log_dir, logs_before)
    shutil.copy2(sdk_log_path, sdk_csv_path)

    raw_capture = raw_capture_path.read_bytes()
    packets = parse_capture_packets(raw_capture)
    protocol_rows = [flatten_packet(packet) for packet in packets]
    write_protocol_csv(protocol_rows, protocol_csv_path)
    sdk_rows = load_sdk_rows(sdk_csv_path)
    summary, mismatches = compare_rows(protocol_rows, sdk_rows, abs_tol)

    with mismatches_csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["T_us", "field", "protocol_value", "sdk_value", "abs_diff"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mismatches)

    summary.update(
        {
            "raw_capture_bytes": len(raw_capture),
            "raw_capture_path": str(raw_capture_path),
            "protocol_csv_path": str(protocol_csv_path),
            "sdk_csv_path": str(sdk_csv_path),
            "mismatches_csv_path": str(mismatches_csv_path),
        }
    )
    summary_json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    return ComparisonArtifacts(
        output_dir=output_dir,
        raw_capture_path=raw_capture_path,
        protocol_csv_path=protocol_csv_path,
        sdk_csv_path=sdk_csv_path,
        summary_json_path=summary_json_path,
        mismatches_csv_path=mismatches_csv_path,
    )


@app.command() if app is not None else (lambda func: func)
def compare(
    port: Annotated[str, _PORT_OPTION] = DEFAULT_PORT,
    baud_rate: Annotated[int, _BAUD_OPTION] = DEFAULT_BAUD_RATE,
    rate: Annotated[int, _RATE_OPTION] = DEFAULT_RATE_HZ,
    duration: Annotated[float, _DURATION_OPTION] = DEFAULT_DURATION_SEC,
    sensor_count: Annotated[int, _SENSOR_COUNT_OPTION] = DEFAULT_SENSOR_COUNT,
    bias: Annotated[bool, _BIAS_OPTION] = False,
    timeout: Annotated[float, _TIMEOUT_OPTION] = DEFAULT_TIMEOUT_SEC,
    abs_tol: Annotated[float, _ABS_TOL_OPTION] = DEFAULT_ABS_TOL,
    output_root: Annotated[pathlib.Path, _OUTPUT_ROOT_OPTION] = DEFAULT_OUTPUT_ROOT,
    log_dir: Annotated[pathlib.Path, _LOG_DIR_OPTION] = DEFAULT_LOG_DIR,
) -> None:
    """采集同一批真实串口字节，并完成 SDK CSV 对照。"""
    ensure_typer_available()
    try:
        artifacts = run_protocol_compare(
            port=port,
            baud_rate=baud_rate,
            rate_hz=rate,
            duration_sec=duration,
            sensor_count=sensor_count,
            bias=bias,
            timeout_sec=timeout,
            abs_tol=abs_tol,
            output_root=output_root,
            log_dir=log_dir,
        )
    except FileNotFoundError as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    except PermissionError:
        typer.secho(f"错误: 没有权限访问 {port}，请检查 dialout 组权限", err=True)
        raise typer.Exit(1)
    except TimeoutError as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    except RuntimeError as exc:
        typer.secho(f"错误: {exc}", err=True)
        raise typer.Exit(1) from exc
    except KeyboardInterrupt:
        typer.secho("收到中断信号，已停止抓包并尝试释放串口", err=True)
        raise typer.Exit(130)

    typer.echo(f"对照完成，输出目录: {artifacts.output_dir}")
    typer.echo(f"原始抓包: {artifacts.raw_capture_path}")
    typer.echo(f"协议解析 CSV: {artifacts.protocol_csv_path}")
    typer.echo(f"SDK CSV: {artifacts.sdk_csv_path}")
    typer.echo(f"摘要: {artifacts.summary_json_path}")
    typer.echo(f"超差明细: {artifacts.mismatches_csv_path}")


if __name__ == "__main__":
    if typer is None:
        sys.stderr.write("错误: 当前环境缺少 typer，请在 python_ws 虚拟环境中运行本脚本\n")
        raise SystemExit(1)
    app()
