#!/usr/bin/env python3
"""Contactile PTS 传感器的 Rerun 2D 矢量图层、时序曲线与张量可视化入口。"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Annotated

import numpy as np
import rerun as rr
import rerun.blueprint as rrb
import serial
import typer

from pts_protocol import PTSProtocolReader
from pts_vis_core import (
    COLOR_AXIS_X,
    COLOR_AXIS_Y,
    COLOR_BASE,
    COLOR_CROSSHAIR,
    COLOR_LABEL,
    COLOR_OUTLINE,
    PTS_N_PILLARS,
    PTSFrame,
    PTSVisualizationConfig,
    active_area_outline,
    compute_pillar_geometry,
    crosshair_segments,
    frames_from_packet,
    mock_frame,
    pillar_base_centers,
)
from pts_vis_image import PTSImageRenderer

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_TIMEOUT_SEC = 1.0
DEFAULT_ENTITY_PATH = "tactile/sen0"
DEFAULT_DUAL_PATHS = ("tactile/sen0", "tactile/sen1")
DEFAULT_MOCK_HZ = 60.0
DEFAULT_MOCK_FRAMES = 180
# Rerun Spatial2DView 默认 +y 向下，翻转 y 轴使屏幕上方对应 sensor frame +y
RERUN_Y_FLIP = np.array([1.0, -1.0], dtype=np.float64)

app = typer.Typer(no_args_is_help=True)


def _to_rerun_xy(xy_mm: np.ndarray) -> np.ndarray:
    """将 sensor frame 平面坐标 (+y 向上) 转换为 Rerun 2D 视图坐标 (+y 向下)。

    Args:
        xy_mm: 传感器平面坐标，单位 mm，sensor frame，shape=(..., 2)。

    Returns:
        Rerun 2D 坐标，单位 mm，shape 同输入。
    """
    return np.asarray(xy_mm, dtype=np.float64) * RERUN_Y_FLIP


class RerunLogger:
    """将 PTS 触觉帧记录到 Rerun Viewer 或 RRD 文件。

    Args:
        application_id: Rerun 应用标识。
        config: PTS 2D 可视化配置。
        spawn: 是否拉起本地 Rerun Viewer 窗口。
        save_path: 可选 RRD 文件保存路径。
        sensor_paths: 预设传感器 entity_path 列表，用于生成 Blueprint。
        log_image: 是否额外将 OpenCV 栅格化触觉图作为 ``rr.Image`` 记录。
        recording: 可选外部注入的 ``RecordingStream``，便于单元测试替身拦截。
    """

    def __init__(
        self,
        application_id: str = "contactile_pts_lab",
        *,
        config: PTSVisualizationConfig | None = None,
        spawn: bool = False,
        save_path: Path | None = None,
        sensor_paths: tuple[str, ...] = (DEFAULT_ENTITY_PATH,),
        log_image: bool = False,
        recording: rr.RecordingStream | None = None,
    ) -> None:
        self.config = config or PTSVisualizationConfig()
        self.sensor_paths = tuple(sensor_paths)
        self.log_image = log_image
        self._static_logged: set[str] = set()
        self._image_renderers: dict[str, PTSImageRenderer] = {}
        self._seq = 0

        if recording is not None:
            self._rec = recording
        else:
            self._rec = rr.RecordingStream(application_id)
            if save_path is not None:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                self._rec.save(str(save_path))
            if spawn:
                self._rec.spawn()

        self._send_pts_blueprint()

    def _send_pts_blueprint(self) -> rrb.Blueprint:
        """根据单路或双路传感器配置自动生成并发送 Rerun Blueprint 布局。

        Returns:
            生成的 ``rrb.Blueprint`` 对象。
        """
        if len(self.sensor_paths) == 1:
            path = self.sensor_paths[0]
            blueprint = rrb.Blueprint(
                rrb.Horizontal(
                    rrb.Spatial2DView(origin=f"{path}/pts", name=f"{path} PTS 2D"),
                    rrb.Vertical(
                        rrb.TimeSeriesView(origin=f"{path}/force", name=f"{path} Global Force (N)"),
                        rrb.TensorView(origin=f"{path}/pressure", name=f"{path} Fz Grid (N)"),
                    ),
                    column_shares=[3, 2],
                ),
                collapse_panels=True,
            )
        else:
            spatial_views = [
                rrb.Spatial2DView(origin=f"{p}/pts", name=f"{p} PTS 2D") for p in self.sensor_paths
            ]
            force_views = [
                rrb.TimeSeriesView(origin=f"{p}/force", name=f"{p} Force (N)")
                for p in self.sensor_paths
            ]
            tensor_views = [
                rrb.TensorView(origin=f"{p}/pressure", name=f"{p} Fz Grid")
                for p in self.sensor_paths
            ]
            blueprint = rrb.Blueprint(
                rrb.Vertical(
                    rrb.Horizontal(*spatial_views),
                    rrb.Horizontal(*force_views),
                    rrb.Horizontal(*tensor_views),
                    row_shares=[3, 2, 2],
                ),
                collapse_panels=True,
            )

        if hasattr(self._rec, "send_blueprint"):
            self._rec.send_blueprint(blueprint)
        return blueprint

    def _log_static_pts_layers(self, pts_root: str) -> None:
        """记录单个传感器不随帧变化的静态图层，避免每帧重复传输固定几何。"""
        if pts_root in self._static_logged:
            return
        cfg = self.config
        outline = _to_rerun_xy(active_area_outline(cfg))
        self._rec.log(
            f"{pts_root}/active_area_outline",
            rr.LineStrips2D([outline], colors=[COLOR_OUTLINE], radii=0.08, draw_order=-2.0),
            static=True,
        )

        base_xy = _to_rerun_xy(pillar_base_centers(cfg.pillar_spacing_mm))
        self._rec.log(
            f"{pts_root}/base_circles",
            rr.Points2D(
                base_xy,
                radii=cfg.base_radius_mm,
                colors=[COLOR_BASE],
                draw_order=-1.0,
            ),
            static=True,
        )

        if cfg.show_labels:
            # 标签放在基底圆上沿略偏外处，防止被顶圆十字准线遮挡
            label_xy = _to_rerun_xy(
                pillar_base_centers(cfg.pillar_spacing_mm)
                + np.array([0.0, cfg.base_radius_mm + 0.6])
            )
            self._rec.log(
                f"{pts_root}/labels",
                rr.Points2D(
                    label_xy,
                    radii=0.01,
                    colors=[COLOR_LABEL],
                    labels=[f"P{i}" for i in range(PTS_N_PILLARS)],
                    show_labels=True,
                    draw_order=2.0,
                ),
                static=True,
            )

        if cfg.show_frame:
            corner = active_area_outline(cfg)[0] + np.array([-1.2, -1.2])
            origin = _to_rerun_xy(np.vstack([corner, corner]))
            axis_len = cfg.pillar_spacing_mm * 0.45
            vectors = _to_rerun_xy(np.array([[axis_len, 0.0], [0.0, axis_len]]))
            self._rec.log(
                f"{pts_root}/frame_axes",
                rr.Arrows2D(
                    origins=origin,
                    vectors=vectors,
                    colors=[COLOR_AXIS_X, COLOR_AXIS_Y],
                    labels=["+x", "+y"],
                    show_labels=True,
                    radii=0.08,
                    draw_order=2.0,
                ),
                static=True,
            )

        self._static_logged.add(pts_root)

    def _log_pts_entities(self, frame: PTSFrame, entity_path: str) -> None:
        """从单帧数据提取 pillar 几何并绘制多层 2D 视图。

        Args:
            frame: 单传感器数据帧（物理量单位：位移 mm，力 N，坐标系 sensor frame）。
            entity_path: 传感器根实体路径，例如 ``tactile/sen0``。
        """
        pts_root = f"{entity_path}/pts"
        self._log_static_pts_layers(pts_root)

        geom = compute_pillar_geometry(frame, self.config)
        self._rec.log(
            f"{pts_root}/tip_circles",
            rr.Points2D(
                _to_rerun_xy(geom.tip_centers),
                radii=geom.tip_radii,
                colors=geom.colors,
                draw_order=0.0,
            ),
        )

        if self.config.show_crosshair:
            segments = _to_rerun_xy(
                crosshair_segments(geom.tip_centers, self.config.crosshair_half_mm)
            )
            self._rec.log(
                f"{pts_root}/crosshairs",
                rr.LineStrips2D(
                    segments,
                    colors=[COLOR_CROSSHAIR],
                    radii=0.04,
                    draw_order=1.0,
                ),
            )

    def log_tactile_frame(
        self,
        frame: PTSFrame,
        entity_path: str = DEFAULT_ENTITY_PATH,
    ) -> None:
        """记录单路传感器的一帧数据，通过 entity_path 隔离多路传感器。

        Args:
            frame: 单传感器触觉帧，包含 9 柱位移 (mm)、力 (N) 及全局力 (N) / 力矩 (N·mm)。
            entity_path: 该传感器在 Rerun 中的实体根路径。
        """
        self._seq += 1
        self._rec.set_time("frame", sequence=self._seq)
        self._rec.set_time("sensor_time", duration=frame.timestamp_us * 1e-6)

        for axis, value in zip(("fx", "fy", "fz"), frame.global_force):
            self._rec.log(f"{entity_path}/force/{axis}", rr.Scalars(float(value)))
        for axis, value in zip(("tx", "ty", "tz"), frame.global_torque):
            self._rec.log(f"{entity_path}/torque/{axis}", rr.Scalars(float(value)))

        # 将 9 柱法向力重排为 3×3 张量，供 TensorView 显示压力分布热力图
        fz_grid = frame.forces[:, 2].reshape(3, 3).astype(np.float32)
        self._rec.log(
            f"{entity_path}/pressure",
            rr.Tensor(fz_grid, dim_names=("row", "col")),
        )

        if self.config.enabled:
            self._log_pts_entities(frame, entity_path)

        if self.log_image:
            renderer = self._image_renderers.get(entity_path)
            if renderer is None:
                renderer = PTSImageRenderer(self.config, title=entity_path)
                self._image_renderers[entity_path] = renderer
            self._rec.log(f"{entity_path}/image", rr.Image(renderer.render(frame)))

    def close(self) -> None:
        """刷新并断开 Rerun 输出流。"""
        if hasattr(self._rec, "flush"):
            self._rec.flush()
        if hasattr(self._rec, "disconnect"):
            self._rec.disconnect()


def run_rerun_visualizer(
    *,
    port: str = DEFAULT_PORT,
    baud_rate: int = DEFAULT_BAUD_RATE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    samples: int = DEFAULT_MOCK_FRAMES,
    dual: bool = False,
    mock: bool = False,
    spawn: bool = True,
    save_rrd: Path | None = None,
    log_image: bool = False,
    config: PTSVisualizationConfig | None = None,
) -> int:
    """运行 Rerun PTS 可视化主循环。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        timeout_sec: 串口单次读取超时，单位 s。
        samples: 采集帧数（<=0 表示持续运行直到 Ctrl+C）。
        dual: 是否启用双路传感器布局（SEN0 + SEN1）。
        mock: 是否使用模拟数据而不访问真实串口。
        spawn: 是否启动本地 Rerun Viewer 窗口。
        save_rrd: 可选 RRD 录制文件路径。
        log_image: 是否同时记录 OpenCV 渲染的触觉图像。
        config: 可选自定义 PTSVisualizationConfig。

    Returns:
        进程退出码，0 表示正常结束。
    """
    sensor_paths = DEFAULT_DUAL_PATHS if dual else (DEFAULT_ENTITY_PATH,)
    if not mock and not os.path.exists(port):
        typer.secho(f"错误: 串口设备不存在: {port}", err=True)
        return 1

    logger = RerunLogger(
        config=config,
        spawn=spawn,
        save_path=save_rrd,
        sensor_paths=sensor_paths,
        log_image=log_image,
    )
    try:
        if mock:
            dt = 1.0 / DEFAULT_MOCK_HZ
            count = 0
            while samples <= 0 or count < samples:
                t_s = count * dt
                for idx, path in enumerate(sensor_paths):
                    logger.log_tactile_frame(mock_frame(t_s, phase=idx * 1.2), entity_path=path)
                count += 1
                if spawn:
                    time.sleep(dt)
            typer.echo(f"Rerun mock 可视化完成，共记录 {count} 帧")
            return 0

        with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout_sec) as ser:
            reader = PTSProtocolReader(ser)
            typer.echo(f"已连接 {port} ({baud_rate} baud)，开始推送到 Rerun...")
            count = 0
            while samples <= 0 or count < samples:
                packet = reader.read_packet()
                frames = frames_from_packet(packet)
                for frame, path in zip(frames, sensor_paths):
                    logger.log_tactile_frame(frame, entity_path=path)
                count += 1
    except PermissionError:
        # 串口权限不足时只能由用户调整 dialout 组，脚本禁止调用 sudo
        typer.secho(f"错误: 没有权限访问 {port}，请将当前用户加入 dialout 组", err=True)
        return 1
    except (OSError, ValueError, TimeoutError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        return 1
    except KeyboardInterrupt:
        # 确保串口上下文安全退出后再返回中断状态码
        typer.secho("收到中断信号，已安全释放串口与 Rerun 连接", err=True)
        return 130
    finally:
        logger.close()

    return 0


@app.command()
def main(
    port: Annotated[str, typer.Option("--port", "-p", help="串口设备路径")] = DEFAULT_PORT,
    baud_rate: Annotated[
        int, typer.Option("--baud-rate", "-b", help="串口波特率")
    ] = DEFAULT_BAUD_RATE,
    samples: Annotated[
        int, typer.Option("--samples", "-n", help="采集帧数，0 表示持续运行")
    ] = DEFAULT_MOCK_FRAMES,
    dual: Annotated[bool, typer.Option("--dual", help="双路传感器并排模式")] = False,
    mock: Annotated[bool, typer.Option("--mock", help="使用模拟数据，不依赖硬件")] = False,
    no_spawn: Annotated[
        bool, typer.Option("--no-spawn", help="不弹出 Rerun 窗口，仅写入文件或静默运行")
    ] = False,
    save_rrd: Annotated[Path | None, typer.Option("--save-rrd", help="保存 RRD 文件路径")] = None,
    log_image: Annotated[
        bool, typer.Option("--log-image", help="同时记录 OpenCV 栅格化触觉图像")
    ] = False,
    contact_threshold: Annotated[
        float, typer.Option("--contact-threshold", help="接触力阈值 (N)")
    ] = 0.2,
) -> None:
    """启动 Contactile PTS 的 Rerun 2D 可视化。"""
    cfg = PTSVisualizationConfig(contact_threshold_n=contact_threshold)
    code = run_rerun_visualizer(
        port=port,
        baud_rate=baud_rate,
        samples=samples,
        dual=dual,
        mock=mock,
        spawn=not no_spawn,
        save_rrd=save_rrd,
        log_image=log_image,
        config=cfg,
    )
    raise typer.Exit(code)


if __name__ == "__main__":
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
