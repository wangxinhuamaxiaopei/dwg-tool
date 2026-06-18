#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸统一定向工具 - 单文件版
自动检测PDF每页图签位置，旋转统一到右下角，方便装订打印
运行: python 图纸定向工具.py
"""
import os
import sys
import time

# ── 检查依赖 ──
try:
    import fitz  # PyMuPDF
except ImportError:
    print("=" * 50)
    print("  缺少 PyMuPDF 库，正在自动安装...")
    print("=" * 50)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF", "-q"])
    import fitz
    print("  安装完成！\n")

try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    # 尝试安装
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image
    import io
    HAS_PIL = True


# ═══════════════════════════════════════
#  核心：图签检测
# ═══════════════════════════════════════

# 页面旋转 R° 时，未旋转坐标系中的角落映射到视觉角落的表
_VISUAL_MAP = {
    0:   {'BR': 'BR', 'BL': 'BL', 'TR': 'TR', 'TL': 'TL'},
    90:  {'BR': 'BL', 'BL': 'TL', 'TR': 'BR', 'TL': 'TR'},
    180: {'BR': 'TL', 'BL': 'TR', 'TR': 'BL', 'TL': 'BR'},
    270: {'BR': 'TR', 'BL': 'BR', 'TR': 'TL', 'TL': 'BL'},
}


def _quadrant(x_pct, y_pct):
    """归一化坐标 → 未旋转象限"""
    if x_pct >= 0.5 and y_pct >= 0.5:
        return 'BR'
    elif x_pct < 0.5 and y_pct >= 0.5:
        return 'BL'
    elif x_pct >= 0.5 and y_pct < 0.5:
        return 'TR'
    else:
        return 'TL'


def _to_visual(rotation, unrot_quad):
    """未旋转象限 → 视觉角落"""
    m = _VISUAL_MAP.get(rotation % 360, _VISUAL_MAP[0])
    return m.get(unrot_quad, 'BR')


def detect_by_text(page):
    """方法一：分析四个角落的文字密度"""
    try:
        rot = page.rotation or 0
        # page.rect 是旋转后的尺寸，文字坐标在未旋转坐标系中
        if rot in (90, 270):
            pw, ph = page.rect.height, page.rect.width
        else:
            pw, ph = page.rect.width, page.rect.height

        if pw <= 0 or ph <= 0:
            return None

        blocks = page.get_text("blocks")
        if not blocks:
            return None

        counts = {'TL': 0, 'TR': 0, 'BL': 0, 'BR': 0}

        for b in blocks:
            if len(b) < 5:
                continue
            x0, y0, x1, y1 = b[0], b[1], b[2], b[3]
            txt = str(b[4] or '').strip()
            if not txt:
                continue

            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            uq = _quadrant(cx / pw, cy / ph)
            vc = _to_visual(rot, uq)
            counts[vc] += len(txt)

        total = sum(counts.values())
        if total < 15:
            return None
        return max(counts, key=counts.get)
    except:
        return None


def detect_by_pixel(page, dpi=50):
    """方法二：渲染为图像，分析四角灰度密度"""
    try:
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(data)).convert('L')

        iw, ih = img.size
        hw, hh = iw // 2, ih // 2
        corners = {
            'TL': (0, 0, hw, hh),
            'TR': (hw, 0, iw, hh),
            'BL': (0, hh, hw, ih),
            'BR': (hw, hh, iw, ih),
        }

        # 计算每个角的平均灰度，最低灰度=最暗=内容最多
        scores = {}
        for name, box in corners.items():
            crop = img.crop(box)
            px = list(crop.getdata())
            avg = sum(px) / len(px) if px else 255
            scores[name] = avg

        return min(scores, key=scores.get)
    except:
        return None


def find_title_block(page):
    """综合检测：文字优先 → 图像兜底 → 默认BR"""
    r = detect_by_text(page)
    if r:
        return r
    r = detect_by_pixel(page)
    if r:
        return r
    return 'BR'


def calc_rotation(block_corner):
    """图签在某个角 → 需要顺时针旋转多少度才能到BR"""
    return {'BR': 0, 'BL': 270, 'TR': 90, 'TL': 180}[block_corner]


# ═══════════════════════════════════════
#  批量处理
# ═══════════════════════════════════════

def process(folder, mode='merge'):
    """
    处理文件夹中所有PDF，不修改原文件
    mode: 'merge' 合并成一个, 'individual' 保留独立文件
    """
    # 收集PDF
    pdf_files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    )
    if not pdf_files:
        raise FileNotFoundError(f"文件夹中没有PDF文件:\n{folder}")

    # 创建输出目录
    fn = os.path.basename(folder.rstrip('/\\'))
    parent = os.path.dirname(folder.rstrip('/\\'))
    out_dir = os.path.join(parent, fn + '_已处理')
    os.makedirs(out_dir, exist_ok=True)

    # 统计总页数
    total_pages = 0
    file_pages = []
    for p in pdf_files:
        d = fitz.open(p)
        file_pages.append((p, d.page_count))
        total_pages += d.page_count
        d.close()

    print(f"  共 {len(pdf_files)} 个文件, {total_pages} 页\n")

    # 逐文件处理（在内存中旋转，保存到输出目录）
    rotated_count = 0
    skipped_count = 0
    done = 0

    for pdf_path, pg_count in file_pages:
        doc = fitz.open(pdf_path)
        name = os.path.basename(pdf_path)

        for pg_idx in range(pg_count):
            done += 1
            pct = done / total_pages * 100
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            eta = ""
            if done > 0:
                eta_sec = (time.time() - t0) / done * (total_pages - done) if 't0' in dir() else 0
                if eta_sec > 0:
                    eta = f"  剩余{eta_sec:.0f}s"
            sys.stdout.write(f"\r  [{bar}] {pct:3.0f}%  {name} 第{pg_idx+1}/{pg_count}页{eta}")
            sys.stdout.flush()

            pg = doc[pg_idx]
            old_rot = pg.rotation or 0
            block = find_title_block(pg)
            delta = calc_rotation(block)
            new_rot = (old_rot + delta) % 360

            if new_rot != old_rot:
                pg.set_rotation(new_rot)
                rotated_count += 1
            else:
                skipped_count += 1

        # 保存到输出目录（不碰原文件）
        if mode == 'individual':
            base = os.path.splitext(name)[0]
            out_name = base + '_已修正.pdf'
            out_path = os.path.join(out_dir, out_name)
            doc.save(out_path, deflate=True)
        doc.close()

    sys.stdout.write(f"\r  {'':>50}\r")
    sys.stdout.flush()

    # ── 生成最终输出 ──
    print("  正在生成输出文件...")
    outputs = []

    if mode == 'merge':
        merged = fitz.open()
        for pdf_path in pdf_files:
            d = fitz.open(pdf_path)
            # 逐页读取并应用旋转
            for i in range(d.page_count):
                pg = d[i]
                old_rot = pg.rotation or 0
                block = find_title_block(pg)
                delta = calc_rotation(block)
                new_rot = (old_rot + delta) % 360
                if new_rot != old_rot:
                    pg.set_rotation(new_rot)
            merged.insert_pdf(d)
            d.close()
        out_name = fn + '_合并统一方向.pdf'
        out_path = os.path.join(out_dir, out_name)
        merged.save(out_path, deflate=True)
        merged.close()
        outputs.append(out_path)
    else:
        # individual 模式已经在前面保存了，这里收集文件路径
        for pdf_path in pdf_files:
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            out_name = base + '_已修正.pdf'
            out_path = os.path.join(out_dir, out_name)
            if os.path.exists(out_path):
                outputs.append(out_path)

    return {
        'total': total_pages,
        'rotated': rotated_count,
        'skipped': skipped_count,
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
    print("  图纸统一定向工具 v1.0")
    print("  检测图签位置 → 统一旋转到右下角")
    print("  方便左边装订、翻阅时图签统一朝向")
    print("=" * 54)
    print()

    # ── 选文件夹 ──
    while True:
        try:
            raw = input("  文件夹路径 (可拖拽文件夹或文件到此处) > ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            return
        if not raw:
            print("  不能为空")
            continue
        p = os.path.abspath(raw)
        # 如果拖入的是文件，自动使用它所在的文件夹
        if os.path.isfile(p):
            f = os.path.dirname(p)
            print(f"  📄 识别为文件，自动使用所在文件夹")
        elif os.path.isdir(p):
            f = p
        else:
            print(f"  找不到路径: {p}")
            continue
        pdfs = [x for x in os.listdir(f) if x.lower().endswith('.pdf')]
        if not pdfs:
            print(f"  该文件夹中没有 PDF 文件")
            if input("  重新选择? (y/n): ").strip().lower() != 'y':
                return
            continue
        print(f"  找到 {len(pdfs)} 个 PDF 文件\n")
        break

    # ── 选模式 ──
    print("  输出模式:")
    print("    1) 合并为一个 PDF (推荐，方便一次性打印)")
    print("    2) 保留独立文件 (每个文件单独输出)")
    m = input("\n  请选择 (1或2, 默认1): ").strip()
    mode = 'merge' if m != '2' else 'individual'

    # ── 确认 ──
    fn = os.path.basename(f.rstrip('/\\'))
    out = os.path.join(os.path.dirname(f.rstrip('/\\')), fn + '_已处理')
    print(f"\n  输出目录: {out}")
    r = input("  按 Enter 开始 (输入 n 取消): ").strip().lower()
    if r == 'n':
        print("  已取消")
        return

    # ── 执行 ──
    print("\n" + "-" * 54)
    global t0
    t0 = time.time()

    try:
        result = process(f, mode)
        elapsed = time.time() - t0

        print("\n" + "=" * 54)
        print(f"  ✅ 处理完成! (耗时 {elapsed:.1f} 秒)")
        print(f"  总页数: {result['total']}")
        print(f"  已旋转: {result['rotated']}  无需旋转: {result['skipped']}")
        print(f"  源文件: {result['files']} 个")
        print(f"\n  📁 输出: {result['output_dir']}")
        for fp in result['output_files']:
            sz = os.path.getsize(fp)
            szs = f"{sz/1048576:.1f}MB" if sz > 1048576 else f"{sz/1024:.0f}KB"
            print(f"    └─ {os.path.basename(fp)} ({szs})")
        print("=" * 54)
        print("\n  现在可以打开输出文件进行打印了！")
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    input("\n  按 Enter 退出...")
    del t0


if __name__ == '__main__':
    t0 = 0
    main()
