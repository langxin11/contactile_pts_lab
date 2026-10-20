#!/usr/bin/env python3
"""PTS 2D 可视化的共享几何核心。

Rerun 矢量图层与 Foxglove 触觉图像共用同一套“物理量 → 视觉量”映射，
避免两个后端各自实现导致半径、颜色、接触判定不一致。帧数据模型
（``PTSFrame`` / ``frames_from_packet``）由共享串口库 papillarray-pts >= 0.3.0
提供，本模块只保留可视化几何，不依赖任何渲染库。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from papillarray_pts.frames import PTSFrame

# 以下几何参数来自 PTS_2.1_SPEC_JAN25 Table 3.1
PILLAR_SPACING_MM = 7.0  # 方形网格中心距
PILLAR_DIAMETER_MM = 6.0
# 单柱量程（同一份规格书）：X/Y ±1 mm，Z +2.5 mm
XY_DISPLACEMENT_RANGE_MM = 1.0
# 原厂 PTSVIS 默认接触阈值：任一轴 |F| >= 0.2 N 视为接触
DEFAULT_CONTACT_THRESHOLD_N = 0.2

# 颜色约定沿用 PTSVIS：未接触灰、接触白；坐标轴 X 黄 / Y 绿（与其曲线配色一致）
COLOR_NO_CONTACT = (110, 115, 125)
COLOR_CONTACT = (240, 240, 240)
COLOR_CROSSHAIR = (230, 60, 60)
COLOR_BASE = (75, 80, 90)
COLOR_OUTLINE = (95, 100, 110)
COLOR_AXIS_X = (230, 190, 40)
COLOR_AXIS_Y = (60, 200, 80)
COLOR_LABEL = (170, 170, 170)

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class PTSVisualizationConfig:
    """PTS 2D 可视化参数，所有长度单位为 mm（sensor frame 顶视图）。

    Attributes:
        enabled: 是否绘制 PTS 2D 图层；关闭后后端只记录时序/张量。
        contact_threshold_n: 接触阈值，单位 N，任一轴力绝对值超过即视为接触。
        pillar_spacing_mm: pillar 中心距。
        base_radius_mm: pillar 基底圆半径（未变形外轮廓）。
        tip_radius_min_mm: Fz=0 时顶圆半径。
        tip_radius_max_mm: Fz>=force_full_scale_n 时顶圆半径。
        force_full_scale_n: 半径与颜色饱和对应的法向力，单位 N。
        displacement_gain: X/Y 位移显示放大倍数；量程仅 ±1 mm，不放大几乎看不出移动。
        crosshair_half_mm: 十字线半长。
        show_labels: 是否显示 P0~P8 标签。
        show_crosshair: 是否显示位移十字线。
        show_frame: 是否显示 +x/+y 坐标轴。
        flip_x: 默认 True，使屏幕显示 +x 朝左、+y 朝上；在法向压缩 +z 朝向屏幕向里时满足右手直角坐标系。
    """

    enabled: bool = True
    contact_threshold_n: float = DEFAULT_CONTACT_THRESHOLD_N
    pillar_spacing_mm: float = PILLAR_SPACING_MM
    base_radius_mm: float = PILLAR_DIAMETER_MM / 2.0
    tip_radius_min_mm: float = 0.8
    tip_radius_max_mm: float = 2.8
    force_full_scale_n: float = 5.0
    displacement_gain: float = 2.0
    crosshair_half_mm: float = 0.9
    show_labels: bool = True
    show_crosshair: bool = True
    show_frame: bool = True
    flip_x: bool = True

    def __post_init__(self) -> None:
        """校验参数，避免后端绘制出负半径或除零。"""
        if self.pillar_spacing_mm <= 0 or self.base_radius_mm <= 0:
            raise ValueError("pillar_spacing_mm 与 base_radius_mm 必须为正")
        if not 0 < self.tip_radius_min_mm <= self.tip_radius_max_mm:
            raise ValueError("要求 0 < tip_radius_min_mm <= tip_radius_max_mm")
        if self.force_full_scale_n <= 0:
            raise ValueError("force_full_scale_n 必须为正")
        if self.contact_threshold_n < 0:
            raise ValueError("contact_threshold_n 不能为负")


@dataclass(frozen=True)
class PillarGeometry:
    """一帧的可视化几何，单位 mm，sensor frame（+x 右，+y 上）。

    Attributes:
        base_centers: 基底圆心，shape=(9, 2)。
        tip_centers: 顶圆心（基底 + 放大后的 X/Y 位移），shape=(9, 2)。
        tip_radii: 顶圆半径，shape=(9,)。
        in_contact: 接触标志，shape=(9,)。
        colors: 顶圆 RGB，shape=(9, 3)，dtype=uint8。
    """

    base_centers: np.ndarray
    tip_centers: np.ndarray
    tip_radii: np.ndarray
    in_contact: np.ndarray
    colors: np.ndarray


def pillar_base_centers(
    spacing_mm: float = PILLAR_SPACING_MM,
    flip_x: bool = True,
) -> np.ndarray:
    """返回 9 个 pillar 基底中心。

    P0~P8 在 sensor frame 下按行优先排列：
    - flip_x=True (默认): +x 朝左，+y 朝上，P0 位于 (+s, +s) 即屏幕左上角。
    - flip_x=False: +x 朝右，+y 朝上，P0 位于 (-s, +s)。

    Args:
        spacing_mm: pillar 中心距，单位 mm。
        flip_x: 是否使用 +x 朝左坐标系（保持 +z 朝向屏幕向里时的右手系）。

    Returns:
        基底中心坐标，单位 mm，shape=(9, 2)。
    """
    s = float(spacing_mm)
    xs = (s, 0.0, -s) if flip_x else (-s, 0.0, s)
    return np.array([(x, y) for y in (s, 0.0, -s) for x in xs], dtype=np.float64)


def active_area_outline(config: PTSVisualizationConfig) -> np.ndarray:
    """返回有效区域外框（闭合折线），恰好包住 3×3 pillar 基底圆。

    Args:
        config: 可视化配置。

    Returns:
        闭合矩形顶点，单位 mm，shape=(5, 2)。
    """
    half = config.pillar_spacing_mm + config.base_radius_mm + 0.5  # 留 0.5 mm 边距
    return np.array(
        [(-half, -half), (half, -half), (half, half), (-half, half), (-half, -half)],
        dtype=np.float64,
    )


def contact_mask(forces: np.ndarray, threshold_n: float) -> np.ndarray:
    """按 PTSVIS 规则判定接触：任一轴 |F| >= 阈值。

    Args:
        forces: pillar 力，单位 N，shape=(9, 3)。
        threshold_n: 接触阈值，单位 N。

    Returns:
        接触标志，shape=(9,)，dtype=bool。
    """
    return np.any(np.abs(forces) >= threshold_n, axis=1)


def force_to_color(fz: np.ndarray, in_contact: np.ndarray, full_scale_n: float) -> np.ndarray:
    """法向力 → 颜色：未接触灰；接触后由白渐变到橙红，越红压得越重。

    Args:
        fz: 法向力，单位 N，shape=(9,)。
        in_contact: 接触标志，shape=(9,)。
        full_scale_n: 颜色饱和对应的力，单位 N。

    Returns:
        RGB 颜色，shape=(9, 3)，dtype=uint8。
    """
    t = np.clip(np.asarray(fz, dtype=np.float64) / full_scale_n, 0.0, 1.0)[:, None]
    white = np.array(COLOR_CONTACT, dtype=np.float64)
    hot = np.array((240, 90, 40), dtype=np.float64)
    contact_rgb = white + (hot - white) * t
    grey = np.broadcast_to(np.array(COLOR_NO_CONTACT, dtype=np.float64), contact_rgb.shape)
    rgb = np.where(np.asarray(in_contact)[:, None], contact_rgb, grey)
    return np.rint(rgb).astype(np.uint8)


def compute_pillar_geometry(frame: PTSFrame, config: PTSVisualizationConfig) -> PillarGeometry:
    """把单帧物理量映射为可视化几何。

    Args:
        frame: 单传感器帧。
        config: 可视化配置。

    Returns:
        该帧的 pillar 几何。
    """
    base = pillar_base_centers(config.pillar_spacing_mm, flip_x=config.flip_x)
    tips = base + frame.displacements[:, :2] * config.displacement_gain
    # 只用压缩方向的 Fz；拉伸（负值）多为 bias 漂移，不应让圆变小于最小值
    fz = np.clip(frame.forces[:, 2], 0.0, None)
    ratio = np.clip(fz / config.force_full_scale_n, 0.0, 1.0)
    radii = config.tip_radius_min_mm + (config.tip_radius_max_mm - config.tip_radius_min_mm) * ratio
    in_contact = contact_mask(frame.forces, config.contact_threshold_n)
    colors = force_to_color(fz, in_contact, config.force_full_scale_n)
    return PillarGeometry(base, tips, radii, in_contact, colors)


def crosshair_segments(tip_centers: np.ndarray, half_mm: float) -> np.ndarray:
    """生成每个顶圆的十字线段。

    Args:
        tip_centers: 顶圆心，单位 mm，shape=(N, 2)。
        half_mm: 十字线半长，单位 mm。

    Returns:
        线段端点，shape=(2N, 2, 2)，依次为每个 pillar 的水平线、竖直线。
    """
    segments = []
    for x, y in np.asarray(tip_centers, dtype=np.float64):
        segments.append(((x - half_mm, y), (x + half_mm, y)))
        segments.append(((x, y - half_mm), (x, y + half_mm)))
    return np.asarray(segments, dtype=np.float64).reshape(-1, 2, 2)


def mock_frame(t_s: float, phase: float = 0.0, flip_x: bool = True) -> PTSFrame:
    """生成可复现的模拟帧：一个接触斑在阵列上画圈并周期性按压。

    Args:
        t_s: 时间，单位 s。
        phase: 相位偏移，单位 rad，用于让双路 mock 数据不完全相同。
        flip_x: 是否使用 +x 朝左坐标系。

    Returns:
        模拟的单传感器帧。
    """
    base = pillar_base_centers(flip_x=flip_x)
    center = 5.0 * np.array([np.cos(0.6 * t_s + phase), np.sin(0.6 * t_s + phase)])
    press = 0.5 * (1.0 - np.cos(1.5 * t_s + phase))  # 0~1 周期按压
    dist2 = np.sum((base - center) ** 2, axis=1)
    weight = np.exp(-dist2 / (2 * 5.0**2)) * press
    fz = 4.0 * weight  # N
    shear_dir = np.array([np.cos(0.4 * t_s), np.sin(0.4 * t_s)])
    fxy = 0.8 * weight[:, None] * shear_dir  # N
    forces = np.column_stack([fxy, fz])
    # 线性刚度近似：仅用于演示，真实刚度由传感器标定决定
    displacements = np.column_stack([fxy / 1.2, fz / 3.0])
    torque_z = float(np.sum(base[:, 0] * fxy[:, 1] - base[:, 1] * fxy[:, 0]))
    return PTSFrame(
        timestamp_us=int(t_s * 1e6),
        displacements=displacements,
        forces=forces,
        global_force=forces.sum(axis=0),
        global_torque=np.array([0.0, 0.0, torque_z]),
    )
