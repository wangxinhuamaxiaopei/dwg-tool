#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸定向工具 - GUI启动入口
"""
import sys
import os

# GUI模式下，确保sys.stdout不为None
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

# 确保能找到包
if getattr(sys, 'frozen', False):
    # 打包后的路径
    base_path = sys._MEIPASS
else:
    # 开发环境路径
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

# 启动GUI
from 图纸定向工具.gui import DrawingToolGUI

if __name__ == '__main__':
    app = DrawingToolGUI()
    app.run()
