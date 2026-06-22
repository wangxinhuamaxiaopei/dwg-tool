#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils模块单元测试
"""
import os
import sys
import unittest

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from 图纸定向工具.utils import (
    natural_sort_key,
    collect_pdf_files,
    get_output_dir,
    sanitize_filename,
    format_file_size,
    check_disk_space,
    get_folder_size
)


class TestNaturalSortKey(unittest.TestCase):
    """自然排序测试"""
    
    def test_numbers_in_names(self):
        """测试文件名中的数字排序"""
        files = ['图2.pdf', '图10.pdf', '图1.pdf', '图20.pdf']
        sorted_files = sorted(files, key=natural_sort_key)
        self.assertEqual(sorted_files, ['图1.pdf', '图2.pdf', '图10.pdf', '图20.pdf'])
    
    def test_mixed_content(self):
        """测试混合内容排序"""
        items = ['a10b', 'a2b', 'a1b', 'a20b']
        sorted_items = sorted(items, key=natural_sort_key)
        self.assertEqual(sorted_items, ['a1b', 'a2b', 'a10b', 'a20b'])
    
    def test_empty_string(self):
        """测试空字符串"""
        result = natural_sort_key('')
        self.assertEqual(result, [])


class TestSanitizeFilename(unittest.TestCase):
    """文件名清理测试"""
    
    def test_remove_illegal_chars(self):
        """测试移除非法字符"""
        result = sanitize_filename('test<>:"/\\|?*file.pdf')
        self.assertNotIn('<', result)
        self.assertNotIn('>', result)
        self.assertNotIn(':', result)
        self.assertNotIn('"', result)
    
    def test_keep_valid_chars(self):
        """测试保留合法字符"""
        result = sanitize_filename('正常文件名.pdf')
        self.assertEqual(result, '正常文件名.pdf')


class TestFormatFileSize(unittest.TestCase):
    """文件大小格式化测试"""
    
    def test_bytes(self):
        """测试字节显示"""
        result = format_file_size(512)
        self.assertEqual(result, '512B')
    
    def test_kilobytes(self):
        """测试KB显示"""
        result = format_file_size(1024)
        self.assertEqual(result, '1KB')
    
    def test_megabytes(self):
        """测试MB显示"""
        result = format_file_size(1048576)
        self.assertEqual(result, '1.0MB')
    
    def test_large_file(self):
        """测试大文件"""
        result = format_file_size(5242880)  # 5MB
        self.assertEqual(result, '5.0MB')


class TestGetOutputDir(unittest.TestCase):
    """输出目录生成测试"""
    
    def test_basic_output_dir(self):
        """测试基本输出目录"""
        result = get_output_dir('C:\\工作\\图纸')
        self.assertIn('_已处理', result)
        self.assertIn('图纸', result)
    
    def test_with_timestamp(self):
        """测试带时间戳的输出目录"""
        result = get_output_dir('C:\\工作\\图纸', add_timestamp=True)
        self.assertIn('_已处理_', result)
        # 验证时间戳格式
        self.assertRegex(result, r'_\d{8}_\d{6}$')


class TestCheckDiskSpace(unittest.TestCase):
    """磁盘空间检查测试"""
    
    def test_sufficient_space(self):
        """测试空间充足"""
        has_space, free, needed = check_disk_space('E:\\', 1000)
        self.assertTrue(has_space)
    
    def test_insufficient_space(self):
        """测试空间不足"""
        # 请求一个非常大的空间
        has_space, free, needed = check_disk_space('E:\\', 999999999999999)
        self.assertFalse(has_space)


class TestGetFolderSize(unittest.TestCase):
    """文件夹大小计算测试"""
    
    def test_existing_folder(self):
        """测试现有文件夹"""
        size = get_folder_size('E:\\ocproject')
        self.assertGreater(size, 0)
    
    def test_nonexistent_folder(self):
        """测试不存在的文件夹"""
        size = get_folder_size('E:\\不存在的文件夹')
        self.assertEqual(size, 0)


if __name__ == '__main__':
    unittest.main()
