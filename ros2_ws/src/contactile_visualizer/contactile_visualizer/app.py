#!/usr/bin/env python3
"""ROS2 Contactile PTS data viewer."""

from __future__ import annotations

import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Annotated, Literal

import rclpy
from rclpy.node import Node
from sensor_interfaces.msg import PillarState, SensorState
import typer

try:
    from PyQt5 import QtCore, QtWidgets
except ModuleNotFoundError as exc:
    raise SystemExit("错误: 未安装 PyQt5，请先安装 python3-pyqt5") from exc

try:
    import pyqtgraph as pg
except ModuleNotFoundError as exc:
    raise SystemExit("错误: 未安装 pyqtgraph，请先安装 python3-pyqtgraph") from exc


DEFAULT_TOPIC = "/hub_0/sensor_0"
DEFAULT_REFRESH_HZ = 15
DEFAULT_HISTORY_SEC = 5.0
DEFAULT_PILLAR_ID = 0
ROS_ARGS = [sys.argv[0]]

ViewMode = Literal["displacement", "force", "global"]
DisplayMode = Literal["text", "curve"]


@dataclass
class SensorSnapshot:
    """GUI 显示所需的最新传感器状态。

    Args:
        message: 最近一帧 ROS2 传感器消息，物理量使用 sensor frame。
        received_s: 主机接收时间，单位 s。
    """

    message: SensorState
    received_s: float


@dataclass
class DataHistory:
    """曲线缓存。

    Args:
        max_age_s: 保留的历史窗口长度，单位 s。

    Returns:
        None。

    Raises:
        ValueError: 当历史窗口长度不为正数时抛出。
    """

    max_age_s: float
    view: ViewMode
    pillar_id: int
    samples: deque[tuple[float, tuple[float, ...]]] = field(default_factory=deque)
    start_s: float | None = None

    def __post_init__(self) -> None:
        if self.max_age_s <= 0:
            raise ValueError("history-sec 必须大于 0")

    def append(self, received_s: float, msg: SensorState) -> None:
        """追加一帧传感器消息。

        Args:
            received_s: 主机接收时间，单位 s。
            msg: ROS2 传感器状态消息。

        Returns:
            None。

        Raises:
            None。
        """
        if self.start_s is None:
            self.start_s = received_s

        rel_s = received_s - self.start_s
        values = self._extract_values(msg)
        if values is not None:
            self.samples.append((rel_s, values))

        cutoff_s = rel_s - self.max_age_s
        while self.samples and self.samples[0][0] < cutoff_s:
            self.samples.popleft()

    def _extract_values(self, msg: SensorState) -> tuple[float, ...] | None:
        """提取当前视图需要缓存的数值。

        Args:
            msg: ROS2 传感器状态消息。

        Returns:
            `global` 返回 Fx/Fy/Fz/Tx/Ty/Tz；单柱视图返回 X/Y/Z；找不到柱时返回 None。

        Raises:
            None。
        """
        if self.view == "global":
            return (msg.gfx, msg.gfy, msg.gfz, msg.gtx, msg.gty, msg.gtz)

        pillar = find_pillar(msg, self.pillar_id)
        if pillar is None:
            return None
        if self.view == "displacement":
            return (pillar.dx, pillar.dy, pillar.dz)
        return (pillar.fx, pillar.fy, pillar.fz)

    def global_arrays(self) -> tuple[list[float], list[float], list[float], list[float], list[float], list[float], list[float]]:
        """返回全局力和力矩曲线数组。

        Args:
            None。

        Returns:
            shape=(N,) 的时间、Fx、Fy、Fz、Tx、Ty、Tz 数组；时间单位 s，力单位 N，力矩单位 N·mm。

        Raises:
            None。
        """
        if not self.samples:
            return [], [], [], [], [], [], []

        xs: list[float] = []
        fxs: list[float] = []
        fys: list[float] = []
        fzs: list[float] = []
        txs: list[float] = []
        tys: list[float] = []
        tzs: list[float] = []

        for rel_s, values in self.samples:
            xs.append(rel_s)
            fxs.append(values[0])
            fys.append(values[1])
            fzs.append(values[2])
            txs.append(values[3])
            tys.append(values[4])
            tzs.append(values[5])

        return xs, fxs, fys, fzs, txs, tys, tzs

    def pillar_arrays(self) -> tuple[list[float], list[float], list[float], list[float]]:
        """返回单柱位移或力曲线数组。

        Args:
            None。

        Returns:
            shape=(N,) 的时间、X、Y、Z 数组；时间单位 s，位移单位 mm 或力单位 N。

        Raises:
            None。
        """
        if not self.samples:
            return [], [], [], []

        xs: list[float] = []
        vals_x: list[float] = []
        vals_y: list[float] = []
        vals_z: list[float] = []

        for rel_s, values in self.samples:
            xs.append(rel_s)
            vals_x.append(values[0])
            vals_y.append(values[1])
            vals_z.append(values[2])

        return xs, vals_x, vals_y, vals_z


class SensorSubscriber(Node):
    """订阅 Contactile PTS 传感器状态的 ROS2 节点。"""

    def __init__(
        self,
        topic: str,
        history_sec: float,
        view: ViewMode,
        display: DisplayMode,
        pillar_id: int,
    ) -> None:
        """初始化订阅节点。

        Args:
            topic: SensorState 话题名。
            history_sec: 曲线保留时间，单位 s。
            view: 显示内容类型。
            display: 显示形式，文本或曲线。
            pillar_id: 单柱显示使用的柱编号。

        Returns:
            None。

        Raises:
            ValueError: 当 history_sec 不为正数时抛出。
        """
        super().__init__("contactile_data_viewer")
        self._display = display
        self._lock = threading.Lock()
        self._snapshot: SensorSnapshot | None = None
        self._history = DataHistory(max_age_s=history_sec, view=view, pillar_id=pillar_id)
        self.create_subscription(SensorState, topic, self._on_sensor_state, 10)
        self.get_logger().info(f"Subscribing to {topic}")

    def _on_sensor_state(self, msg: SensorState) -> None:
        # callback 只更新缓存，避免 ROS2 线程和 Qt 绘图互相阻塞。
        received_s = time.monotonic()
        with self._lock:
            self._snapshot = SensorSnapshot(msg, received_s)
            if self._display == "curve":
                self._history.append(received_s, msg)

    def read_state(self) -> tuple[SensorSnapshot | None, DataHistory]:
        """读取 GUI 刷新所需状态。

        Args:
            None。

        Returns:
            最新快照和曲线缓存；调用者只读使用。

        Raises:
            None。
        """
        with self._lock:
            return self._snapshot, self._history


def find_pillar(msg: SensorState, pillar_id: int) -> PillarState | None:
    """按编号查找单柱状态。

    Args:
        msg: ROS2 传感器状态消息。
        pillar_id: 柱编号。

    Returns:
        找到时返回 PillarState，否则返回 None。

    Raises:
        None。
    """
    for pillar in msg.pillars:
        if pillar.id == pillar_id:
            return pillar
    return None


class DataViewerWindow(QtWidgets.QMainWindow):
    """Contactile PTS 数据查看主窗口。"""

    def __init__(
        self,
        node: SensorSubscriber,
        topic: str,
        view: ViewMode,
        display: DisplayMode,
        pillar_id: int,
        refresh_hz: int,
    ) -> None:
        """创建 Qt 主窗口。

        Args:
            node: ROS2 订阅节点。
            topic: SensorState 话题名。
            view: 显示内容类型。
            display: 显示形式，文本或曲线。
            pillar_id: 单柱显示使用的柱编号。
            refresh_hz: GUI 刷新频率，单位 Hz。

        Returns:
            None。

        Raises:
            ValueError: 当 refresh_hz 不为正数时抛出。
        """
        super().__init__()
        if refresh_hz <= 0:
            raise ValueError("refresh-hz 必须大于 0")

        self._node = node
        self._topic = topic
        self._view = view
        self._display = display
        self._pillar_id = pillar_id

        self.setWindowTitle("Contactile PTS Data Viewer")
        self.resize(960, 620)
        self._build_ui()

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(int(1000 / refresh_hz))

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = self._title_text()
        self._title_label = QtWidgets.QLabel(title)
        self._title_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self._title_label)

        if self._display == "text":
            self._value_label = QtWidgets.QLabel("等待数据...")
            self._value_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self._value_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
            self._value_label.setStyleSheet("font-family: monospace; font-size: 18px;")
            layout.addWidget(self._value_label, stretch=1)
        else:
            self._build_curve_ui(layout)

        self._status_label = QtWidgets.QLabel("等待数据...")
        self._status_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self._status_label)
        self.setCentralWidget(central)

    def _build_curve_ui(self, layout: QtWidgets.QVBoxLayout) -> None:
        if self._view == "global":
            self._force_plot = self._new_plot("Global force", "N")
            self._torque_plot = self._new_plot("Global torque", "N.mm")
            self._fx_curve = self._force_plot.plot(pen=pg.mkPen("#f2cc38", width=2), name="Fx")
            self._fy_curve = self._force_plot.plot(pen=pg.mkPen("#51cf66", width=2), name="Fy")
            self._fz_curve = self._force_plot.plot(pen=pg.mkPen("#339af0", width=2), name="Fz")
            self._tx_curve = self._torque_plot.plot(pen=pg.mkPen("#f2cc38", width=2), name="Tx")
            self._ty_curve = self._torque_plot.plot(pen=pg.mkPen("#51cf66", width=2), name="Ty")
            self._tz_curve = self._torque_plot.plot(pen=pg.mkPen("#339af0", width=2), name="Tz")
            self._force_plot.addLegend()
            self._torque_plot.addLegend()
            layout.addWidget(self._force_plot, stretch=1)
            layout.addWidget(self._torque_plot, stretch=1)
        else:
            unit = "mm" if self._view == "displacement" else "N"
            self._pillar_plot = self._new_plot(self._title_text(), unit)
            self._x_curve = self._pillar_plot.plot(pen=pg.mkPen("#f2cc38", width=2), name="X")
            self._y_curve = self._pillar_plot.plot(pen=pg.mkPen("#51cf66", width=2), name="Y")
            self._z_curve = self._pillar_plot.plot(pen=pg.mkPen("#339af0", width=2), name="Z")
            self._pillar_plot.addLegend()
            layout.addWidget(self._pillar_plot, stretch=1)

    def _new_plot(self, title: str, unit: str) -> pg.PlotWidget:
        plot = pg.PlotWidget(title=title)
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.setLabel("bottom", "time", units="s")
        plot.setLabel("left", "value", units=unit)
        return plot

    def _refresh(self) -> None:
        snapshot, history = self._node.read_state()
        if snapshot is None:
            return

        if self._display == "text":
            self._draw_text(snapshot.message)
        elif self._view == "global":
            self._draw_global_curves(history)
        else:
            self._draw_pillar_curves(history)

        self._draw_status(snapshot)

    def _draw_text(self, msg: SensorState) -> None:
        if self._view == "global":
            text = "\n".join(
                [
                    "Global force (N)",
                    f"  Fx: {msg.gfx: .6f}",
                    f"  Fy: {msg.gfy: .6f}",
                    f"  Fz: {msg.gfz: .6f}",
                    "",
                    "Global torque (N.mm)",
                    f"  Tx: {msg.gtx: .6f}",
                    f"  Ty: {msg.gty: .6f}",
                    f"  Tz: {msg.gtz: .6f}",
                ]
            )
        else:
            pillar = find_pillar(msg, self._pillar_id)
            if pillar is None:
                text = f"未找到 pillar {self._pillar_id}，当前消息包含 {len(msg.pillars)} 个 pillar。"
            elif self._view == "displacement":
                text = "\n".join(
                    [
                        f"Pillar {self._pillar_id} displacement (mm)",
                        f"  DX: {pillar.dx: .6f}",
                        f"  DY: {pillar.dy: .6f}",
                        f"  DZ: {pillar.dz: .6f}",
                    ]
                )
            else:
                text = "\n".join(
                    [
                        f"Pillar {self._pillar_id} force (N)",
                        f"  FX: {pillar.fx: .6f}",
                        f"  FY: {pillar.fy: .6f}",
                        f"  FZ: {pillar.fz: .6f}",
                    ]
                )

        self._value_label.setText(text)

    def _draw_global_curves(self, history: DataHistory) -> None:
        xs, fxs, fys, fzs, txs, tys, tzs = history.global_arrays()
        self._fx_curve.setData(xs, fxs)
        self._fy_curve.setData(xs, fys)
        self._fz_curve.setData(xs, fzs)
        self._tx_curve.setData(xs, txs)
        self._ty_curve.setData(xs, tys)
        self._tz_curve.setData(xs, tzs)

    def _draw_pillar_curves(self, history: DataHistory) -> None:
        xs, vals_x, vals_y, vals_z = history.pillar_arrays()
        self._x_curve.setData(xs, vals_x)
        self._y_curve.setData(xs, vals_y)
        self._z_curve.setData(xs, vals_z)

    def _draw_status(self, snapshot: SensorSnapshot) -> None:
        msg = snapshot.message
        age_ms = (time.monotonic() - snapshot.received_s) * 1000.0
        self._status_label.setText(
            " | ".join(
                [
                    f"topic={self._topic}",
                    f"pillars={len(msg.pillars)}",
                    f"friction={msg.friction_est:.3f}",
                    f"target grip={msg.target_grip_force:.3f} N",
                    f"slip active={msg.is_sd_active}",
                    f"contact={msg.is_contact}",
                    f"age={age_ms:.0f} ms",
                ]
            )
        )

    def _title_text(self) -> str:
        if self._view == "global":
            return "Global 3D force + Global 3D torque"
        if self._view == "displacement":
            return f"Pillar {self._pillar_id} 3D displacement"
        return f"Pillar {self._pillar_id} 3D force"


def run_gui(
    topic: str,
    view: ViewMode,
    display: DisplayMode,
    pillar_id: int,
    refresh_hz: int,
    history_sec: float,
) -> None:
    """启动 ROS2 + Qt 数据查看器。

    Args:
        topic: 订阅的 SensorState 话题名。
        view: 显示内容类型。
        display: 显示形式，文本或曲线。
        pillar_id: 单柱显示使用的柱编号。
        refresh_hz: GUI 刷新频率，单位 Hz。
        history_sec: 曲线保留时间，单位 s。

    Returns:
        None。

    Raises:
        ValueError: 参数不合法时抛出。
    """
    rclpy.init(args=ROS_ARGS)
    node = SensorSubscriber(
        topic=topic,
        history_sec=history_sec,
        view=view,
        display=display,
        pillar_id=pillar_id,
    )

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    window = DataViewerWindow(
        node=node,
        topic=topic,
        view=view,
        display=display,
        pillar_id=pillar_id,
        refresh_hz=refresh_hz,
    )
    window.show()

    try:
        app.exec_()
    finally:
        # Qt 退出时主动释放 ROS2 节点，避免后台线程持有 DDS 资源。
        node.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)


def main(
    topic: Annotated[str, typer.Option("--topic", "-t")] = DEFAULT_TOPIC,
    view: Annotated[ViewMode, typer.Option("--view", "-v")] = "global",
    display: Annotated[DisplayMode, typer.Option("--display", "-d")] = "curve",
    pillar_id: Annotated[int, typer.Option("--pillar-id", "-p")] = DEFAULT_PILLAR_ID,
    refresh_hz: Annotated[int, typer.Option("--refresh-hz")] = DEFAULT_REFRESH_HZ,
    history_sec: Annotated[float, typer.Option("--history-sec")] = DEFAULT_HISTORY_SEC,
) -> None:
    """启动 Contactile PTS 数据查看 GUI。

    Args:
        topic: SensorState 话题名。
        view: 显示内容，`displacement`、`force` 或 `global`。
        display: 显示形式，`text` 或 `curve`。
        pillar_id: 单柱显示使用的柱编号。
        refresh_hz: GUI 刷新频率，单位 Hz。
        history_sec: 曲线保留时间，单位 s。

    Returns:
        None。

    Raises:
        typer.BadParameter: 参数不合法时抛出。
    """
    if pillar_id < 0:
        raise typer.BadParameter("--pillar-id 必须大于等于 0")
    if refresh_hz <= 0:
        raise typer.BadParameter("--refresh-hz 必须大于 0")
    if history_sec <= 0:
        raise typer.BadParameter("--history-sec 必须大于 0")

    run_gui(
        topic=topic,
        view=view,
        display=display,
        pillar_id=pillar_id,
        refresh_hz=refresh_hz,
        history_sec=history_sec,
    )


def cli() -> None:
    """解析命令行参数并启动 GUI。

    Args:
        None。

    Returns:
        None。

    Raises:
        typer.BadParameter: 参数不合法时抛出。
    """
    global ROS_ARGS

    if "--ros-args" in sys.argv:
        ros_args_index = sys.argv.index("--ros-args")
        ROS_ARGS = [sys.argv[0], *sys.argv[ros_args_index:]]
        sys.argv = sys.argv[:ros_args_index]

    typer.run(main)


if __name__ == "__main__":
    cli()
