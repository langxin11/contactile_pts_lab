#!/usr/bin/env python3
"""Contactile PTS Python SDK + DearPyGui 实时曲线查看器。"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Annotated, Literal

import dearpygui.dearpygui as dpg
import PTSDK_CXX_Pybind
import typer

BAUD_RATE = 115200
PARITY_NONE = 0
BYTE_SIZE_CHAR = "\x08"
DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_RATE_HZ = 500
DEFAULT_SENSOR = 0
DEFAULT_VIEW = "global"
DEFAULT_WINDOW_SEC = 4.0
DEFAULT_WIDTH = 1500
DEFAULT_HEIGHT = 1000
DEFAULT_FONT_SIZE = 20
GUI_FRAME_RATE_HZ = 60.0
PTS_MAX_SENSORS = 4
PTS_N_PILLARS = 9
DPG_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LAYOUT_RESERVED_HEIGHT = 105
LOCAL_PLOT_MIN_HEIGHT = 180
GLOBAL_PLOT_MIN_HEIGHT = 360

ViewMode = Literal["displacement", "force", "global"]
Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class Sample:
    """单帧 PTS 传感器采样数据。

    Args:
        timestamp_us: 传感器时间戳，单位 us。
        t_monotonic_ns: 主机单调时间戳，单位 ns。
        displacements: 9 个 pillar 位移，单位 mm，sensor frame，shape=(9, 3)。
        forces: 9 个 pillar 力，单位 N，sensor frame，shape=(9, 3)。
        global_force: 全局力，单位 N，sensor frame，shape=(3,)。
        global_torque: 全局力矩，单位 N·mm，sensor frame，shape=(3,)。
    """

    timestamp_us: int
    t_monotonic_ns: int
    displacements: tuple[Vector3, ...]
    forces: tuple[Vector3, ...]
    global_force: Vector3
    global_torque: Vector3


@dataclass
class LiveState:
    """采集线程和 GUI 线程共享的数据缓存。

    Args:
        max_samples: ring buffer 最大样本数。
    """

    max_samples: int
    samples: deque[Sample] = field(init=False)
    stop: threading.Event = field(default_factory=threading.Event)
    error: BaseException | None = None
    count: int = 0
    measured_rate_hz: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.samples = deque(maxlen=self.max_samples)

    def append(self, sample: Sample) -> None:
        """追加采样数据。

        Args:
            sample: 单帧采样数据。

        Returns:
            None。

        Raises:
            None。
        """
        with self._lock:
            self.samples.append(sample)
            self.count += 1
            if len(self.samples) >= 2:
                dt_us = self.samples[-1].timestamp_us - self.samples[-2].timestamp_us
                self.measured_rate_hz = 1_000_000.0 / dt_us if dt_us > 0 else 0.0

    def snapshot(self) -> tuple[list[Sample], int, float, BaseException | None]:
        """返回 GUI 线程可安全读取的数据快照。

        Args:
            None。

        Returns:
            样本列表、累计样本数、估算采样率和异常对象。

        Raises:
            None。
        """
        with self._lock:
            return list(self.samples), self.count, self.measured_rate_hz, self.error


class PtsSession:
    """管理 PTS Python SDK 连接，确保异常退出时释放串口。"""

    def __init__(
        self,
        port: str,
        rate_hz: int,
        sensor_index: int,
        *,
        bias: bool,
        confirm_no_load: bool,
    ) -> None:
        """初始化会话参数。

        Args:
            port: 串口设备路径。
            rate_hz: 控制器采样率，单位 Hz，可选 100/250/500/1000。
            sensor_index: 传感器索引，范围 0..3。
            bias: 是否发送 SDK bias 请求。
            confirm_no_load: 是否确认无负载，用于授权 bias。

        Raises:
            ValueError: 参数越界或危险 bias 未确认时抛出。
        """
        if not 0 <= sensor_index < PTS_MAX_SENSORS:
            raise ValueError(f"sensor 必须在 0..{PTS_MAX_SENSORS - 1} 之间")
        if bias and not confirm_no_load:
            raise ValueError("bias 校准前必须添加 --confirm-no-load")

        self.port = port
        self.rate_hz = rate_hz
        self.sensor_index = sensor_index
        self.bias = bias
        self.listener = None
        self.sensors = [PTSDK_CXX_Pybind.PTSDKSensor() for _ in range(PTS_MAX_SENSORS)]
        self._last_timestamp_us: int | None = None

    def __enter__(self) -> "PtsSession":
        if not os.path.exists(self.port):
            raise FileNotFoundError(f"串口设备不存在: {self.port}")

        self.listener = PTSDK_CXX_Pybind.PTSDKListener(logFlag=False)
        for sensor in self.sensors:
            self.listener.addSensor(sensor)

        result = self.listener.connectAndStartListening(
            self.port,
            BAUD_RATE,
            PARITY_NONE,
            BYTE_SIZE_CHAR,
            True,
        )
        if result != 0:
            raise RuntimeError(f"连接失败，错误码: {result}")

        if self.bias and not self.listener.sendBiasRequest():
            raise RuntimeError("Bias 请求失败")

        self._set_sampling_rate()
        time.sleep(0.2)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """释放串口连接。

        Args:
            None。

        Returns:
            None。

        Raises:
            None。
        """
        if self.listener is not None:
            self.listener.stopListeningAndDisconnect()
            self.listener = None

    def _set_sampling_rate(self) -> None:
        rate_map = {
            100: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_100,
            250: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_250,
            500: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500,
            1000: PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_1000,
        }
        try:
            sdk_rate = rate_map[self.rate_hz]
        except KeyError as exc:
            raise ValueError("rate 仅支持 100/250/500/1000 Hz") from exc
        self.listener.setSamplingRate(sdk_rate)

    def next_sample(self, timeout_sec: float = 2.0) -> Sample:
        """等待并返回下一帧新样本。

        Args:
            timeout_sec: 超时时间，单位 s。

        Returns:
            单帧采样数据，物理量使用 sensor frame。

        Raises:
            TimeoutError: 超时未收到新 timestamp 时抛出。
        """
        deadline = time.monotonic() + timeout_sec
        sleep_sec = max(0.0002, min(0.002, 0.5 / self.rate_hz))
        while True:
            sample = self.read_current()
            if self._is_new_sample(sample.timestamp_us):
                self._last_timestamp_us = sample.timestamp_us
                return sample
            if time.monotonic() > deadline:
                raise TimeoutError("等待新样本超时")
            time.sleep(sleep_sec)

    def read_current(self) -> Sample:
        """读取当前 SDK 缓存中的传感器数据。

        Args:
            None。

        Returns:
            当前采样数据。

        Raises:
            None。
        """
        sensor = self.sensors[self.sensor_index]
        displacements = tuple(
            tuple(float(v) for v in sensor.getPillarDisplacements(pillar_id))
            for pillar_id in range(PTS_N_PILLARS)
        )
        forces = tuple(
            tuple(float(v) for v in sensor.getPillarForces(pillar_id))
            for pillar_id in range(PTS_N_PILLARS)
        )
        return Sample(
            timestamp_us=int(sensor.getTimestamp_us()),
            t_monotonic_ns=time.monotonic_ns(),
            displacements=displacements,
            forces=forces,
            global_force=tuple(float(v) for v in sensor.getGlobalForce()),
            global_torque=tuple(float(v) for v in sensor.getGlobalTorque()),
        )

    def _is_new_sample(self, timestamp_us: int) -> bool:
        if timestamp_us == 0:
            return False
        return self._last_timestamp_us is None or timestamp_us > self._last_timestamp_us



def acquisition_worker(
    port: str,
    rate_hz: int,
    sensor_index: int,
    bias: bool,
    confirm_no_load: bool,
    state: LiveState,
) -> None:
    """后台采集线程。

    Args:
        port: 串口设备路径。
        rate_hz: 控制器采样率，单位 Hz。
        sensor_index: 传感器索引。
        bias: 是否发送 SDK bias 请求。
        confirm_no_load: 是否确认无负载。
        state: GUI 共享状态。

    Returns:
        None。

    Raises:
        None。异常会写入 state.error。
    """
    try:
        with PtsSession(
            port,
            rate_hz,
            sensor_index,
            bias=bias,
            confirm_no_load=confirm_no_load,
        ) as session:
            while not state.stop.is_set():
                state.append(session.next_sample())
    except Exception as exc:
        state.error = exc
        state.stop.set()


def setup_font(font_size: int) -> None:
    """设置 DearPyGui 全局字体。"""
    if os.path.exists(DPG_FONT_PATH):
        with dpg.font_registry():
            font = dpg.add_font(DPG_FONT_PATH, font_size)
        dpg.bind_font(font)


def visible_samples(samples: list[Sample], window_sec: float) -> tuple[list[Sample], list[float]]:
    """截取可见窗口并计算相对时间轴。

    Args:
        samples: 最近采样窗口。
        window_sec: 显示时间窗口，单位 s。

    Returns:
        可见样本和相对时间，时间单位 s，shape=(N,)。

    Raises:
        None。
    """
    if not samples:
        return [], []
    latest_ts = samples[-1].timestamp_us
    window_start = latest_ts - int(window_sec * 1_000_000)
    visible = [sample for sample in samples if sample.timestamp_us >= window_start]
    xs = [(sample.timestamp_us - latest_ts) / 1_000_000.0 for sample in visible]
    return visible, xs


def update_local_curves(samples: list[Sample], view: ViewMode, window_sec: float) -> None:
    """更新 9 个 pillar 子图。

    Args:
        samples: 最近采样窗口。
        view: `displacement` 或 `force`。
        window_sec: 显示时间窗口，单位 s。

    Returns:
        None。

    Raises:
        None。
    """
    visible, xs = visible_samples(samples, window_sec)
    if not visible:
        return

    for pillar_id in range(PTS_N_PILLARS):
        rows = [
            sample.displacements[pillar_id] if view == "displacement" else sample.forces[pillar_id]
            for sample in visible
        ]
        for axis_index, axis_name in enumerate(("x", "y", "z")):
            dpg.set_value(
                f"p{pillar_id}_{axis_name}",
                [xs, [row[axis_index] for row in rows]],
            )


def update_global_curves(samples: list[Sample], window_sec: float) -> None:
    """更新全局力和力矩曲线。

    Args:
        samples: 最近采样窗口。
        window_sec: 显示时间窗口，单位 s。

    Returns:
        None。

    Raises:
        None。
    """
    visible, xs = visible_samples(samples, window_sec)
    if not visible:
        return

    rows = [sample.global_force + sample.global_torque for sample in visible]
    for axis_index, tag in enumerate(("gfx", "gfy", "gfz", "gtx", "gty", "gtz")):
        dpg.set_value(tag, [xs, [row[axis_index] for row in rows]])


def add_local_plots(view: ViewMode, window_sec: float) -> None:
    """创建 3x3 pillar 曲线视图。

    Args:
        view: `displacement` 或 `force`。
        window_sec: 显示时间窗口，单位 s。

    Returns:
        None。

    Raises:
        None。
    """
    unit = "mm" if view == "displacement" else "N"
    y_limit = 5.0 if view == "displacement" else 10.0
    label = "Displacement" if view == "displacement" else "Force"

    with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchProp):
        for _ in range(3):
            dpg.add_table_column()
        for row in range(3):
            with dpg.table_row():
                for col in range(3):
                    pillar_id = row * 3 + col
                    with dpg.table_cell():
                        with dpg.plot(
                            label=f"P{pillar_id} {label}",
                            height=LOCAL_PLOT_MIN_HEIGHT,
                            width=-1,
                            tag=f"plot_p{pillar_id}",
                        ):
                            dpg.add_plot_legend()
                            x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=unit)
                            dpg.set_axis_limits(x_axis, -window_sec, 0)
                            dpg.set_axis_limits(y_axis, -y_limit, y_limit)
                            for tag_suffix, axis_label in (("x", "X"), ("y", "Y"), ("z", "Z")):
                                dpg.add_line_series(
                                    [],
                                    [],
                                    label=axis_label,
                                    parent=y_axis,
                                    tag=f"p{pillar_id}_{tag_suffix}",
                                )


def add_global_plot(window_sec: float) -> None:
    """创建单传感器全局曲线视图。

    Args:
        window_sec: 显示时间窗口，单位 s。

    Returns:
        None。

    Raises:
        None。
    """
    with dpg.plot(
        label="Global force + torque",
        height=GLOBAL_PLOT_MIN_HEIGHT,
        width=-1,
        tag="global_plot",
    ):
        dpg.add_plot_legend()
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Value")
        dpg.set_axis_limits(x_axis, -window_sec, 0)
        dpg.set_axis_limits(y_axis, -250, 250)
        for tag, label in (
            ("gfx", "Fx (N)"),
            ("gfy", "Fy (N)"),
            ("gfz", "Fz (N)"),
            ("gtx", "Tx (N.mm)"),
            ("gty", "Ty (N.mm)"),
            ("gtz", "Tz (N.mm)"),
        ):
            dpg.add_line_series([], [], label=label, parent=y_axis, tag=tag)


def update_plot_layout(view: ViewMode, last_height: int) -> int:
    """按窗口大小调整图表高度。

    Args:
        view: 当前视图类型。
        last_height: 上一次应用的 viewport client 高度。

    Returns:
        当前已应用的 viewport client 高度。

    Raises:
        None。
    """
    client_height = dpg.get_viewport_client_height()
    if client_height == last_height:
        return last_height

    available_height = max(client_height - LAYOUT_RESERVED_HEIGHT, LOCAL_PLOT_MIN_HEIGHT)
    if view == "global":
        dpg.configure_item(
            "global_plot",
            height=max(available_height, GLOBAL_PLOT_MIN_HEIGHT),
            width=-1,
        )
    else:
        plot_height = max(int(available_height / 3), LOCAL_PLOT_MIN_HEIGHT)
        for pillar_id in range(PTS_N_PILLARS):
            dpg.configure_item(f"plot_p{pillar_id}", height=plot_height, width=-1)
    return client_height


def run_live(
    port: str,
    rate_hz: int,
    sensor_index: int,
    view: ViewMode,
    window_sec: float,
    width: int,
    height: int,
    font_size: int,
    bias: bool,
    confirm_no_load: bool,
) -> None:
    """启动 DearPyGui 实时曲线查看器。

    Args:
        port: 串口设备路径。
        rate_hz: 控制器采样率，单位 Hz。
        sensor_index: 传感器索引。
        view: 显示内容。
        window_sec: 曲线窗口，单位 s。
        width: 窗口宽度，单位 px。
        height: 窗口高度，单位 px。
        font_size: 字体大小，单位 px。
        bias: 是否发送 SDK bias 请求。
        confirm_no_load: 是否确认无负载。

    Returns:
        None。

    Raises:
        RuntimeError: 采集线程返回异常时抛出。
    """
    max_samples = max(int(rate_hz * window_sec * 1.5), rate_hz)
    state = LiveState(max_samples=max_samples)
    worker = threading.Thread(
        target=acquisition_worker,
        args=(port, rate_hz, sensor_index, bias, confirm_no_load, state),
        daemon=True,
    )
    worker.start()

    dpg.create_context()
    setup_font(font_size)
    dpg.create_viewport(title="Contactile PTS Live", width=width, height=height)

    with dpg.window(label="Contactile PTS Live", tag="main_window"):
        dpg.add_text("启动采集...", tag="status")
        if view == "global":
            add_global_plot(window_sec)
        else:
            add_local_plots(view, window_sec)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

    try:
        frame_interval_sec = 1.0 / GUI_FRAME_RATE_HZ
        last_layout_height = 0
        while dpg.is_dearpygui_running() and not state.stop.is_set():
            frame_start = time.monotonic()
            last_layout_height = update_plot_layout(view, last_layout_height)
            samples, count, measured_rate_hz, error = state.snapshot()
            if error is not None:
                raise error

            if view == "global":
                update_global_curves(samples, window_sec)
            else:
                update_local_curves(samples, view, window_sec)

            dpg.set_value(
                "status",
                f"port={port} sensor={sensor_index} view={view} "
                f"rate={rate_hz}Hz measured={measured_rate_hz:.1f}Hz samples={count}",
            )
            dpg.render_dearpygui_frame()
            elapsed = time.monotonic() - frame_start
            if elapsed < frame_interval_sec:
                time.sleep(frame_interval_sec - elapsed)
    finally:
        state.stop.set()
        worker.join(timeout=3.0)
        dpg.destroy_context()


def main(
    port: Annotated[str, typer.Option("--port", "-p")] = DEFAULT_PORT,
    rate_hz: Annotated[int, typer.Option("--rate", "-r")] = DEFAULT_RATE_HZ,
    sensor_index: Annotated[int, typer.Option("--sensor", "-s", min=0, max=3)] = DEFAULT_SENSOR,
    view: Annotated[ViewMode, typer.Option("--view", "-v")] = DEFAULT_VIEW,
    window_sec: Annotated[float, typer.Option("--window", "-w", min=1.0)] = DEFAULT_WINDOW_SEC,
    bias: Annotated[bool, typer.Option("--bias/--no-bias")] = False,
    confirm_no_load: Annotated[bool, typer.Option("--confirm-no-load")] = False,
) -> None:
    """启动 PTS Python SDK + DearPyGui 实时曲线查看器。

    Args:
        port: 串口设备路径。
        rate_hz: 控制器采样率，单位 Hz。
        sensor_index: 传感器索引。
        view: 显示内容，`displacement`、`force` 或 `global`。
        window_sec: 曲线显示窗口，单位 s。
        bias: 是否发送 SDK bias 请求。
        confirm_no_load: 是否确认无负载。

    Returns:
        None。

    Raises:
        typer.BadParameter: 参数不合法时抛出。
    """
    if rate_hz not in {100, 250, 500, 1000}:
        raise typer.BadParameter("--rate 仅支持 100/250/500/1000")
    if bias and not confirm_no_load:
        raise typer.BadParameter("--bias 必须同时添加 --confirm-no-load")

    run_live(
        port=port,
        rate_hz=rate_hz,
        sensor_index=sensor_index,
        view=view,
        window_sec=window_sec,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        font_size=DEFAULT_FONT_SIZE,
        bias=bias,
        confirm_no_load=confirm_no_load,
    )


if __name__ == "__main__":
    typer.run(main)
