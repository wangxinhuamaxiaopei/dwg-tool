#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸统一定向工具 v2.0
- 自动识别图纸页 vs 封面页
- 图纸页: 图签关键词定位 → 旋转统一到右下角
- 封面页: 不旋转
运行: python 图纸定向工具.py
"""
import os
import sys
import time

try:
    import fitz
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

# ═══════════════════════════════════════
#  图签关键词（工程图纸专用）
# ═══════════════════════════════════════
_TITLE_KW = ['图号', '图纸名称', '阶段', '版次', '比例', '图名',
             '项目名称', '设计阶段', '专业', '审核', '校对', '设计',
             '批准', '制图', '描图']

_VISUAL = {
    0:   {'BR':'BR','BL':'BL','TR':'TR','TL':'TL'},
    90:  {'BR':'BL','BL':'TL','TR':'BR','TL':'TR'},
    180: {'BR':'TL','BL':'TR','TR':'BL','TL':'BR'},
    270: {'BR':'TR','BL':'BR','TR':'TL','TL':'BL'},
}

_REVERSE = {}
for r, m in _VISUAL.items():
    _REVERSE[r] = {v: k for k, v in m.items()}

def analyze(page):
    """分析一页: (是否图纸, 图签在视觉哪个角)"""
    rot = page.rotation or 0
    if rot in (90, 270):
        pw, ph = page.rect.height, page.rect.width
    else:
        pw, ph = page.rect.width, page.rect.height

    if pw <= 0 or ph <= 0:
        return False, 'BR', {}

    blocks = page.get_text("blocks")
    if not blocks:
        return False, 'BR', {}

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
                detail[vc].append(txt[:50])

    total = sum(hits.values())
    if total >= 2:
        return True, max(hits, key=hits.get), detail

    # 关键词不够 → 不是图纸页
    return False, 'BR', detail


def calc_new_rotation(page):
    """计算目标旋转: (新角度, 操作类型, 详情信息)"""
    old = page.rotation or 0
    is_dwg, vc, detail = analyze(page)

    if not is_dwg:
        return old, '封面跳过', ''

    # 目标: 图签在视觉 BR
    delta_map = {'BR': 0, 'BL': 270, 'TR': 90, 'TL': 180}
    delta = delta_map.get(vc, 0)
    new_rot = (old + delta) % 360

    if new_rot != old:
        return new_rot, '已旋转', '+' + str(delta) + '°'
    else:
        return new_rot, '无需旋转', ''


# ═══════════════════════════════════════
#  批量处理
# ═══════════════════════════════════════

def process(folder, mode='merge'):
    pdf_files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    )
    if not pdf_files:
        raise FileNotFoundError("文件夹中没有PDF文件:\n" + folder)

    fn = os.path.basename(folder.rstrip('/\\'))
    parent = os.path.dirname(folder.rstrip('/\\'))
    out_dir = os.path.join(parent, fn + '_已处理')
    os.makedirs(out_dir, exist_ok=True)

    total_pages = 0
    file_pages = []
    for p in pdf_files:
        d = fitz.open(p)
        file_pages.append((p, d.page_count))
        total_pages += d.page_count
        d.close()

    print("  共 %d 个文件, %d 页\n" % (len(pdf_files), total_pages))

    rotated, skipped, cover = 0, 0, 0
    done = 0

    for pdf_path, pg_count in file_pages:
        doc = fitz.open(pdf_path)
        name = os.path.basename(pdf_path)

        for pg_idx in range(pg_count):
            done += 1
            pct = done / total_pages * 100
            bar = chr(9608) * int(pct / 5) + chr(9617) * (20 - int(pct / 5))
            sys.stdout.write("\r  [%s] %3.0f%%  %s 第%d/%d页" % (bar, pct, name, pg_idx+1, pg_count))
            sys.stdout.flush()

            pg = doc[pg_idx]
            new_rot, action, info = calc_new_rotation(pg)

            if action == '封面跳过':
                cover += 1
            elif action == '已旋转':
                pg.set_rotation(new_rot)
                rotated += 1
            else:
                skipped += 1

        if mode == 'individual':
            base = os.path.splitext(name)[0]
            out_path = os.path.join(out_dir, base + '_已修正.pdf')
            doc.save(out_path, deflate=True)
        doc.close()

    sys.stdout.write("\r  " + " " * 50 + "\r")
    sys.stdout.flush()

    print("  正在生成输出文件...")
    outputs = []

    if mode == 'merge':
        merged = fitz.open()
        for pdf_path in pdf_files:
            d = fitz.open(pdf_path)
            for i in range(d.page_count):
                pg = d[i]
                new_rot, _, _ = calc_new_rotation(pg)
                if new_rot != (pg.rotation or 0):
                    pg.set_rotation(new_rot)
            merged.insert_pdf(d)
            d.close()
        out_name = fn + '_合并统一方向.pdf'
        out_path = os.path.join(out_dir, out_name)
        merged.save(out_path, deflate=True)
        merged.close()
        outputs.append(out_path)
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
    }


# ═══════════════════════════════════════
#  主程序
# ═══════════════════════════════════════

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 54)
    print("  图纸统一定向工具 v2.0")
    print("  图纸页: 图签统一到右下角 | 封面页: 不旋转")
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

    print("  1) 合并为一个 PDF (推荐)")
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

        print("\n" + "=" * 54)
        print("  处理完成! (%.1fs)" % elapsed)
        print("  总页数: %d    图纸旋转: %d    无需旋转: %d    封面跳过: %d" % (
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
