#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_analysis模块单元测试
"""
import os
import sys
import unittest

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from 图纸定向工具.config import (
    ZOOM_FACTOR,
    QUADRANT_MARGIN,
    PIXEL_GAP_THRESHOLD,
    REL_GAP_THRESHOLD,
    MIN_TEXT_BLOCKS_FOR_IMAGE
)


class TestImageAnalysisConfig(unittest.TestCase):
    """图像分析配置测试"""
    
    def test_zoom_factor(self):
        """测试缩放因子"""
        self.assertGreater(ZOOM_FACTOR, 0)
        self.assertLess(ZOOM_FACTOR, 1)
    
    def test_quadrant_margin(self):
        """测试象限边距"""
        self.assertGreater(QUADRANT_MARGIN, 0)
        self.assertLess(QUADRANT_MARGIN, 0.5)
    
    def test_pixel_gap_threshold(self):
        """测试像素差距阈值"""
        self.assertGreater(PIXEL_GAP_THRESHOLD, 0)
    
    def test_rel_gap_threshold(self):
        """测试相对差距阈值"""
        self.assertGreater(REL_GAP_THRESHOLD, 0)
        self.assertLess(REL_GAP_THRESHOLD, 1)
    
    def test_min_text_blocks(self):
        """测试最小文本块数量"""
        self.assertGreater(MIN_TEXT_BLOCKS_FOR_IMAGE, 0)


if __name__ == '__main__':
    unittest.main()
