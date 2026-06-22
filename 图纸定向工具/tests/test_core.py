#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core模块单元测试
"""
import os
import sys
import unittest

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from 图纸定向工具.config import (
    TITLE_KEYWORDS,
    CORE_KEYWORDS,
    VISUAL_MAPPING,
    BR_DELTA
)


class TestConfig(unittest.TestCase):
    """配置常量测试"""
    
    def test_title_keywords_not_empty(self):
        """测试标题关键词列表不为空"""
        self.assertGreater(len(TITLE_KEYWORDS), 0)
    
    def test_core_keywords_not_empty(self):
        """测试核心关键词列表不为空"""
        self.assertGreater(len(CORE_KEYWORDS), 0)
    
    def test_core_keywords_subset_of_title(self):
        """测试核心关键词是标题关键词的子集"""
        for kw in CORE_KEYWORDS:
            self.assertIn(kw, TITLE_KEYWORDS)
    
    def test_visual_mapping_complete(self):
        """测试旋转映射完整"""
        for angle in [0, 90, 180, 270]:
            self.assertIn(angle, VISUAL_MAPPING)
            for corner in ['TL', 'TR', 'BL', 'BR']:
                self.assertIn(corner, VISUAL_MAPPING[angle])
    
    def test_br_delta_complete(self):
        """测试BRDelta完整"""
        for corner in ['TL', 'TR', 'BL', 'BR']:
            self.assertIn(corner, BR_DELTA)
            self.assertIn(BR_DELTA[corner], [0, 90, 180, 270])


class TestVisualMapping(unittest.TestCase):
    """旋转映射测试"""
    
    def test_zero_rotation(self):
        """测试0度旋转（无变化）"""
        mapping = VISUAL_MAPPING[0]
        self.assertEqual(mapping['TL'], 'TL')
        self.assertEqual(mapping['TR'], 'TR')
        self.assertEqual(mapping['BL'], 'BL')
        self.assertEqual(mapping['BR'], 'BR')
    
    def test_90_rotation(self):
        """测试90度旋转"""
        mapping = VISUAL_MAPPING[90]
        # 90度旋转后，原来的BR变成BL
        self.assertEqual(mapping['BR'], 'BL')
        self.assertEqual(mapping['BL'], 'TL')
    
    def test_180_rotation(self):
        """测试180度旋转"""
        mapping = VISUAL_MAPPING[180]
        # 180度旋转后，对角互换
        self.assertEqual(mapping['BR'], 'TL')
        self.assertEqual(mapping['TL'], 'BR')
    
    def test_270_rotation(self):
        """测试270度旋转"""
        mapping = VISUAL_MAPPING[270]
        # 270度旋转后
        self.assertEqual(mapping['BR'], 'TR')
        self.assertEqual(mapping['TR'], 'TL')


class TestBRDelta(unittest.TestCase):
    """BRDelta测试"""
    
    def test_already_at_br(self):
        """测试已在BR位置"""
        self.assertEqual(BR_DELTA['BR'], 0)
    
    def test_at_bl(self):
        """测试在BL位置"""
        self.assertEqual(BR_DELTA['BL'], 270)
    
    def test_at_tr(self):
        """测试在TR位置"""
        self.assertEqual(BR_DELTA['TR'], 90)
    
    def test_at_tl(self):
        """测试在TL位置"""
        self.assertEqual(BR_DELTA['TL'], 180)


if __name__ == '__main__':
    unittest.main()
