#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数 - 自然排序、路径处理等
"""
import os
import re


def natural_sort_key(s):
    """
    提取数字用于自然排序（图2 < 图10）
    
    Args:
        s: 输入字符串
        
    Returns:
        排序键列表
    """
    if not s:
        return []
    parts = re.split(r'(\d+)', s)
    return [('0', int(p)) if p.isdigit() else ('1', p.lower()) for p in parts]


def collect_pdf_files(folder):
    """
    收集文件夹中的PDF文件并按自然排序排列
    
    Args:
        folder: 文件夹路径
        
    Returns:
        排序后的PDF文件完整路径列表
    """
    return [
        os.path.join(folder, f)
        for f in sorted(
            [x for x in os.listdir(folder) if x.lower().endswith('.pdf')],
            key=natural_sort_key
        )
    ]


def get_output_dir(folder, add_timestamp=False):
    """
    根据输入文件夹生成输出目录路径
    
    Args:
        folder: 输入文件夹路径
        add_timestamp: 是否添加时间戳后缀（避免覆盖）
        
    Returns:
        输出目录完整路径
    """
    import time
    fn = os.path.basename(folder.rstrip('/\\'))
    parent = os.path.dirname(folder.rstrip('/\\'))
    
    base_name = fn + '_已处理'
    
    if add_timestamp:
        # 添加时间戳
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        base_name = base_name + '_' + timestamp
    
    out_dir = os.path.join(parent, base_name)
    
    # 如果目录已存在且未指定时间戳，自动添加时间戳
    if not add_timestamp and os.path.exists(out_dir):
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        out_dir = os.path.join(parent, base_name + '_' + timestamp)
    
    return out_dir


def sanitize_filename(name):
    """
    清理文件名中的非法字符
    
    Args:
        name: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # Windows非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    return re.sub(illegal_chars, '_', name)


def format_file_size(size_bytes):
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化的字符串（如 "1.5MB", "256KB" 或 "512B"）
    """
    if size_bytes >= 1048576:  # >= 1MB
        return "%.1fMB" % (size_bytes / 1048576)
    elif size_bytes >= 1024:  # >= 1KB
        return "%.0fKB" % (size_bytes / 1024)
    else:  # < 1KB
        return "%dB" % size_bytes


def check_disk_space(folder, required_bytes):
    """
    检查磁盘空间是否充足
    
    Args:
        folder: 目标文件夹路径
        required_bytes: 需要的最小空间（字节）
        
    Returns:
        tuple: (是否充足, 可用空间, 需要空间)
    """
    try:
        import shutil
        usage = shutil.disk_usage(folder)
        free = usage.free
        return free >= required_bytes, free, required_bytes
    except Exception:
        # 无法检测时默认通过
        return True, 0, required_bytes


def get_folder_size(folder):
    """
    计算文件夹总大小
    
    Args:
        folder: 文件夹路径
        
    Returns:
        总大小（字节）
    """
    total = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total
