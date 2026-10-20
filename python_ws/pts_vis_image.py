#!/usr/bin/env python3
"""把 PTS 帧栅格化为“触觉图像”，供 Foxglove Image 面板（或任何图像管线）显示。

几何全部来自 ``pts_vis_core``，本模块只负责 mm → 像素与 OpenCV 绘制，
因此与 Rerun 图层保持同一套半径 / 颜色 / 接触判定。
"""

from __future__ import annotations

import cv2
import numpy as np

from pts_vis_core import (
    COLOR_AXIS_X,
    COLOR_AXIS_Y,
    COLOR_BASE,
    COLOR_CROSSHAIR,
    COLOR_LABEL,
    COLOR_OUTLINE,
    PTSFrame,
    PTSVisualizationConfig,
    active_area_outline,
    compute_pillar_geometry,
    crosshair_segments,
)

DEFAULT_IMAGE_SIZE_PX = 480
BACKGROUND_RGB = (30, 32, 38)
JPEG_QUALITY = 85  # 触觉图为大面积纯色，85 已无可见伪影且单帧约十几 KB


class PTSImageRenderer:
    """PTS 单传感器顶视图渲染器，输出 RGB uint8 图像。

    Args:
        config: 可视化配置。
        size_px: 正方形图像边长，单位像素。
        title: 左上角标题，例如 ``SEN0``。
    """

    def __init__(
        self,
        config: PTSVisualizationConfig | None = None,
        size_px: int = DEFAULT_IMAGE_SIZE_PX,
        title: str = "",
    ) -> None:
        if size_px < 64:
            raise ValueError("size_px 至少为 64")
        self.config = config or PTSVisualizationConfig()
        self.size_px = size_px
        self.title = title
        outline_half = float(np.max(np.abs(active_area_outline(self.config))))
        # 外框两侧各留 15% 画布给坐标轴和文字
        self.px_per_mm = size_px * 0.70 / (2.0 * outline_half)
        self._static = self._render_static()

    def to_px(self, xy_mm: np.ndarray) -> np.ndarray:
        """sensor frame (mm, +y 向上) → 图像像素 (+y 向下)。

        当 config.flip_x=True 时，+x 朝左，满足 +z 垂直屏幕向里时的空间右手系。

        Args:
            xy_mm: 坐标，单位 mm，shape=(..., 2)。

        Returns:
            像素坐标，shape 同输入，dtype=int32。
        """
        xy = np.asarray(xy_mm, dtype=np.float64)
        c = self.size_px / 2.0
        px = np.empty_like(xy)
        if self.config.flip_x:
            px[..., 0] = c - xy[..., 0] * self.px_per_mm
        else:
            px[..., 0] = c + xy[..., 0] * self.px_per_mm
        px[..., 1] = c - xy[..., 1] * self.px_per_mm
        return np.rint(px).astype(np.int32)

    def _render_static(self) -> np.ndarray:
        """预渲染不随帧变化的图层，每帧只拷贝一次，降低 CPU 占用。"""
        cfg = self.config
        img = np.full((self.size_px, self.size_px, 3), BACKGROUND_RGB, dtype=np.uint8)
        outline = self.to_px(active_area_outline(cfg))
        cv2.polylines(img, [outline.reshape(-1, 1, 2)], True, COLOR_OUTLINE, 2, cv2.LINE_AA)

        base_r = max(1, int(round(cfg.base_radius_mm * self.px_per_mm)))
        from pts_vis_core import pillar_base_centers  # 局部导入避免顶部列表过长

        for i, center in enumerate(
            self.to_px(pillar_base_centers(cfg.pillar_spacing_mm, flip_x=cfg.flip_x))
        ):
            cv2.circle(img, tuple(int(v) for v in center), base_r, COLOR_BASE, 1, cv2.LINE_AA)
            if cfg.show_labels:
                org = (int(center[0]) - base_r, int(center[1]) - base_r - 4)
                cv2.putText(
                    img, f"P{i}", org, cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_LABEL, 1, cv2.LINE_AA
                )

        if cfg.show_frame:
            length = int(0.10 * self.size_px)
            font = cv2.FONT_HERSHEY_SIMPLEX
            if cfg.flip_x:
                # 放在右下角，+X 朝左，+Y 朝上，满足右手直角坐标系
                o = (int(0.86 * self.size_px), int(0.88 * self.size_px))
                x_end = (o[0] - length, o[1])  # 箭头向左
                y_end = (o[0], o[1] - length)  # 箭头向上
                cv2.arrowedLine(img, o, x_end, COLOR_AXIS_X, 2, cv2.LINE_AA, tipLength=0.25)
                cv2.arrowedLine(img, o, y_end, COLOR_AXIS_Y, 2, cv2.LINE_AA, tipLength=0.25)
                cv2.putText(img, "+x", (x_end[0] - 22, x_end[1] + 5), font, 0.45, COLOR_AXIS_X, 1)
                cv2.putText(img, "+y", (y_end[0] - 8, y_end[1] - 6), font, 0.45, COLOR_AXIS_Y, 1)
                # 绘制 ⊗ 符号代表 +Z 垂直屏幕向里
                cv2.circle(img, o, 4, COLOR_LABEL, 1, cv2.LINE_AA)
                cv2.line(
                    img, (o[0] - 3, o[1] - 3), (o[0] + 3, o[1] + 3), COLOR_LABEL, 1, cv2.LINE_AA
                )
                cv2.line(
                    img, (o[0] - 3, o[1] + 3), (o[0] + 3, o[1] - 3), COLOR_LABEL, 1, cv2.LINE_AA
                )
                cv2.putText(img, "+z (in)", (o[0] - 20, o[1] + 16), font, 0.35, COLOR_LABEL, 1)
            else:
                corner = active_area_outline(cfg)[0]  # 左下角
                origin = self.to_px(corner + np.array([-1.0, -1.0]))
                o = (int(origin[0]), int(origin[1]))
                x_end, y_end = (o[0] + length, o[1]), (o[0], o[1] - length)
                cv2.arrowedLine(img, o, x_end, COLOR_AXIS_X, 2, cv2.LINE_AA, tipLength=0.2)
                cv2.arrowedLine(img, o, y_end, COLOR_AXIS_Y, 2, cv2.LINE_AA, tipLength=0.2)
                cv2.putText(img, "+x", (x_end[0] + 4, x_end[1] + 5), font, 0.45, COLOR_AXIS_X, 1)
                cv2.putText(img, "+y", (y_end[0] - 8, y_end[1] - 6), font, 0.45, COLOR_AXIS_Y, 1)

        if self.title:
            cv2.putText(
                img,
                self.title,
                (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                COLOR_LABEL,
                1,
                cv2.LINE_AA,
            )
        return img

    def render(self, frame: PTSFrame) -> np.ndarray:
        """渲染一帧。

        Args:
            frame: 单传感器帧。

        Returns:
            RGB 图像，shape=(size_px, size_px, 3)，dtype=uint8。
        """
        cfg = self.config
        img = self._static.copy()
        geom = compute_pillar_geometry(frame, cfg)
        tips_px = self.to_px(geom.tip_centers)
        for center, radius_mm, color in zip(tips_px, geom.tip_radii, geom.colors):
            r = max(1, int(round(radius_mm * self.px_per_mm)))
            cv2.circle(
                img,
                (int(center[0]), int(center[1])),
                r,
                tuple(int(c) for c in color),
                -1,
                cv2.LINE_AA,
            )
        if cfg.show_crosshair:
            for seg in self.to_px(crosshair_segments(geom.tip_centers, cfg.crosshair_half_mm)):
                p0, p1 = (int(seg[0][0]), int(seg[0][1])), (int(seg[1][0]), int(seg[1][1]))
                cv2.line(img, p0, p1, COLOR_CROSSHAIR, 1, cv2.LINE_AA)

        fx, fy, fz = frame.global_force
        text = f"F = [{fx:+.2f}, {fy:+.2f}, {fz:+.2f}] N"
        cv2.putText(
            img,
            text,
            (8, self.size_px - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            COLOR_LABEL,
            1,
            cv2.LINE_AA,
        )
        return img


def encode_jpeg(rgb: np.ndarray, quality: int = JPEG_QUALITY) -> bytes:
    """把 RGB 图像编码为 JPEG，用于 CompressedImage 以压低带宽与录包体积。

    Args:
        rgb: RGB 图像，shape=(H, W, 3)，dtype=uint8。
        quality: JPEG 质量，1~100。

    Returns:
        JPEG 字节串。

    Raises:
        RuntimeError: OpenCV 编码失败时抛出。
    """
    # OpenCV 编码按 BGR 解释通道，必须先转换，否则红蓝互换
    ok, buf = cv2.imencode(
        ".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, quality]
    )
    if not ok:
        raise RuntimeError("JPEG 编码失败")
    return buf.tobytes()
