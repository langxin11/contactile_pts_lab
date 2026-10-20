#!/usr/bin/env python3
"""Contactile PTS 传感器的 Foxglove 触觉图像 (CompressedImage) 与 MCAP/WebSocket 可视化入口。

通过 ``pts_vis_image.PTSImageRenderer`` 将 9 柱三维位移与力栅格化为 JPEG 触觉图像，
以降采样帧率（默认 30 Hz）发布到 Foxglove WebSocket 服务或写入 MCAP 文件，避免 500 Hz
原始采样率下每帧绘图造成 CPU 与录包体积膨胀。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Annotated

import foxglove
import serial
import typer
from foxglove.channels import CompressedImageChannel
from foxglove.messages import CompressedImage, Timestamp

from pts_protocol import PTSProtocolReader
from pts_vis_core import (
    PTSFrame,
    PTSVisualizationConfig,
    frames_from_packet,
    mock_frame,
)
from pts_vis_image import DEFAULT_IMAGE_SIZE_PX, PTSImageRenderer, encode_jpeg

DEFAULT_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200
DEFAULT_TIMEOUT_SEC = 1.0
DEFAULT_WS_HOST = "127.0.0.1"
DEFAULT_WS_PORT = 8765
DEFAULT_IMAGE_HZ = 30.0
DEFAULT_MOCK_HZ = 100.0
DEFAULT_MOCK_FRAMES = 120
DEFAULT_SENSOR_NAME = "sen0"
DEFAULT_DUAL_NAMES = ("sen0", "sen1")
US_TO_NS = 1_000
US_PER_SEC = 1_000_000

app = typer.Typer(no_args_is_help=True)


class FoxglovePTSLogger:
    """将 PTS 触觉帧以 JPEG 压缩图像 + JSON 状态通道写入 Foxglove WebSocket / MCAP。

    Args:
        config: PTS 2D 可视化配置。
        image_hz: 触觉图像最大渲染与发布频率，单位 Hz（防止 500 Hz 全速渲染拖慢采集）。
        image_size_px: 触觉图像边长，单位像素。
        serve_ws: 是否启动本地 Foxglove WebSocket 实时服务。
        ws_host: WebSocket 监听地址。
        ws_port: WebSocket 监听端口。
        mcap_path: 可选 MCAP 文件保存路径。
    """

    def __init__(
        self,
        *,
        config: PTSVisualizationConfig | None = None,
        image_hz: float = DEFAULT_IMAGE_HZ,
        image_size_px: int = DEFAULT_IMAGE_SIZE_PX,
        serve_ws: bool = False,
        ws_host: str = DEFAULT_WS_HOST,
        ws_port: int = DEFAULT_WS_PORT,
        mcap_path: Path | None = None,
    ) -> None:
        if image_hz <= 0:
            raise ValueError("image_hz 必须为正数")
        self.config = config or PTSVisualizationConfig()
        self.image_period_us = int(round(US_PER_SEC / image_hz))
        self.image_size_px = image_size_px
        # 每个实例使用独立 Context，避免多实例或单元测试之间通道冲突
        self._ctx = foxglove.Context()
        self._server = None
        self._mcap = None
        if mcap_path is not None:
            mcap_path.parent.mkdir(parents=True, exist_ok=True)
            self._mcap = foxglove.open_mcap(mcap_path, allow_overwrite=True, context=self._ctx)
        if serve_ws:
            self._server = foxglove.start_server(host=ws_host, port=ws_port, context=self._ctx)

        self._renderers: dict[str, PTSImageRenderer] = {}
        self._image_channels: dict[str, CompressedImageChannel] = {}
        self._state_channels: dict[str, foxglove.Channel] = {}
        self._last_image_us: dict[str, int] = {}
        self.rendered_image_count = 0

    def log_tactile_frame(
        self,
        frame: PTSFrame,
        sensor_name: str = DEFAULT_SENSOR_NAME,
    ) -> bool:
        """记录单帧全局力状态，并按降采样周期渲染与发布 JPEG 触觉图像。

        Args:
            frame: 单传感器数据帧（位移 mm，力 N，力矩 N·mm，sensor frame）。
            sensor_name: 传感器标识，如 ``sen0`` 或 ``left``。

        Returns:
            本帧是否实际触发了图像渲染与发布。
        """
        topic_root = f"/tactile/{sensor_name}"
        log_time_ns = max(0, int(frame.timestamp_us * US_TO_NS))

        state_ch = self._state_channels.get(sensor_name)
        if state_ch is None:
            state_ch = foxglove.Channel(
                f"{topic_root}/state", message_encoding="json", context=self._ctx
            )
            self._state_channels[sensor_name] = state_ch

        fx, fy, fz = (float(v) for v in frame.global_force)
        tx, ty, tz = (float(v) for v in frame.global_torque)
        state_ch.log(
            {
                "timestamp_us": int(frame.timestamp_us),
                "fx": fx,
                "fy": fy,
                "fz": fz,
                "tx": tx,
                "ty": ty,
                "tz": tz,
            },
            log_time=log_time_ns,
        )

        if not self.config.enabled:
            return False

        last_us = self._last_image_us.get(sensor_name)
        if last_us is not None and (frame.timestamp_us - last_us) < self.image_period_us:
            return False

        renderer = self._renderers.get(sensor_name)
        if renderer is None:
            renderer = PTSImageRenderer(
                self.config, size_px=self.image_size_px, title=sensor_name.upper()
            )
            self._renderers[sensor_name] = renderer

        img_ch = self._image_channels.get(sensor_name)
        if img_ch is None:
            img_ch = CompressedImageChannel(f"{topic_root}/image", context=self._ctx)
            self._image_channels[sensor_name] = img_ch

        rgb = renderer.render(frame)
        jpeg_bytes = encode_jpeg(rgb)
        sec = max(0, int(frame.timestamp_us // US_PER_SEC))
        nsec = max(0, int((frame.timestamp_us % US_PER_SEC) * US_TO_NS))
        img_ch.log(
            CompressedImage(
                timestamp=Timestamp(sec=sec, nsec=nsec),
                frame_id=sensor_name,
                data=jpeg_bytes,
                format="jpeg",
            ),
            log_time=log_time_ns,
        )
        self._last_image_us[sensor_name] = frame.timestamp_us
        self.rendered_image_count += 1
        return True

    def close(self) -> None:
        """关闭 WebSocket 服务与 MCAP 写入器，确保落盘完整。

        Args:
            None。

        Returns:
            None。

        Raises:
            None。清理失败降级为警告，避免覆盖主流程的退出码。
        """
        # 与 RerunLogger.close 同理：finally 阶段单个资源释放失败只降级为警告，
        # 不中断其余资源释放，也不覆盖 Ctrl+C 的 130 退出码
        if self._server is not None:
            try:
                self._server.stop()
            except Exception as exc:
                typer.secho(f"警告: Foxglove WebSocket 服务关闭失败: {exc}", err=True)
            self._server = None
        if self._mcap is not None:
            try:
                self._mcap.close()
            except Exception as exc:
                typer.secho(f"警告: MCAP 文件关闭失败: {exc}", err=True)
            self._mcap = None


def build_foxglove_layout(
    sensor_names: tuple[str, ...] = (DEFAULT_SENSOR_NAME,),
) -> dict[str, object]:
    """生成可直接导入 Foxglove Studio 的布局字典（含触觉图像面板与三轴力曲线面板）。

    Args:
        sensor_names: 传感器名称列表。

    Returns:
        符合 Foxglove Layout JSON 规范的字典。
    """
    config_by_id: dict[str, object] = {}
    panels: list[str] = []
    for name in sensor_names:
        img_id = f"Image!{name}"
        plot_id = f"Plot!{name}"
        config_by_id[img_id] = {
            "cameraState": {},
            "followMode": "follow-pose",
            "imageMode": {"imageTopic": f"/tactile/{name}/image"},
            "foxglovePanelTitle": f"{name.upper()} · PTS 2D Tactile Image",
        }
        config_by_id[plot_id] = {
            "foxglovePanelTitle": f"{name.upper()} · Global Force (N)",
            "paths": [
                {"value": f"/tactile/{name}/state.fx", "enabled": True, "label": "Fx"},
                {"value": f"/tactile/{name}/state.fy", "enabled": True, "label": "Fy"},
                {"value": f"/tactile/{name}/state.fz", "enabled": True, "label": "Fz"},
            ],
            "showLegend": True,
            "xAxisVal": "timestamp",
        }
        panels.extend([img_id, plot_id])

    layout: object = (
        panels[0]
        if len(panels) == 1
        else {
            "direction": "row",
            "first": panels[0],
            "second": panels[1]
            if len(panels) == 2
            else {
                "direction": "row",
                "first": panels[1],
                "second": {"direction": "row", "first": panels[2], "second": panels[3]},
            },
        }
    )
    return {
        "configById": config_by_id,
        "globalVariables": {},
        "userNodes": {},
        "playbackConfig": {"speed": 1.0},
        "layout": layout,
    }


def run_foxglove_visualizer(
    *,
    port: str = DEFAULT_PORT,
    baud_rate: int = DEFAULT_BAUD_RATE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    samples: int = DEFAULT_MOCK_FRAMES,
    dual: bool = False,
    mock: bool = False,
    serve_ws: bool = True,
    ws_host: str = DEFAULT_WS_HOST,
    ws_port: int = DEFAULT_WS_PORT,
    save_mcap: Path | None = None,
    export_layout: Path | None = None,
    image_hz: float = DEFAULT_IMAGE_HZ,
    config: PTSVisualizationConfig | None = None,
) -> int:
    """运行 Foxglove 触觉图像发布与 MCAP 记录主循环。

    Args:
        port: 串口设备路径。
        baud_rate: 串口波特率，单位 baud。
        timeout_sec: 单次串口读取超时，单位 s。
        samples: 采集帧数（<=0 表示持续运行）。
        dual: 是否启用双路传感器模式。
        mock: 是否使用模拟数据而不访问真实串口。
        serve_ws: 是否开启 Foxglove WebSocket 服务。
        ws_host: WebSocket 监听地址。
        ws_port: WebSocket 监听端口。
        save_mcap: 可选 MCAP 保存路径。
        export_layout: 可选导出 Foxglove 布局 JSON 的文件路径。
        image_hz: 触觉图像降采样发布频率，单位 Hz。
        config: 可选自定义 PTSVisualizationConfig。

    Returns:
        进程退出码，0 表示正常结束。
    """
    sensor_names = DEFAULT_DUAL_NAMES if dual else (DEFAULT_SENSOR_NAME,)
    if export_layout is not None:
        export_layout.parent.mkdir(parents=True, exist_ok=True)
        export_layout.write_text(
            json.dumps(build_foxglove_layout(sensor_names), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        typer.echo(f"已导出 Foxglove 布局文件: {export_layout}")

    if not mock and not os.path.exists(port):
        typer.secho(f"错误: 串口设备不存在: {port}", err=True)
        return 1

    logger = FoxglovePTSLogger(
        config=config,
        image_hz=image_hz,
        serve_ws=serve_ws,
        ws_host=ws_host,
        ws_port=ws_port,
        mcap_path=save_mcap,
    )
    try:
        if serve_ws:
            typer.echo(f"Foxglove WebSocket 已启动: ws://{ws_host}:{ws_port}")
        if mock:
            dt = 1.0 / DEFAULT_MOCK_HZ
            count = 0
            while samples <= 0 or count < samples:
                t_s = count * dt
                for idx, name in enumerate(sensor_names):
                    logger.log_tactile_frame(mock_frame(t_s, phase=idx * 1.2), sensor_name=name)
                count += 1
                if serve_ws:
                    time.sleep(dt)
            typer.echo(
                f"Foxglove mock 完成: 原始帧 {count}，渲染图像 {logger.rendered_image_count} 帧"
            )
            return 0

        with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout_sec) as ser:
            reader = PTSProtocolReader(ser)
            typer.echo(f"已连接 {port} ({baud_rate} baud)，以 {image_hz} Hz 渲染触觉图像...")
            count = 0
            while samples <= 0 or count < samples:
                packet = reader.read_packet()
                frames = frames_from_packet(packet)
                for frame, name in zip(frames, sensor_names):
                    logger.log_tactile_frame(frame, sensor_name=name)
                count += 1
    except PermissionError:
        # 串口权限不足时只能由用户调整 dialout 组，脚本禁止调用 sudo
        typer.secho(f"错误: 没有权限访问 {port}，请将当前用户加入 dialout 组", err=True)
        return 1
    except (OSError, ValueError, TimeoutError) as exc:
        typer.secho(f"错误: {exc}", err=True)
        return 1
    except KeyboardInterrupt:
        # 确保串口和 MCAP 写入器在中断时正常刷盘释放
        typer.secho("收到中断信号，已安全释放串口与 Foxglove 资源", err=True)
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
    dual: Annotated[bool, typer.Option("--dual", help="双路传感器模式")] = False,
    mock: Annotated[bool, typer.Option("--mock", help="使用模拟数据，不依赖硬件")] = False,
    no_ws: Annotated[
        bool, typer.Option("--no-ws", help="不启动 WebSocket 服务，仅录制 MCAP")
    ] = False,
    ws_host: Annotated[
        str, typer.Option("--ws-host", help="Foxglove WebSocket 监听地址")
    ] = DEFAULT_WS_HOST,
    ws_port: Annotated[
        int, typer.Option("--ws-port", help="Foxglove WebSocket 端口")
    ] = DEFAULT_WS_PORT,
    save_mcap: Annotated[
        Path | None, typer.Option("--save-mcap", help="保存 MCAP 文件路径")
    ] = None,
    export_layout: Annotated[
        Path | None, typer.Option("--export-layout", help="导出 Foxglove 布局 JSON 路径")
    ] = None,
    image_hz: Annotated[
        float, typer.Option("--image-hz", help="触觉图像渲染频率 (Hz)")
    ] = DEFAULT_IMAGE_HZ,
    contact_threshold: Annotated[
        float, typer.Option("--contact-threshold", help="接触力阈值 (N)")
    ] = 0.2,
) -> None:
    """启动 Contactile PTS 的 Foxglove 触觉图像发布或 MCAP 录制。"""
    cfg = PTSVisualizationConfig(contact_threshold_n=contact_threshold)
    code = run_foxglove_visualizer(
        port=port,
        baud_rate=baud_rate,
        samples=samples,
        dual=dual,
        mock=mock,
        serve_ws=not no_ws,
        ws_host=ws_host,
        ws_port=ws_port,
        save_mcap=save_mcap,
        export_layout=export_layout,
        image_hz=image_hz,
        config=cfg,
    )
    raise typer.Exit(code)


if __name__ == "__main__":
    try:
        app()
    except SystemExit as exc:
        sys.exit(exc.code)
