#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸定向工具包
"""
from .config import __version__
from .file_handler import process
from .core import analyze, calc_new_rotation
from .ui import main as cli_main

# 尝试导入GUI（可选）
try:
    from .gui import main as gui_main
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

__all__ = ['__version__', 'process', 'analyze', 'calc_new_rotation', 
           'cli_main', 'gui_main', 'HAS_GUI']
