#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常类
"""


class DrawingToolError(Exception):
    """图纸定向工具基础异常类"""
    pass


class PDFFileError(DrawingToolError):
    """PDF文件相关错误"""
    pass


class PDFCorruptedError(PDFFileError):
    """PDF文件损坏"""
    pass


class PDFEncryptedError(PDFFileError):
    """PDF文件加密"""
    pass


class OutputError(DrawingToolError):
    """输出文件相关错误"""
    pass


class DiskSpaceError(OutputError):
    """磁盘空间不足"""
    pass


class PermissionError(OutputError):
    """文件权限错误"""
    pass
