#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行所有单元测试
"""
import os
import sys
import unittest

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 发现并运行所有测试
if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回退出码
    sys.exit(0 if result.wasSuccessful() else 1)
