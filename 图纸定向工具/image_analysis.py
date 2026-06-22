#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像分析 - 渲染页面并分析像素亮度确定图签位置
"""
import io
import logging

import fitz
from PIL import Image

from .config import (
    ZOOM_FACTOR,
    QUADRANT_MARGIN,
    PIXEL_GAP_THRESHOLD,
    REL_GAP_THRESHOLD
)

logger = logging.getLogger(__name__)


def pixel_corner(page):
    """
    图像分析: 渲染页面，四角最暗的=图签所在
    
    原理：图签区域通常包含更多文字和线条，像素亮度较低（更暗）。
    通过比较四个角落区域的平均亮度，确定图签位置。
    
    Args:
        page: PyMuPDF页面对象
        
    Returns:
        最暗角落标识 ('TL', 'TR', 'BL', 'BR') 或 None（无法确定）
    """
    try:
        # 渲染页面为图像（低分辨率，够用且快）
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM_FACTOR, ZOOM_FACTOR))
        data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(data)).convert('L')
        iw, ih = img.size

        # 计算角落区域边界
        # 使用35%的边缘区域，避免中心内容干扰
        left = int(iw * QUADRANT_MARGIN)
        right = int(iw * (1 - QUADRANT_MARGIN))
        top = int(ih * QUADRANT_MARGIN)
        bottom = int(ih * (1 - QUADRANT_MARGIN))

        # 定义四个角落的裁剪区域
        corners = {
            'TL': (0, 0, left, top),
            'TR': (right, 0, iw, top),
            'BL': (0, bottom, left, ih),
            'BR': (right, bottom, iw, ih),
        }

        # 计算每个角落的平均亮度
        scores = {}
        for name, box in corners.items():
            crop = img.crop(box)
            px = list(crop.getdata())
            avg = sum(px) / len(px) if px else 255
            scores[name] = avg

        # 找到最暗的角落
        darkest = min(scores, key=scores.get)

        # 验证：最暗角必须明显偏暗才认为有效
        # 条件：绝对差距 > 8 或 相对差距 > 3%
        values = sorted(scores.values())
        if len(values) >= 2:
            gap = values[1] - values[0]
            rel_gap = gap / max(values[0], 1)
            if gap > PIXEL_GAP_THRESHOLD or rel_gap > REL_GAP_THRESHOLD:
                return darkest

        return None
    except Exception as e:
        logger.debug("图像分析失败: %s", e)
        return None
