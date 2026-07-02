#!/usr/bin/env python3
"""Contactile PTS 最简 Python 读取示例.

运行前请确保已激活虚拟环境:
    source python_ws/.venv/bin/activate
    python quick_read.py --help

或直接使用脚本:
    bash scripts/run_python.sh quick_read --help
"""

import os
import sys
import time
from typing import Annotated

import PTSDK_CXX_Pybind
import typer

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_RATE_HZ = 500
DEFAULT_SAMPLES = 100
DEFAULT_SENSOR_INDEX = 0
DEFAULT_SENSOR_COUNT = 2
DEFAULT_REGISTERED_SENSOR_IDS = (0, 1)
DEFAULT_TIMEOUT_SEC = 5.0

# SDK 要求 byteSize 传 char；传整数 8 会导致 pybind 参数不匹配。
BYTE_SIZE_CHAR = "\u0008"
PARITY_NONE = 0
FIRST_SAMPLE_POLL_SEC = 0.01


def sdk_sampling_rate(rate_hz: int) -> int:
    """把用户输入的采样率映射为 SDK 常量。

    Args:
        rate_hz: 控制器采样率，单位 Hz。

    Returns:
        PTSDK 采样率枚举值。

    Raises:
        ValueError: 当采样率不是 SDK 支持值时抛出。
    """
    rate_map = {
        100: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_100,
        250: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_250,
        500: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500,
        1000: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_1000,
    }
    try:
        return rate_map[rate_hz]
    except KeyError as exc:
        raise ValueError("rate 仅支持 100/250/500/1000 Hz") from exc


def wait_for_first_sample(sensor: PTSDK_CXX_Pybind.PTSDKSensor, timeout_sec: float) -> int:
    """等待 SDK 后台线程解析出第一帧数据。

    Args:
        sensor: 传感器数据容器，读取 sensor frame 中的缓存数据。
        timeout_sec: 首帧等待超时时间，单位 s。

    Returns:
        首帧时间戳，单位 µs。

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


def run_quick_read(
    port: str,
    baud_rate: int,
    rate_hz: int,
    samples: int,
    sensor_index: int,
    bias: bool,
    confirm_no_load: bool,
    timeout_sec: float,
) -> int:
    """连接 PTS 控制器并打印全局三轴力。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        rate_hz: 控制器采样率，单位 Hz。
        samples: 读取样本数。
        sensor_index: 传感器索引，范围 0..1。
        bias: 是否发送 bias 零点校准请求。
        confirm_no_load: 是否确认传感器无负载，用于授权 bias。
        timeout_sec: 首帧等待超时时间，单位 s。

    Returns:
        进程退出码，0 表示成功。

    Raises:
        None。
    """
    if bias and not confirm_no_load:
        typer.secho("错误: bias 前必须确认传感器无负载，请添加 --confirm-no-load", err=True)
        return 1
    if not 0 <= sensor_index < DEFAULT_SENSOR_COUNT:
        typer.secho(f"错误: sensor 必须在 0..{DEFAULT_SENSOR_COUNT - 1} 之间", err=True)
        return 1
    if not os.path.exists(port):
        typer.secho(f"错误: 设备 {port} 不存在，请检查连接和权限", err=True)
        return 1

    # Workaround for vendor bug: 当前 hub 默认输出 SEN0/SEN1，两者都注册才能避免 pybind 崩溃。
    sen0 = PTSDK_CXX_Pybind.PTSDKSensor()
    sen1 = PTSDK_CXX_Pybind.PTSDKSensor()
    sensors = (sen0, sen1)
    sensor = sensors[sensor_index]
    listener = PTSDK_CXX_Pybind.PTSDKListener(logFlag=False)
    for registered_sensor_id in DEFAULT_REGISTERED_SENSOR_IDS:
        listener.addSensor(sensors[registered_sensor_id])
    connected = False

    try:
        res = listener.connectAndStartListening(port, baud_rate, PARITY_NONE, BYTE_SIZE_CHAR, True)
        if res != 0:
            typer.secho(f"错误: 无法连接串口，错误码 {res}", err=True)
            return 1
        connected = True
        typer.echo(f"已连接到 {port}，波特率 {baud_rate}")

        if bias:
            if not listener.sendBiasRequest():
                typer.secho("错误: Bias 请求失败", err=True)
                return 1
            typer.echo("Bias 完成")

        listener.setSamplingRate(sdk_sampling_rate(rate_hz))
        timestamp_us = wait_for_first_sample(sensor, timeout_sec)
        typer.echo(f"收到 SEN{sensor_index} 首帧: timestamp={timestamp_us} µs")

        sleep_sec = max(0.0002, 0.5 / rate_hz)
        typer.echo(f"{'Sample':<8} {'Fx (N)':<12} {'Fy (N)':<12} {'Fz (N)':<12}")
        for i in range(samples):
            time.sleep(sleep_sec)
            force = sensor.getGlobalForce()  # shape=(3,)
            typer.echo(f"{i + 1:<8} {force[0]:<12.4f} {force[1]:<12.4f} {force[2]:<12.4f}")
    except PermissionError:
        # 串口权限不足时通常需要加入 dialout 组，不能在脚本内自动提权。
        typer.secho(f"错误: 没有权限访问 {port}，请检查 dialout 组权限", err=True)
        return 1
    except ValueError as exc:
        typer.secho(f"错误: {exc}", err=True)
        return 1
    except TimeoutError as exc:
        typer.secho(f"错误: {exc}", err=True)
        typer.secho("建议: 先尝试 --baud-rate 9600，再确认串口路径和控制器供电/接线", err=True)
        return 1
    except KeyboardInterrupt:
        # 用户中断时返回非零码，让外层脚本知道采集未完整结束。
        typer.echo("\n收到中断信号")
        return 130
    finally:
        # 异常退出时必须释放串口，否则 /dev/ttyACM0 可能保持占用。
        if connected:
            listener.stopListeningAndDisconnect()
            typer.echo("已断开连接")

    return 0


def main(
    port: Annotated[str, typer.Option("--port", "-p")] = DEFAULT_PORT,
    baud_rate: Annotated[int, typer.Option("--baud-rate", "-b")] = DEFAULT_BAUD_RATE,
    rate_hz: Annotated[int, typer.Option("--rate", "-r")] = DEFAULT_RATE_HZ,
    samples: Annotated[int, typer.Option("--samples", "-n")] = DEFAULT_SAMPLES,
    sensor_index: Annotated[int, typer.Option("--sensor", "-s")] = DEFAULT_SENSOR_INDEX,
    bias: Annotated[bool, typer.Option("--bias")] = False,
    confirm_no_load: Annotated[bool, typer.Option("--confirm-no-load")] = False,
    timeout_sec: Annotated[float, typer.Option("--timeout")] = DEFAULT_TIMEOUT_SEC,
) -> None:
    """读取传感器全局三轴力，物理量单位为 N，坐标系为 sensor frame。"""
    raise typer.Exit(
        run_quick_read(
            port,
            baud_rate,
            rate_hz,
            samples,
            sensor_index,
            bias,
            confirm_no_load,
            timeout_sec,
        )
    )


if __name__ == "__main__":
    try:
        typer.run(main)
    except SystemExit as exc:
        sys.exit(exc.code)
