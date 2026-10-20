#!/usr/bin/env python3
"""PTS 2D 可视化共享几何核心、Rerun 后端与 Foxglove 触觉图像后端的离线单元测试。"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pts_protocol import ParsedPacket
from pts_vis import MockPtsSession
from pts_vis_core import (
    COLOR_NO_CONTACT,
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
from pts_vis_foxglove import (
    FoxglovePTSLogger,
    build_foxglove_layout,
)
from pts_vis_foxglove import (
    app as foxglove_app,
)
from pts_vis_image import PTSImageRenderer, encode_jpeg
from pts_vis_rerun import RerunLogger
from pts_vis_rerun import app as rerun_app


class _FakeRecording:
    """拦截 RerunLogger 的记录调用，避免单元测试启动真实 Viewer。"""

    def __init__(self) -> None:
        self.logs: list[tuple[str, object, bool]] = []
        self.times: list[tuple[str, dict[str, object]]] = []
        self.blueprints: list[object] = []

    def send_blueprint(self, blueprint: object) -> None:
        self.blueprints.append(blueprint)

    def set_time(self, timeline: str, **kwargs: object) -> None:
        self.times.append((timeline, kwargs))

    def log(self, entity_path: str, entity: object, *, static: bool = False) -> None:
        self.logs.append((entity_path, entity, static))

    def flush(self) -> None:
        pass

    def disconnect(self) -> None:
        pass


def test_config_validation_rejects_invalid_parameters() -> None:
    """非法半径、间距或力满量程应在构造时立即报错。"""
    with pytest.raises(ValueError, match="必须为正"):
        PTSVisualizationConfig(pillar_spacing_mm=0.0)
    with pytest.raises(ValueError, match="tip_radius"):
        PTSVisualizationConfig(tip_radius_min_mm=3.0, tip_radius_max_mm=1.0)
    with pytest.raises(ValueError, match="force_full_scale_n"):
        PTSVisualizationConfig(force_full_scale_n=-1.0)


def test_pillar_geometry_radius_and_contact_color_mapping() -> None:
    """顶圆半径应随 Fz 单调递增，接触前后颜色应按阈值切换。"""
    cfg = PTSVisualizationConfig(
        contact_threshold_n=0.2,
        tip_radius_min_mm=0.8,
        tip_radius_max_mm=2.8,
        force_full_scale_n=5.0,
        displacement_gain=2.0,
    )
    disps = np.zeros((PTS_N_PILLARS, 3))
    disps[0, :2] = [0.5, -0.25]
    forces = np.zeros((PTS_N_PILLARS, 3))
    forces[0, 2] = 0.1  # 未达接触阈值 0.2 N
    forces[4, 2] = 2.5  # 达半满量程且接触
    forces[8, 2] = 10.0  # 超过满量程，应钳位到最大半径

    frame = PTSFrame(
        timestamp_us=1000,
        displacements=disps,
        forces=forces,
        global_force=forces.sum(axis=0),
        global_torque=np.zeros(3),
    )
    geom = compute_pillar_geometry(frame, cfg)

    base = pillar_base_centers(cfg.pillar_spacing_mm)
    np.testing.assert_allclose(geom.tip_centers[0], base[0] + np.array([1.0, -0.5]))
    assert not geom.in_contact[0]
    assert geom.in_contact[4]
    assert geom.in_contact[8]
    assert tuple(geom.colors[0]) == COLOR_NO_CONTACT
    assert tuple(geom.colors[4]) != COLOR_NO_CONTACT
    assert geom.tip_radii[0] < geom.tip_radii[4] < geom.tip_radii[8]
    assert pytest.approx(geom.tip_radii[4]) == 1.8
    assert pytest.approx(geom.tip_radii[8]) == cfg.tip_radius_max_mm


def test_outline_and_crosshair_geometry_shapes() -> None:
    """外框应为闭合 5 点折线，十字准星应为每柱 2 条线段。"""
    cfg = PTSVisualizationConfig()
    outline = active_area_outline(cfg)
    assert outline.shape == (5, 2)
    np.testing.assert_allclose(outline[0], outline[-1])

    segs = crosshair_segments(pillar_base_centers(), cfg.crosshair_half_mm)
    assert segs.shape == (2 * PTS_N_PILLARS, 2, 2)


def test_flip_x_coordinate_conventions() -> None:
    """默认 flip_x=True 应满足右手系 (+x 朝左、+y 朝上、+z 向里) 像素与点阵映射。"""
    s = 7.0
    base_rh = pillar_base_centers(spacing_mm=s, flip_x=True)
    # P0 为左上角：+x 朝左故 x=+s；+y 朝上故 y=+s
    np.testing.assert_allclose(base_rh[0], (s, s))
    np.testing.assert_allclose(base_rh[2], (-s, s))
    np.testing.assert_allclose(base_rh[8], (-s, -s))

    base_lh = pillar_base_centers(spacing_mm=s, flip_x=False)
    np.testing.assert_allclose(base_lh[0], (-s, s))
    np.testing.assert_allclose(base_lh[2], (s, s))

    renderer_rh = PTSImageRenderer(PTSVisualizationConfig(flip_x=True))
    px_p0 = renderer_rh.to_px(base_rh[0])
    px_p2 = renderer_rh.to_px(base_rh[2])
    px_p6 = renderer_rh.to_px(base_rh[6])
    # 像素坐标中，P0 应严格在 P2 左侧 (X 像素值更小)，P0 应在 P6 上方 (Y 像素值更小)
    assert px_p0[0] < px_p2[0]
    assert px_p0[1] < px_p6[1]


def test_frames_from_packet_converts_dual_sensors() -> None:
    """协议包解析出的双传感器数据应正确转为两个 PTSFrame。"""
    pkt = ParsedPacket(
        packet_counter=1,
        timestamp_us=5000,
        pillar_forces=[np.zeros((9, 3)), np.ones((9, 3))],
        pillar_displacements=[np.zeros((9, 3)), np.zeros((9, 3))],
        global_forces=[np.zeros(3), np.ones(3)],
        global_torques=[np.zeros(3), np.zeros(3)],
    )
    frames = frames_from_packet(pkt)
    assert len(frames) == 2
    assert pytest.approx(frames[1].global_force[2]) == 1.0

    # 第 1 路 pillar 数异常时应占位 None 并告警，而不是把第 2 路数据前移错配
    pkt_bad = ParsedPacket(
        packet_counter=2,
        timestamp_us=6000,
        pillar_forces=[np.zeros((8, 3)), np.ones((9, 3))],
        pillar_displacements=[np.zeros((8, 3)), np.zeros((9, 3))],
        global_forces=[np.zeros(3), np.ones(3)],
        global_torques=[np.zeros(3), np.zeros(3)],
    )
    with pytest.warns(RuntimeWarning, match="pillar 数异常"):
        frames_bad = frames_from_packet(pkt_bad)
    assert frames_bad[0] is None
    assert frames_bad[1] is not None
    assert pytest.approx(frames_bad[1].global_force[2]) == 1.0


def test_rerun_logger_entity_path_isolation_and_blueprint() -> None:
    """RerunLogger 应支持单/双路 Blueprint，并按 entity_path 隔离左右传感器图层。"""
    fake_single = _FakeRecording()
    logger_single = RerunLogger(
        sensor_paths=("tactile/sen0",),
        recording=fake_single,
    )
    assert len(fake_single.blueprints) == 1
    logger_single.log_tactile_frame(mock_frame(0.1), entity_path="tactile/sen0")
    logged_paths = {path for path, _, _ in fake_single.logs}
    assert "tactile/sen0/pts/active_area_outline" in logged_paths
    assert "tactile/sen0/pts/base_circles" in logged_paths
    assert "tactile/sen0/pts/tip_circles" in logged_paths
    assert "tactile/sen0/pts/crosshairs" in logged_paths
    assert "tactile/sen0/pts/labels" in logged_paths
    assert "tactile/sen0/pts/frame_axes" in logged_paths
    assert "tactile/sen0/pressure" in logged_paths
    assert "tactile/sen0/force/fz" in logged_paths

    fake_dual = _FakeRecording()
    logger_dual = RerunLogger(
        sensor_paths=("tactile/left", "tactile/right"),
        recording=fake_dual,
    )
    logger_dual.log_tactile_frame(mock_frame(0.1), entity_path="tactile/left")
    logger_dual.log_tactile_frame(mock_frame(0.1, phase=1.0), entity_path="tactile/right")
    dual_paths = {path for path, _, _ in fake_dual.logs}
    assert "tactile/left/pts/tip_circles" in dual_paths
    assert "tactile/right/pts/tip_circles" in dual_paths


def test_rerun_logger_respects_disabled_pts_layer() -> None:
    """关闭 PTSVisualizationConfig.enabled 时不应记录 2D 几何实体，仅保留标量与张量。"""
    fake = _FakeRecording()
    logger = RerunLogger(
        config=PTSVisualizationConfig(enabled=False),
        recording=fake,
    )
    logger.log_tactile_frame(mock_frame(0.0), entity_path="tactile/sen0")
    paths = {path for path, _, _ in fake.logs}
    assert "tactile/sen0/force/fz" in paths
    assert "tactile/sen0/pressure" in paths
    assert not any("/pts/" in p for p in paths)


def test_image_renderer_and_foxglove_mcap_throttling(tmp_path: pathlib.Path) -> None:
    """图像渲染器应输出合法 JPEG，FoxglovePTSLogger 应按频率降采样渲染并生成非空 MCAP。"""
    renderer = PTSImageRenderer(size_px=240, title="SEN0")
    rgb = renderer.render(mock_frame(0.2))
    assert rgb.shape == (240, 240, 3)
    assert rgb.dtype == np.uint8
    jpeg = encode_jpeg(rgb)
    assert jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9"

    mcap_file = tmp_path / "pts.mcap"
    fg_logger = FoxglovePTSLogger(image_hz=25.0, serve_ws=False, mcap_path=mcap_file)
    # 以 100 Hz (步长 10_000 us) 输入 10 帧，25 Hz (周期 40_000 us) 应只渲染 3 帧 (t=0, 40ms, 80ms)
    for i in range(10):
        f = mock_frame(i * 0.01)
        fg_logger.log_tactile_frame(f, sensor_name="sen0")
    fg_logger.close()
    assert fg_logger.rendered_image_count == 3
    assert mcap_file.is_file() and mcap_file.stat().st_size > 0

    layout = build_foxglove_layout(("sen0", "sen1"))
    assert "Image!sen0" in layout["configById"]
    assert "Plot!sen1" in layout["configById"]


def _collect_layout_panels(node: object, acc: set[str]) -> None:
    """递归收集布局树中实际挂载的面板 id。"""
    if isinstance(node, str):
        acc.add(node)
    elif isinstance(node, dict):
        _collect_layout_panels(node["first"], acc)
        _collect_layout_panels(node["second"], acc)


def test_foxglove_layout_covers_all_panels_for_any_sensor_count() -> None:
    """任意数量传感器的面板都应挂进布局树，双路应为均衡的图像行 + 曲线行。"""
    for names in (("sen0",), ("sen0", "sen1"), ("a", "b", "c"), ("a", "b", "c", "d")):
        layout = build_foxglove_layout(names)
        used: set[str] = set()
        _collect_layout_panels(layout["layout"], used)
        assert used == set(layout["configById"].keys()), names

    dual = build_foxglove_layout(("sen0", "sen1"))
    assert dual["layout"] == {
        "direction": "column",
        "first": {"direction": "row", "first": "Image!sen0", "second": "Image!sen1"},
        "second": {"direction": "row", "first": "Plot!sen0", "second": "Plot!sen1"},
    }
    single = build_foxglove_layout(("sen0",))
    assert single["layout"] == {
        "direction": "row",
        "first": "Image!sen0",
        "second": "Plot!sen0",
    }


def test_cli_mock_runs_offline(tmp_path: pathlib.Path) -> None:
    """两个 CLI 入口在 --mock 模式下均应离线完成且不访问硬件。"""
    runner = CliRunner()
    res_rerun = runner.invoke(rerun_app, ["--mock", "--no-spawn", "--samples", "4", "--dual"])
    assert res_rerun.exit_code == 0, res_rerun.output

    mcap_out = tmp_path / "cli.mcap"
    layout_out = tmp_path / "layout.json"
    res_fg = runner.invoke(
        foxglove_app,
        [
            "--mock",
            "--no-ws",
            "--samples",
            "6",
            "--save-mcap",
            str(mcap_out),
            "--export-layout",
            str(layout_out),
        ],
    )
    assert res_fg.exit_code == 0, res_fg.output
    assert mcap_out.is_file()
    assert layout_out.is_file()


def test_mock_pts_session_generates_independent_pillars() -> None:
    """MockPtsSession 应产出时间戳递增、9 柱齐全且幅度在显示范围内的模拟帧。"""
    session = MockPtsSession(rate_hz=100, sensor_index=0)
    first = session.next_sample()
    second = session.next_sample()

    assert len(first.forces) == PTS_N_PILLARS
    assert len(first.displacements) == PTS_N_PILLARS
    assert second.timestamp_us > first.timestamp_us == 0
    assert second.forces != first.forces
    # 幅度需落在曲线视图默认量程内（力 ±10 N，位移 ±1 mm），否则 mock 演示会被截断
    assert all(abs(component) < 10.0 for force in first.forces for component in force)
    assert all(abs(component) < 1.0 for disp in first.displacements for component in disp)


class _SeveredRecording(_FakeRecording):
    """模拟查看器先于脚本关闭：flush 抛 RuntimeError，disconnect 仍应被调用。"""

    def __init__(self) -> None:
        super().__init__()
        self.disconnect_called = False

    def flush(self) -> None:
        raise RuntimeError("gRPC connection severed")

    def disconnect(self) -> None:
        self.disconnect_called = True


def test_rerun_logger_close_tolerates_severed_connection() -> None:
    """查看器连接断开时 close() 不应抛出，也不能跳过后续 disconnect 清理。"""
    fake = _SeveredRecording()
    logger = RerunLogger(recording=fake)
    logger.log_tactile_frame(mock_frame(0.0), entity_path="tactile/sen0")

    logger.close()

    assert fake.disconnect_called
