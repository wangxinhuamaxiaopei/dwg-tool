#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心分析逻辑 - 页面分析和旋转角度计算
"""
from typing import Tuple, Optional
import logging

import fitz  # type: ignore

from .config import (
    TITLE_KEYWORDS,
    CORE_KEYWORDS,
    VISUAL_MAPPING,
    BR_DELTA,
    MIN_TEXT_BLOCKS_FOR_IMAGE
)
from .image_analysis import pixel_corner

logger = logging.getLogger(__name__)


def analyze(page: fitz.Page) -> Tuple[bool, str]:
    """
    分析一页PDF：判断是否为图纸页，并确定图签位置
    
    策略：
    1. 优先使用关键词匹配（快速、准确）
    2. 文字不足时使用图像分析兜底（处理CAD转路径的图纸）
    
    Args:
        page: PyMuPDF页面对象
        
    Returns:
        tuple: (是否图纸页, 图签在视觉哪个角)
               图签位置: 'TL'(左上), 'TR'(右上), 'BL'(左下), 'BR'(右下)
    """
    rot = page.rotation or 0
    
    # 获取页面尺寸（考虑旋转）
    if rot in (90, 270):
        pw, ph = page.rect.height, page.rect.width
    else:
        pw, ph = page.rect.width, page.rect.height

    if pw <= 0 or ph <= 0:
        return False, 'BR'

    # 获取文本块
    blocks = page.get_text("blocks")
    if not blocks:
        return False, 'BR'

    # 统计四个角落的关键词命中次数
    hits = {'TL': 0, 'TR': 0, 'BL': 0, 'BR': 0}
    detail = {'TL': [], 'TR': [], 'BL': [], 'BR': []}

    for b in blocks:
        if len(b) < 5:
            continue
        x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
        txt = str(b[4] or '').strip()
        if not txt:
            continue

        # 确定文本块在哪个象限（未旋转坐标系）
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        if cx < pw * 0.5 and cy < ph * 0.5:
            uq = 'TL'
        elif cx >= pw * 0.5 and cy < ph * 0.5:
            uq = 'TR'
        elif cx < pw * 0.5 and cy >= ph * 0.5:
            uq = 'BL'
        else:
            uq = 'BR'

        # 考虑页面旋转，转换到视觉象限
        m = VISUAL_MAPPING.get(rot % 360, VISUAL_MAPPING[0])
        vc = m.get(uq, 'BR')

        # 匹配图签关键词
        for kw in TITLE_KEYWORDS:
            if kw in txt:
                hits[vc] += 1
                detail[vc].append(txt)

    # 判断是否找到图签
    total = sum(hits.values())
    has_core = any(
        sum(1 for d in detail[c] for kw in CORE_KEYWORDS if kw in d) > 0
        for c in ['TL', 'TR', 'BL', 'BR']
    )

    # 条件1：关键词命中数 >= 2 且包含核心关键词
    if total >= 2 and has_core:
        return True, max(hits, key=hits.get)

    # 条件2：文字很少 + 无图签词 → 可能是CAD转路径的图纸 → 图像兜底
    text_blocks = sum(1 for b in blocks if len(b) >= 5 and str(b[4] or '').strip())
    if text_blocks <= MIN_TEXT_BLOCKS_FOR_IMAGE:
        corner = pixel_corner(page)
        if corner:
            return True, corner

    return False, 'BR'


def calc_new_rotation(page: fitz.Page) -> Tuple[int, str, str]:
    """
    计算页面的目标旋转角度
    
    逻辑：
    - 封面页 → 不旋转
    - 图纸页 → 两步旋转：
      1. 将图签旋转到视觉底部右侧(BR)
      2. 如果页面是竖向的，再旋转90°使图签到BL（仍在底部），同时变为横向
    
    Args:
        page: PyMuPDF页面对象
        
    Returns:
        tuple: (新旋转角度, 操作类型, 详情)
               操作类型: '封面跳过', '已正确', '已旋转'
    """
    old = page.rotation or 0
    is_dwg, vc = analyze(page)

    if not is_dwg:
        return old, '封面跳过', ''

    # 第1步：将图签移到视觉 BR
    delta = BR_DELTA.get(vc, 0)
    rot_br = (old + delta) % 360

    # 获取未旋转的原始尺寸
    if old in (90, 270):
        raw_w, raw_h = page.rect.height, page.rect.width
    else:
        raw_w, raw_h = page.rect.width, page.rect.height

    # 计算 rot_br 下的视觉宽高
    if rot_br in (90, 270):
        vis_w, vis_h = raw_h, raw_w
    else:
        vis_w, vis_h = raw_w, raw_h

    if vis_w > vis_h:
        # 已横向 → 图签在 BR，OK
        final_rot = rot_br
        target_corner = 'BR'
    else:
        # 竖向 → 再转90°，图签从 BR 滑到 BL（仍在底部），变横向
        final_rot = (rot_br + 90) % 360
        target_corner = 'BL'

    # 计算总旋转量
    total_delta = (final_rot - old) % 360
    if total_delta == 0 or total_delta == 360:
        return final_rot, '已正确', ''
    else:
        deg_str = '+%d°' % (total_delta if total_delta > 0 else total_delta + 360)
        pos_str = '→%s(底部)' % target_corner
        return final_rot, '已旋转', '%s %s' % (deg_str, pos_str)
