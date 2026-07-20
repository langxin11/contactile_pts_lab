#!/usr/bin/env python3
"""Contactile PTS (PapillArray v2.0) 触觉传感器驱动 (纯 Python)。

PTS 为 9 个 pillar 排成 3x3，每 pillar 输出 3D 力/位移，另有全局力/力矩。

实现说明: 此驱动**不使用 SDK**，改用 pyserial 直接读串口、按官方协议
(ftg.sensors.pts_protocol) 解析二进制数据包。这样不受原厂 cp310 wheel 约束，也便于
用 CSV 和官方 SDK 做字段级对比。若改回官方 SDK，需要注意 hub 输出 SEN0/SEN1 两路时
必须注册两个 PTSDKSensor；只注册一路会触发 native parser 崩溃。
控制器命令为 ASCII: ``z\\n`` bias、``f500\\n`` 设采样率。

控制器可接 1~2 个 sensor; 本类默认暴露索引 ``sensor_index`` 指定的那个 (默认 0)。
"""

from __future__ import annotations

import os
import threading
import time

import numpy as np
from ftg.sensors.base import BaseTactileSensor
from ftg.sensors.pts_protocol import PTSProtocolReader, parse_packet, verify_checksum
from ftg.types import TactileFrame

_DEFAULT_BAUD = 115200  # USB CDC 虚拟波特率，取值不敏感
_BIAS_DURATION_S = 2.0  # bias 最长耗时，期间须保持无负载
_SUPPORTED_RATES_HZ = {100, 250, 500, 1000}


def _import_pyserial():
    """导入 pyserial，并把同名错误包场景转成可读错误。"""
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


class ContactilePTS(BaseTactileSensor):
    """Contactile PTS 触觉传感器 (纯 Python 串口驱动)。

    Args:
        port: 串口设备路径。
        baud_rate: 波特率 (USB CDC 下不敏感，默认 115200)。
        sampling_rate_hz: 采样率，支持 100/250/500/1000。
        bias_on_startup: connect() 后是否自动 bias (要求无负载)。
        sensor_index: 控制器接多个 sensor 时，本类对外暴露的 sensor 序号。
    """

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baud_rate: int = _DEFAULT_BAUD,
        sampling_rate_hz: int = 500,
        bias_on_startup: bool = True,
        sensor_index: int = 0,
    ) -> None:
        self._port = port
        self._baud = baud_rate
        self._rate_hz = sampling_rate_hz
        self._bias_on_startup = bias_on_startup
        self._sensor_index = sensor_index
        self._ser = None
        self._reader = None
        # 读串口与 bias 复用同一把锁: 避免 bias 的 reset_input_buffer 与并发读冲突
        self._serial_lock = threading.Lock()

    def connect(self) -> None:
        serial = _import_pyserial()

        # 预检查设备，给出比 pyserial 更友好的提示
        if not os.path.exists(self._port):
            raise ConnectionError(f"设备 {self._port} 不存在，请检查连接和 dialout 权限")
        try:
            self._ser = serial.Serial(self._port, self._baud, timeout=1)
        except serial.SerialException as exc:
            raise ConnectionError(f"无法打开 {self._port}: {exc}") from exc
        self._reader = PTSProtocolReader(self._ser)

        self._set_sampling_rate(self._rate_hz)
        if self._bias_on_startup:
            self.bias()

    def disconnect(self) -> None:
        # 异常退出也必须释放串口，否则设备占用 (见 AGENTS.md 硬件安全)
        if self._ser is not None:
            with self._serial_lock:
                self._ser.close()
            self._ser = None
            self._reader = None

    def _set_sampling_rate(self, hz: int) -> None:
        if hz not in _SUPPORTED_RATES_HZ:
            supported = ", ".join(str(v) for v in sorted(_SUPPORTED_RATES_HZ))
            raise ValueError(f"PTS 采样率仅支持 {supported} Hz，当前为 {hz}")
        # ASCII 命令 fXXX\n，控制器据此切换采样率
        self._ser.write(f"f{hz}\n".encode("ascii"))
        self._ser.flush()

    def bias(self) -> None:
        if self._ser is None:
            raise RuntimeError("传感器未连接，请先 connect()")
        # ASCII 命令 z\n: 零点校准，最长 2s，期间必须无负载
        with self._serial_lock:
            self._ser.reset_input_buffer()
            if self._reader is not None:
                self._reader.reset_buffer()
            self._ser.write(b"z\n")
            self._ser.flush()
            time.sleep(_BIAS_DURATION_S)
            self._ser.reset_input_buffer()  # 丢弃 bias 期间的过渡帧
            if self._reader is not None:
                self._reader.reset_buffer()

    def read(self) -> TactileFrame:
        frames = self.read_all()
        i = self._sensor_index
        if i >= len(frames):
            raise IndexError(f"请求 sensor {i}，但仅检测到 {len(frames)} 个")
        return frames[i]

    def read_all(self) -> list[TactileFrame]:
        if self._reader is None:
            raise RuntimeError("传感器未连接，请先 connect()")
        with self._serial_lock:
            pkt = self._reader.read_packet()
        return self._packet_to_frames(pkt)

    def _packet_to_frames(self, pkt) -> list[TactileFrame]:
        return [
            TactileFrame(
                timestamp_us=pkt.timestamp_us,
                pillar_forces=pkt.pillar_forces[i],
                pillar_displacements=pkt.pillar_displacements[i],
                global_force=pkt.global_forces[i],
                global_torque=pkt.global_torques[i],
            )
            for i in range(pkt.n_sensors)
        ]


class MockContactilePTS(BaseTactileSensor):
    """无硬件 mock 传感器: 返回带噪声的零负载读数，供离线开发/测试。"""

    _N_PILLARS = 9

    def __init__(self, sensor_count: int = 1, sensor_index: int = 0, **_kwargs) -> None:
        if sensor_count < 1:
            raise ValueError("mock PTS sensor_count 必须 >= 1")
        self._sensor_count = sensor_count
        self._sensor_index = sensor_index
        self._t = 0

    def connect(self) -> None:
        self._t = 0

    def disconnect(self) -> None:
        pass

    def bias(self) -> None:
        pass

    def read(self) -> TactileFrame:
        frames = self.read_all()
        if self._sensor_index >= len(frames):
            raise IndexError(f"请求 sensor {self._sensor_index}，但仅检测到 {len(frames)} 个")
        return frames[self._sensor_index]

    def read_all(self) -> list[TactileFrame]:
        self._t += 2000  # 模拟 500Hz 步进，单位 us
        frames = []
        for i in range(self._sensor_count):
            rng = np.random.default_rng(self._t + i)  # 由时间戳派生，避免依赖全局随机源
            noise = rng.normal(0, 0.01, size=(self._N_PILLARS, 3))
            frames.append(
                TactileFrame(
                    timestamp_us=self._t,
                    pillar_forces=noise,
                    pillar_displacements=noise * 0.1,
                    global_force=noise.sum(axis=0),
                    global_torque=np.zeros(3),
                )
            )
        return frames


__all__ = ["ContactilePTS", "MockContactilePTS", "parse_packet", "verify_checksum"]
