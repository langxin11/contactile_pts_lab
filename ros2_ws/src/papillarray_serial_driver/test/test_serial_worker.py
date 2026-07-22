#!/usr/bin/env python3
"""串口命令、释放和自动重连的离线测试。"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

import papillarray_serial_driver.serial_worker as worker_module
from papillarray_serial_driver.protocol import ParsedPacket
from papillarray_serial_driver.serial_worker import (
    BIAS_COMMAND,
    START_SLIP_COMMAND,
    STOP_SLIP_COMMAND,
    SerialWorker,
    SerialWorkerConfig,
)


def _packet() -> ParsedPacket:
    return ParsedPacket(
        packet_counter=1,
        timestamp_us=2,
        pillar_forces=[np.empty((0, 3))],
        pillar_displacements=[np.empty((0, 3))],
        global_forces=[np.zeros(3)],
        global_torques=[np.zeros(3)],
    )


class _FakeReader:
    def __init__(self, _serial_port: object, _max_packet_bytes: int) -> None:
        pass

    def read_packet(self) -> ParsedPacket:
        time.sleep(0.005)
        return _packet()


class _BlockingReader:
    entered = threading.Event()
    release = threading.Event()

    def __init__(self, _serial_port: object, _max_packet_bytes: int) -> None:
        pass

    def read_packet(self) -> ParsedPacket:
        self.entered.set()
        self.release.wait(1.0)
        return _packet()


class _FakeSerial:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.closed = False

    def read(self, _size: int) -> bytes:
        return b""

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def _wait_for(predicate: Any, timeout_sec: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("等待条件超时")


def _config() -> SerialWorkerConfig:
    return SerialWorkerConfig(
        port="/dev/fake",
        baud_rate=115200,
        sampling_rate=500,
        timeout_sec=0.05,
        reconnect_initial_delay_sec=0.01,
        reconnect_max_delay_sec=0.02,
    )


def test_writes_sampling_rate_and_service_commands_in_io_thread(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(worker_module, "PTSProtocolReader", _FakeReader)
    fake_serial = _FakeSerial()
    callback_threads: list[int] = []
    worker = SerialWorker(
        _config(),
        lambda _packet_value: callback_threads.append(threading.get_ident()),
        serial_factory=lambda **_kwargs: fake_serial,
    )

    worker.start()
    _wait_for(lambda: worker.is_connected and bool(callback_threads))
    assert worker.send_command(BIAS_COMMAND)
    assert worker.send_command(START_SLIP_COMMAND)
    assert worker.send_command(STOP_SLIP_COMMAND)
    worker.stop()

    assert fake_serial.writes[:4] == [b"f500\n", b"z\n", b"S\n", b"s\n"]
    assert callback_threads[0] != threading.get_ident()
    assert fake_serial.closed


def test_returns_false_instead_of_queueing_command_while_disconnected() -> None:
    worker = SerialWorker(_config(), lambda _packet_value: None)

    assert worker.send_command(BIAS_COMMAND) is False


def test_does_not_send_command_after_wait_timeout(monkeypatch: Any) -> None:
    _BlockingReader.entered.clear()
    _BlockingReader.release.clear()
    monkeypatch.setattr(worker_module, "PTSProtocolReader", _BlockingReader)
    fake_serial = _FakeSerial()
    worker = SerialWorker(
        _config(),
        lambda _packet_value: None,
        serial_factory=lambda **_kwargs: fake_serial,
    )

    worker.start()
    assert _BlockingReader.entered.wait(1.0)
    assert worker.send_command(BIAS_COMMAND, timeout_sec=0.01) is False
    _BlockingReader.release.set()
    _wait_for(lambda: len(fake_serial.writes) >= 1)
    time.sleep(0.02)
    worker.stop()

    assert fake_serial.writes == [b"f500\n"]


def test_reconnects_after_open_failure(monkeypatch: Any) -> None:
    monkeypatch.setattr(worker_module, "PTSProtocolReader", _FakeReader)
    fake_serial = _FakeSerial()
    attempts = 0

    def serial_factory(**_kwargs: object) -> _FakeSerial:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("设备暂时不存在")
        return fake_serial

    received = threading.Event()
    worker = SerialWorker(
        _config(), lambda _packet_value: received.set(), serial_factory
    )

    worker.start()
    assert received.wait(1.0)
    worker.stop()

    assert attempts >= 2
    assert fake_serial.writes[0] == b"f500\n"
    assert fake_serial.closed
