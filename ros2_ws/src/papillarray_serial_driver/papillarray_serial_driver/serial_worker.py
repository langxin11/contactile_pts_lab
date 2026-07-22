"""串口读取、控制命令和自动重连。"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import serial

from .protocol import PTSProtocolReader, ParsedPacket

BIAS_COMMAND = b"z\n"
START_SLIP_COMMAND = b"S\n"
STOP_SLIP_COMMAND = b"s\n"
SUPPORTED_SAMPLING_RATES = frozenset({100, 250, 500, 1000})


class SerialPort(Protocol):
    """描述驱动使用的最小串口接口。"""

    def read(self, size: int) -> bytes:
        """读取串口字节。"""
        ...

    def write(self, data: bytes) -> int:
        """写入串口字节。"""
        ...

    def flush(self) -> None:
        """等待已写数据发送完毕。"""
        ...

    def close(self) -> None:
        """关闭串口。"""
        ...


@dataclass(frozen=True)
class SerialWorkerConfig:
    """串口工作线程配置。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        sampling_rate: 控制器采样频率，单位 Hz。
        timeout_sec: 单次串口读取超时，单位 s。
        max_packet_bytes: 单个协议帧允许的最大字节数。
        reconnect_initial_delay_sec: 首次重连等待时间，单位 s。
        reconnect_max_delay_sec: 最大重连等待时间，单位 s。
    """

    port: str
    baud_rate: int
    sampling_rate: int
    timeout_sec: float = 1.0
    max_packet_bytes: int = 8192
    reconnect_initial_delay_sec: float = 1.0
    reconnect_max_delay_sec: float = 10.0

    def validate(self) -> None:
        """校验配置。

        Raises:
            ValueError: 配置值不满足串口驱动约束。
        """
        if not self.port:
            raise ValueError("com_port 不能为空")
        if self.baud_rate <= 0:
            raise ValueError("baud_rate 必须大于 0")
        if self.sampling_rate not in SUPPORTED_SAMPLING_RATES:
            rates = ", ".join(str(rate) for rate in sorted(SUPPORTED_SAMPLING_RATES))
            raise ValueError(f"sampling_rate 必须是 {rates} Hz 之一")
        if self.timeout_sec <= 0:
            raise ValueError("serial_timeout_sec 必须大于 0")
        if self.max_packet_bytes <= 0:
            raise ValueError("max_packet_bytes 必须大于 0")
        if self.reconnect_initial_delay_sec <= 0:
            raise ValueError("reconnect_initial_delay_sec 必须大于 0")
        if self.reconnect_max_delay_sec < self.reconnect_initial_delay_sec:
            raise ValueError("reconnect_max_delay_sec 不能小于初始重连间隔")


@dataclass
class _PendingCommand:
    payload: bytes
    completed: threading.Event
    succeeded: bool = False
    started: bool = False
    cancelled: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


def _default_serial_factory(**kwargs: Any) -> SerialPort:
    """打开 pyserial 串口。

    Args:
        **kwargs: 传递给 ``serial.Serial`` 的参数。

    Returns:
        已打开的串口对象。
    """
    return serial.Serial(**kwargs)


class SerialWorker:
    """在独立线程中读取 PTS 帧并管理控制命令。

    Args:
        config: 串口和重连配置。
        on_packet: 收到有效协议包时的回调。
        serial_factory: 串口工厂，测试时可替换为 fake serial。
        on_info: 普通状态日志回调。
        on_warning: 警告日志回调。
        on_error: 错误日志回调。
    """

    def __init__(
        self,
        config: SerialWorkerConfig,
        on_packet: Callable[[ParsedPacket], None],
        serial_factory: Callable[..., SerialPort] = _default_serial_factory,
        on_info: Callable[[str], None] | None = None,
        on_warning: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        config.validate()
        self._config = config
        self._on_packet = on_packet
        self._serial_factory = serial_factory
        self._on_info = on_info or (lambda _message: None)
        self._on_warning = on_warning or (lambda _message: None)
        self._on_error = on_error or (lambda _message: None)
        self._commands: queue.Queue[_PendingCommand] = queue.Queue()
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_connected(self) -> bool:
        """返回串口当前是否已连接。"""
        return self._connected_event.is_set()

    def start(self) -> None:
        """启动串口工作线程。

        Raises:
            RuntimeError: 工作线程已启动。
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("串口工作线程已经启动")
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="papillarray-serial-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, join_timeout_sec: float | None = None) -> None:
        """停止线程并等待串口关闭。

        Args:
            join_timeout_sec: 等待线程退出的最长时间，单位 s；默认依据串口超时计算。
        """
        self._stop_event.set()
        self._fail_pending_commands()
        if self._thread is not None:
            timeout = join_timeout_sec or self._config.timeout_sec + 1.0
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                self._on_error("串口工作线程未在预期时间内退出")
        self._thread = None

    def send_command(self, payload: bytes, timeout_sec: float | None = None) -> bool:
        """请求 I/O 线程发送命令。

        Args:
            payload: 完整 ASCII 控制命令字节。
            timeout_sec: 等待命令写入的最长时间，单位 s。

        Returns:
            命令是否已完整写入并 flush。断线时立即返回 ``False``。
        """
        if not self.is_connected or self._stop_event.is_set():
            return False
        command = _PendingCommand(payload=payload, completed=threading.Event())
        self._commands.put(command)
        wait_timeout = timeout_sec or self._config.timeout_sec + 0.5
        if not command.completed.wait(wait_timeout):
            with command.lock:
                if not command.started:
                    command.cancelled = True
            return False
        return command.succeeded

    def _run(self) -> None:
        reconnect_delay = self._config.reconnect_initial_delay_sec
        while not self._stop_event.is_set():
            serial_port: SerialPort | None = None
            try:
                serial_port = self._serial_factory(
                    port=self._config.port,
                    baudrate=self._config.baud_rate,
                    timeout=self._config.timeout_sec,
                )
                self._connected_event.set()
                self._on_info(
                    f"已连接 {self._config.port}，波特率 {self._config.baud_rate} baud"
                )
                self._write_payload(
                    serial_port,
                    f"f{self._config.sampling_rate}\n".encode("ascii"),
                )
                reader = PTSProtocolReader(serial_port, self._config.max_packet_bytes)
                received_valid_packet = False

                while not self._stop_event.is_set():
                    self._drain_commands(serial_port)
                    try:
                        packet = reader.read_packet()
                    except ValueError as exc:
                        # 单帧结构异常不代表串口失效，继续同步后续帧可避免无谓重连。
                        self._on_warning(f"已丢弃无法解析的数据包: {exc}")
                        continue
                    try:
                        self._on_packet(packet)
                    except Exception as exc:  # noqa: BLE001
                        # ROS 发布回调异常不应终止串口线程，否则设备仍连接却永久停止采集。
                        self._on_error(f"数据包消费回调失败: {exc}")
                    if not received_valid_packet:
                        reconnect_delay = self._config.reconnect_initial_delay_sec
                        received_valid_packet = True
            except (OSError, TimeoutError, serial.SerialException) as exc:
                if not self._stop_event.is_set():
                    self._on_error(f"串口连接中断: {exc}")
            finally:
                self._connected_event.clear()
                self._fail_pending_commands()
                if serial_port is not None:
                    try:
                        # 所有退出路径都关闭字符设备，避免下一次启动时串口仍被占用。
                        serial_port.close()
                    except (OSError, serial.SerialException) as exc:
                        self._on_warning(f"关闭串口时发生异常: {exc}")

            if not self._stop_event.is_set():
                self._on_info(f"将在 {reconnect_delay:.1f} s 后重连")
                self._stop_event.wait(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2.0, self._config.reconnect_max_delay_sec
                )

    def _drain_commands(self, serial_port: SerialPort) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            with command.lock:
                if command.cancelled:
                    command.completed.set()
                    continue
                command.started = True
            try:
                self._write_payload(serial_port, command.payload)
                command.succeeded = True
            except (OSError, serial.SerialException) as exc:
                self._on_error(f"控制命令写入失败: {exc}")
                command.succeeded = False
                raise
            finally:
                command.completed.set()

    @staticmethod
    def _write_payload(serial_port: SerialPort, payload: bytes) -> None:
        written = serial_port.write(payload)
        if written != len(payload):
            raise OSError(f"串口仅写入 {written}/{len(payload)} 字节")
        serial_port.flush()

    def _fail_pending_commands(self) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            with command.lock:
                command.cancelled = True
                command.succeeded = False
                command.completed.set()
