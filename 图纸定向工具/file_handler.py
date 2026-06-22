#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作 - PDF文件收集、处理、保存
"""
import os
import sys
import time
import logging

import fitz

from .config import __version__
from .utils import collect_pdf_files, get_output_dir, check_disk_space, get_folder_size
from .core import calc_new_rotation

logger = logging.getLogger(__name__)


def safe_print(*args, **kwargs):
    """安全的print函数，GUI模式下不输出到stdout"""
    if sys.stdout:
        print(*args, **kwargs)


def process(folder, mode='merge'):
    """
    处理文件夹中的所有PDF文件
    
    Args:
        folder: 输入文件夹路径
        mode: 处理模式
              - 'merge': 合并为一个PDF（默认）
              - 'individual': 保留独立文件
        
    Returns:
        dict: 处理结果统计
              - total: 总页数
              - rotated: 旋转的页数
              - skipped: 已正确的页数
              - cover: 跳过的封面页数
              - files: 处理的文件数
              - output_dir: 输出目录
              - output_files: 输出文件列表
              - page_log: 每页处理日志
    """
    # 收集PDF文件
    pdf_files = collect_pdf_files(folder)
    if not pdf_files:
        raise FileNotFoundError("文件夹中没有PDF文件:\n" + folder)

    # 准备输出目录
    out_dir = get_output_dir(folder)
    os.makedirs(out_dir, exist_ok=True)

    # 统计总页数
    total_pages = 0
    file_pages = []
    skipped_files = []
    for p in pdf_files:
        try:
            d = fitz.open(p)
            # 检查是否加密
            if d.is_encrypted:
                logger.warning("跳过加密PDF: %s", os.path.basename(p))
                skipped_files.append(os.path.basename(p))
                d.close()
                continue
            file_pages.append((p, d.page_count))
            total_pages += d.page_count
            d.close()
        except Exception as e:
            logger.error("无法打开PDF文件 %s: %s", p, e)
            skipped_files.append(os.path.basename(p))
            continue

    if skipped_files:
        logger.warning("跳过 %d 个文件: %s", len(skipped_files), ", ".join(skipped_files))

    logger.info("共 %d 个文件, %d 页", len(file_pages), total_pages)
    for idx, (p, pgc) in enumerate(file_pages):
        logger.info("[%d] %s (%d页)", idx + 1, os.path.basename(p), pgc)
    safe_print()

    # 处理每一页
    rotated, skipped, cover = 0, 0, 0
    done = 0
    page_log = []
    rotation_cache = {}
    start_time = time.time()  # 记录开始时间

    for pdf_path, pg_count in file_pages:
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error("无法打开PDF文件 %s: %s", pdf_path, e)
            continue
        name = os.path.basename(pdf_path)
        rotation_cache[name] = {}

        for pg_idx in range(pg_count):
            done += 1
            pct = done / total_pages * 100
            _update_progress(pct, name, pg_idx + 1, pg_count, start_time, done, total_pages)

            pg = doc[pg_idx]
            new_rot, action, info = calc_new_rotation(pg)
            rotation_cache[name][pg_idx] = new_rot
            page_log.append((done, name, pg_idx + 1, action, info))

            if action == '封面跳过':
                cover += 1
            elif action in ('已旋转', '已正确'):
                if new_rot != (pg.rotation or 0):
                    pg.set_rotation(new_rot)
                if action == '已旋转':
                    rotated += 1
                else:
                    skipped += 1

        if mode == 'individual':
            _save_individual(doc, name, out_dir)
        doc.close()

    _clear_progress()

    # 磁盘空间检查
    source_size = get_folder_size(folder)
    has_space, free, needed = check_disk_space(out_dir, int(source_size * 1.5))
    if not has_space:
        logger.warning("磁盘空间不足! 需要: %.1fMB, 可用: %.1fMB",
                       needed / 1048576, free / 1048576)

    # 生成输出文件
    safe_print("  正在生成输出文件...")
    outputs = []

    if mode == 'merge':
        fn = os.path.basename(folder.rstrip('/\\'))
        outputs = _merge_pdfs(pdf_files, rotation_cache, fn, out_dir)
    else:
        outputs = _collect_individual_outputs(pdf_files, out_dir)

    return {
        'total': total_pages,
        'rotated': rotated,
        'skipped': skipped,
        'cover': cover,
        'files': len(pdf_files),
        'output_dir': out_dir,
        'output_files': outputs,
        'page_log': page_log,
    }


def _update_progress(pct, filename, page_num, total_pages, start_time, done, total):
    """更新进度条显示，包含ETA"""
    n_bar = int(pct / 5)
    bar = chr(9608) * n_bar + chr(9617) * (20 - n_bar)
    
    # 计算ETA
    elapsed = time.time() - start_time
    if done > 0 and elapsed > 0:
        eta_seconds = elapsed / done * (total - done)
        if eta_seconds >= 60:
            eta_str = "%dm%ds" % (int(eta_seconds // 60), int(eta_seconds % 60))
        else:
            eta_str = "%ds" % int(eta_seconds)
    else:
        eta_str = "--"
    
    if sys.stdout:
        sys.stdout.write("\r  [%s] %3.0f%%  %s  第%d/%d页  ETA:%s" % (bar, pct, filename, page_num, total_pages, eta_str))
        sys.stdout.flush()


def _clear_progress():
    """清除进度条"""
    if sys.stdout:
        sys.stdout.write("\r" + " " * 55 + "\r")
        sys.stdout.flush()


def _save_individual(doc, name, out_dir):
    """保存单个PDF文件"""
    base = os.path.splitext(name)[0]
    out_path = os.path.join(out_dir, base + '_已修正.pdf')
    try:
        doc.save(out_path, deflate=True)
    except IOError as e:
        logger.error("保存失败 %s: %s", out_path, e)


def _merge_pdfs(pdf_files, rotation_cache, folder_name, out_dir):
    """合并多个PDF文件"""
    try:
        merged = fitz.open()
    except Exception as e:
        logger.error("无法创建合并文档: %s", e)
        return []

    total_merged = 0
    for pdf_path in pdf_files:
        try:
            d = fitz.open(pdf_path)
        except Exception as e:
            logger.error("无法打开PDF文件 %s: %s", pdf_path, e)
            continue
        name = os.path.basename(pdf_path)

        for i in range(d.page_count):
            pg = d[i]
            new_rot = rotation_cache[name][i]
            if new_rot != (pg.rotation or 0):
                pg.set_rotation(new_rot)

        merged.insert_pdf(d)
        added = d.page_count
        total_merged += added
        d.close()
        if sys.stdout:
            sys.stdout.write("\r  合并: %s (%d页) → 总%d页" % (name, added, total_merged))
            sys.stdout.flush()

    safe_print()

    out_name = folder_name + '_合并统一方向.pdf'
    out_path = os.path.join(out_dir, out_name)
    outputs = []
    try:
        merged.save(out_path, deflate=True)
        merged.close()
        outputs.append(out_path)
    except IOError as e:
        logger.error("保存合并文件失败 %s: %s", out_path, e)
        merged.close()

    return outputs


def _collect_individual_outputs(pdf_files, out_dir):
    """收集已生成的独立文件列表"""
    outputs = []
    for pdf_path in pdf_files:
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        out_name = base + '_已修正.pdf'
        out_path = os.path.join(out_dir, out_name)
        if os.path.exists(out_path):
            outputs.append(out_path)
    return outputs
