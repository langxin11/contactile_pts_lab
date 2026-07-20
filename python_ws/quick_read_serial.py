#!/usr/bin/env python3
"""通过纯 Python 串口协议读取 Contactile PTS 全局力。"""

from __future__ import annotations

import os
import sys
from typing import Annotated, Protocol

import typer

from pts_protocol import ParsedPacket, PTSProtocolReader

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_SAMPLES = 100
DEFAULT_SENSOR_INDEX = 0
DEFAULT_TIMEOUT_SEC = 1.0

app = typer.Typer(no_args_is_help=True)


class PacketReader(Protocol):
    """描述读取一个 PTS 协议包所需的最小接口。"""

    def read_packet(self) -> ParsedPacket:
        """读取并解析一个协议包。

        Returns:
            已校验的 PTS 数据包。
        """
        ...


def print_global_forces(reader: PacketReader, samples: int, sensor_index: int) -> None:
    """读取并打印指定传感器的全局三轴力。

    Args:
        reader: PTS 协议包读取器。
        samples: 需要输出的样本数。
        sensor_index: 传感器索引。

    Raises:
        ValueError: 样本数无效，或数据包中不存在指定传感器时抛出。
    """
    if samples <= 0:
        raise ValueError("samples 必须大于 0")
    if sensor_index < 0:
        raise ValueError("sensor 必须大于等于 0")

    typer.echo(f"{'Sample':<8} {'Timestamp (µs)':<18} {'Fx (N)':<12} {'Fy (N)':<12} {'Fz (N)':<12}")
    for sample_index in range(samples):
        packet = reader.read_packet()
        if sensor_index >= len(packet.global_forces):
            raise ValueError(
                f"数据包仅包含 {len(packet.global_forces)} 个传感器，无法读取 SEN{sensor_index}"
            )
        force = packet.global_forces[sensor_index]
        typer.echo(
            f"{sample_index + 1:<8} {packet.timestamp_us:<18} "
            f"{force[0]:<12.4f} {force[1]:<12.4f} {force[2]:<12.4f}"
        )


def run_quick_read_serial(
    port: str,
    baud_rate: int,
    samples: int,
    sensor_index: int,
    timeout_sec: float,
) -> int:
    """打开串口并通过自研协议解析器输出全局力。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        samples: 需要输出的样本数。
        sensor_index: 传感器索引。
        timeout_sec: 单次串口读取超时时间，单位 s。

    Returns:
        进程退出码，0 表示成功。
    """
    if not os.path.exists(port):
        typer.secho(f"错误: 设备 {port} 不存在，请检查连接和权限", err=True)
        return 1
    if timeout_sec <= 0:
        typer.secho("错误: timeout 必须大于 0", err=True)
        return 1

    try:
        import serial

        # with 能覆盖正常退出和异常路径，确保 pyserial 总是释放字符设备。
        with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout_sec) as serial_port:
            typer.echo(f"已连接到 {port}，波特率 {baud_rate}，使用纯 Python 协议解析")
            print_global_forces(PTSProtocolReader(serial_port), samples, sensor_index)
    except PermissionError:
        # 串口权限不足时只能由用户调整 dialout 组，脚本不能自行提权。
        typer.secho(f"错误: 没有权限访问 {port}，请检查 dialout 组权限", err=True)
        return 1
    except (OSError, ValueError, TimeoutError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        return 1
    except KeyboardInterrupt:
        # with 会先关闭串口，再把中断状态返回给调用脚本。
        typer.secho("收到中断信号，已释放串口", err=True)
        return 130

    return 0


@app.command()
def main(
    port: Annotated[str, typer.Option("--port", "-p")] = DEFAULT_PORT,
    baud_rate: Annotated[int, typer.Option("--baud-rate", "-b")] = DEFAULT_BAUD_RATE,
    samples: Annotated[int, typer.Option("--samples", "-n")] = DEFAULT_SAMPLES,
    sensor_index: Annotated[int, typer.Option("--sensor", "-s")] = DEFAULT_SENSOR_INDEX,
    timeout_sec: Annotated[float, typer.Option("--timeout")] = DEFAULT_TIMEOUT_SEC,
) -> None:
    """读取全局三轴力，单位为 N，坐标系为 sensor frame。"""
    raise typer.Exit(run_quick_read_serial(port, baud_rate, samples, sensor_index, timeout_sec))


if __name__ == "__main__":
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
