#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸统一定向工具 v2.1
- 图纸页: 图签统一到底部 + 强制横向 → 打印友好
- 封面页: 不旋转
- 严格保持页面顺序
运行: python 图纸定向工具.py
"""
import os
import sys
import time
import re
import logging

try:
    import fitz
    fitz.set_fitz_verbosity(0)  # 抑制MuPDF底层警告
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF", "-q"])
    import fitz

try:
    from PIL import Image
    import io
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image
    import io

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════
#  自然排序（图2 < 图10）
# ═══════════════════════════════════════
def _num_key(s):
    """提取数字用于自然排序"""
    parts = re.split(r'(\d+)', s)
    key = []
    for p in parts:
        if p.isdigit():
            key.append(('0', int(p)))
        else:
            key.append(('1', p.lower()))
    return key

# ═══════════════════════════════════════
#  图签关键词
# ═══════════════════════════════════════
_TITLE_KW = ['图号', '图纸名称', '阶段', '版次', '比例', '图名',
             '项目名称', '设计阶段', '审核', '校对',
             '批准', '制图', '描图']

# 核心图签词：必须有至少一个才能判定为图纸页
_CORE_KW = ['图号', '图纸名称', '阶段', '版次', '比例', '图名']

_VISUAL = {
    0:   {'BR':'BR','BL':'BL','TR':'TR','TL':'TL'},
    90:  {'BR':'BL','BL':'TL','TR':'BR','TL':'TR'},
    180: {'BR':'TL','BL':'TR','TR':'BL','TL':'BR'},
    270: {'BR':'TR','BL':'BR','TR':'TL','TL':'BL'},
}


def analyze(page):
    """
    分析一页: (是否图纸, 图签在视觉哪个角)
    优先关键词匹配 → 文字不足时图像兜底
    """
    rot = page.rotation or 0
    if rot in (90, 270):
        pw, ph = page.rect.height, page.rect.width
    else:
        pw, ph = page.rect.width, page.rect.height

    if pw <= 0 or ph <= 0:
        return False, 'BR'

    blocks = page.get_text("blocks")
    if not blocks:
        return False, 'BR'

    hits = {'TL': 0, 'TR': 0, 'BL': 0, 'BR': 0}
    detail = {'TL': [], 'TR': [], 'BL': [], 'BR': []}

    for b in blocks:
        if len(b) < 5:
            continue
        x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
        txt = str(b[4] or '').strip()
        if not txt:
            continue
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        if cx < pw * 0.5 and cy < ph * 0.5:    uq = 'TL'
        elif cx >= pw * 0.5 and cy < ph * 0.5:  uq = 'TR'
        elif cx < pw * 0.5 and cy >= ph * 0.5:  uq = 'BL'
        else:                                    uq = 'BR'

        m = _VISUAL.get(rot % 360, _VISUAL[0])
        vc = m.get(uq, 'BR')

        for kw in _TITLE_KW:
            if kw in txt:
                hits[vc] += 1
                detail[vc].append(txt)

    total = sum(hits.values())
    has_core = any(
        sum(1 for d in detail[c] for kw in _CORE_KW if kw in d) > 0
        for c in ['TL', 'TR', 'BL', 'BR']
    )

    if total >= 2 and has_core:
        return True, max(hits, key=hits.get)

    # 文字很少 + 无图签词 → 可能是CAD转路径的图纸 → 图像兜底
    text_blocks = sum(1 for b in blocks if len(b) >= 5 and str(b[4] or '').strip())
    if text_blocks <= 15:
        corner = _pixel_corner(page)
        if corner:
            return True, corner

    return False, 'BR'


def _pixel_corner(page):
    """图像分析: 渲染页面，四角最暗的=图签所在"""
    try:
        zoom = 36.0 / 72.0  # 低分辨率，够用且快
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(data)).convert('L')
        iw, ih = img.size
        hw, hh = iw // 2, ih // 2

        # 取四个象限的 25% 区域（更靠近角落，避免中心干扰）
        # 用较小的角落区域：左/上 35%，右/下 35%
        left = int(iw * 0.3)
        right = int(iw * 0.7)
        top = int(ih * 0.3)
        bottom = int(ih * 0.7)

        corners = {
            'TL': (0, 0, left, top),
            'TR': (right, 0, iw, top),
            'BL': (0, bottom, left, ih),
            'BR': (right, bottom, iw, ih),
        }

        scores = {}
        for name, box in corners.items():
            crop = img.crop(box)
            px = list(crop.getdata())
            avg = sum(px) / len(px) if px else 255
            scores[name] = avg

        darkest = min(scores, key=scores.get)
        # 检查是否明显偏暗（最暗角必须比第二暗角深 8 以上，且相对差距 ≥ 3%）
        values = sorted(scores.values())
        if len(values) >= 2:
            gap = values[1] - values[0]
            rel_gap = gap / max(values[0], 1)  # 相对差距
            if gap > 8 or rel_gap > 0.03:
                return darkest
        return None
    except Exception as e:
        logger.debug("图像分析失败: %s", e)
        return None


def calc_new_rotation(page):
    """
    计算目标旋转:
      - 封面页 → 不动
      - 图纸页 → 第1步: 图签旋转到视觉底部(BR)
                第2步: 如果还是竖向 → 再旋转90°到BL(仍在底部) + 横向
    返回: (新角度, 操作类型, 详情)
    """
    old = page.rotation or 0
    is_dwg, vc = analyze(page)

    if not is_dwg:
        return old, '封面跳过', ''

    # 第1步: 图签移到视觉 BR
    br_delta = {'BR': 0, 'BL': 270, 'TR': 90, 'TL': 180}
    delta = br_delta.get(vc, 0)
    rot_br = (old + delta) % 360

    # 第2步: 检查视觉方向（用 page.rect 判断）
    # 创建一个临时检查用 page 看旋转后的宽高
    # page.rect 反映的是视觉尺寸
    # 如果在 rot_br 下 w > h，说明已横向；否则需要再转90°
    # 通过快速数学计算：旋转0/180 时 w=原始w, h=原始h；旋转90/270 时 w=原始h, h=原始w

    # 获取未旋转尺寸
    if old in (90, 270):
        raw_w, raw_h = page.rect.height, page.rect.width
    else:
        raw_w, raw_h = page.rect.width, page.rect.height

    # rot_br 下的视觉宽高
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

    total_delta = (final_rot - old) % 360
    if total_delta == 0:
        return final_rot, '已正确', ''
    elif total_delta == 360:
        return final_rot, '已正确', ''
    else:
        deg_str = '+%d°' % (total_delta if total_delta > 0 else total_delta + 360)
        pos_str = '→%s(底部)' % target_corner
        return final_rot, '已旋转', '%s %s' % (deg_str, pos_str)


# ═══════════════════════════════════════
#  批量处理
# ═══════════════════════════════════════

def process(folder, mode='merge'):
    # 自然排序收集 PDF
    pdf_files = [
        os.path.join(folder, f)
        for f in sorted(
            [x for x in os.listdir(folder) if x.lower().endswith('.pdf')],
            key=_num_key
        )
    ]
    if not pdf_files:
        raise FileNotFoundError("文件夹中没有PDF文件:\n" + folder)

    fn = os.path.basename(folder.rstrip('/\\'))
    parent = os.path.dirname(folder.rstrip('/\\'))
    out_dir = os.path.join(parent, fn + '_已处理')
    os.makedirs(out_dir, exist_ok=True)

    total_pages = 0
    file_pages = []
    for p in pdf_files:
        try:
            d = fitz.open(p)
            file_pages.append((p, d.page_count))
            total_pages += d.page_count
            d.close()
        except Exception as e:
            logger.error("无法打开PDF文件 %s: %s", p, e)
            continue

    logger.info("共 %d 个文件, %d 页", len(pdf_files), total_pages)
    for idx, (p, pgc) in enumerate(file_pages):
        logger.info("[%d] %s (%d页)", idx + 1, os.path.basename(p), pgc)
    print()

    rotated, skipped, cover = 0, 0, 0
    done = 0
    page_log = []  # (page_num, source_file, page_in_file, action, info)
    rotation_cache = {}  # 缓存旋转角度，避免重复计算

    for pdf_path, pg_count in file_pages:
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error("无法打开PDF文件 %s: %s", pdf_path, e)
            continue
        name = os.path.basename(pdf_path)
        rotation_cache[name] = {}  # 初始化缓存

        for pg_idx in range(pg_count):
            done += 1
            pct = done / total_pages * 100
            n_bar = int(pct / 5)
            bar = chr(9608) * n_bar + chr(9617) * (20 - n_bar)
            sys.stdout.write("\r  [%s] %3.0f%%  %s  第%d/%d页" % (bar, pct, name, pg_idx+1, pg_count))
            sys.stdout.flush()

            pg = doc[pg_idx]
            new_rot, action, info = calc_new_rotation(pg)
            rotation_cache[name][pg_idx] = new_rot  # 缓存旋转角度
            page_log.append((done, name, pg_idx+1, action, info))

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
            base = os.path.splitext(name)[0]
            out_path = os.path.join(out_dir, base + '_已修正.pdf')
            try:
                doc.save(out_path, deflate=True)
            except IOError as e:
                logger.error("保存失败 %s: %s", out_path, e)
        doc.close()

    sys.stdout.write("\r" + " " * 55 + "\r")
    sys.stdout.flush()

    print("  正在生成输出文件...")
    outputs = []

    if mode == 'merge':
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
                # 使用缓存值，避免重复计算
                new_rot = rotation_cache[name][i]
                if new_rot != (pg.rotation or 0):
                    pg.set_rotation(new_rot)
            merged.insert_pdf(d)
            added = d.page_count
            total_merged += added
            d.close()
            sys.stdout.write("\r  合并: %s (%d页) → 总%d页" % (name, added, total_merged))
            sys.stdout.flush()
        print()

        out_name = fn + '_合并统一方向.pdf'
        out_path = os.path.join(out_dir, out_name)
        try:
            merged.save(out_path, deflate=True)
            merged.close()
            outputs.append(out_path)
        except IOError as e:
            logger.error("保存合并文件失败 %s: %s", out_path, e)
            merged.close()
    else:
        for pdf_path in pdf_files:
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            out_name = base + '_已修正.pdf'
            out_path = os.path.join(out_dir, out_name)
            if os.path.exists(out_path):
                outputs.append(out_path)

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


# ═══════════════════════════════════════
#  主程序
# ═══════════════════════════════════════

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 54)
    print("  图纸统一定向工具 v2.1")
    print("  图签统一到底部 + 强制横向 | 封面页不动")
    print("  严格保持页面顺序")
    print("=" * 54)
    print()

    while True:
        try:
            raw = input("  文件夹路径 (可拖拽文件夹或文件) > ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            return
        if not raw:
            print("  不能为空"); continue
        p = os.path.abspath(raw)
        if os.path.isfile(p):
            f = os.path.dirname(p)
            print("  识别为文件，自动使用文件夹")
        elif os.path.isdir(p):
            f = p
        else:
            print("  找不到: %s" % p); continue
        pdfs = [x for x in os.listdir(f) if x.lower().endswith('.pdf')]
        if not pdfs:
            print("  没有 PDF 文件")
            if input("  重选? (y/n): ").strip().lower() != 'y':
                return
            continue
        print("  PDF: %d 个\n" % len(pdfs))
        break

    print("  1) 合并为一个 PDF (推荐，顺序严格保持)")
    print("  2) 保留独立文件")
    m = input("  选择 (1/2, 默认1): ").strip()
    mode = 'merge' if m != '2' else 'individual'

    fn = os.path.basename(f.rstrip('/\\'))
    out = os.path.join(os.path.dirname(f.rstrip('/\\')), fn + '_已处理')
    print("\n  输出: %s" % out)
    r = input("  按 Enter 开始 (n 取消): ").strip().lower()
    if r == 'n':
        print("  已取消"); return

    print("\n" + "-" * 54)
    global t0
    t0 = time.time()

    try:
        result = process(f, mode)
        elapsed = time.time() - t0

        # 打印每页处理详情
        print("\n" + "=" * 54)
        print("  %-8s %-20s %-12s %-10s" % ("页序", "来源文件", "页码", "处理"))
        print("  " + "-" * 50)
        for pnum, src, pidx, act, note in result.get('page_log', []):
            short_name = src if len(src) <= 20 else src[:17] + "..."
            detail = act
            if note:
                detail = act + " " + note
            print("  %-8d %-20s %-12s %-10s" % (pnum, short_name, "第%d页" % pidx, detail))

        print("\n" + "=" * 54)
        print("  处理完成! (%.1fs)" % elapsed)
        print("  总页数: %d    图纸旋转: %d    已正确: %d    封面跳过: %d" % (
            result['total'], result['rotated'], result['skipped'], result.get('cover', 0)))
        print("  源文件: %d 个" % result['files'])
        print("\n  输出: %s" % result['output_dir'])
        for fp in result['output_files']:
            sz = os.path.getsize(fp)
            szs = "%.1fMB" % (sz / 1048576) if sz > 1048576 else "%.0fKB" % (sz / 1024)
            print("    -> %s (%s)" % (os.path.basename(fp), szs))
        print("=" * 54)
    except Exception as e:
        print("\n  错误: %s" % e)
        import traceback
        traceback.print_exc()

    input("\n  按 Enter 退出...")
    del t0


if __name__ == '__main__':
    t0 = 0
    main()
