#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸定向工具入口点
支持运行方式：python -m 图纸定向工具
"""
import sys
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 抑制MuPDF底层警告
try:
    import fitz
    if hasattr(fitz, 'set_fitz_verbosity'):
        fitz.set_fitz_verbosity(0)
except ImportError:
    print("正在安装依赖: PyMuPDF...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF", "-q"])
    import fitz
    if hasattr(fitz, 'set_fitz_verbosity'):
        fitz.set_fitz_verbosity(0)

# 检查Pillow依赖
try:
    from PIL import Image
except ImportError:
    print("正在安装依赖: Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])

from .config import __version__
from .ui import main as interactive_main
from .file_handler import process


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog='图纸定向工具',
        description='PDF图纸统一定向工具 - 图签统一到底部 + 强制横向',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python -m 图纸定向工具                          # 启动图形界面
  python -m 图纸定向工具 --cli                    # 命令行交互模式
  python -m 图纸定向工具 -i "D:\\图纸"            # 命令行处理指定文件夹
  python -m 图纸定向工具 -i "D:\\图纸" -m merge   # 合并为一个PDF
  python -m 图纸定向工具 -i "D:\\图纸" --dry-run  # 预览模式，不实际修改
  python -m 图纸定向工具 -i "D:\\图纸" -v         # 详细日志输出
        '''
    )

    parser.add_argument('-i', '--input', type=str, default=None,
                        help='输入PDF文件夹路径')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='输出目录路径（默认: 输入文件夹名_已处理）')
    parser.add_argument('-m', '--mode', choices=['merge', 'individual'],
                        default='merge',
                        help='处理模式: merge=合并, individual=独立文件 (默认: merge)')
    parser.add_argument('--dry-run', action='store_true',
                        help='预览模式：只分析不修改，显示处理结果')
    parser.add_argument('--cli', action='store_true',
                        help='使用命令行交互模式（不启动图形界面）')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细日志')
    parser.add_argument('--version', action='version',
                        version='%%(prog)s v%s' % __version__)

    return parser.parse_args()


def main():
    """主入口"""
    args = parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 没有指定输入路径
    if args.input is None:
        if args.cli:
            # --cli 模式：进入命令行交互
            interactive_main()
        else:
            # 无参数：启动图形界面
            try:
                from .gui import main as gui_main
                gui_main()
            except Exception as e:
                print("无法启动图形界面: %s" % e)
                print("使用 python -m 图纸定向工具 --cli 进入命令行模式")
                interactive_main()
        return

    # 有指定输入路径：命令行处理模式
    import os
    folder = os.path.abspath(args.input)

    if not os.path.isdir(folder):
        print("错误: 文件夹不存在: %s" % folder)
        sys.exit(1)

    # 预览模式
    if args.dry_run:
        _dry_run(folder)
        return

    # 正常处理
    print("=" * 54)
    print("  图纸统一定向工具 v%s" % __version__)
    print("  命令行模式")
    print("=" * 54)
    print()
    print("  输入: %s" % folder)
    print("  模式: %s" % ("合并为一个PDF" if args.mode == 'merge' else "保留独立文件"))
    if args.output:
        print("  输出: %s" % args.output)
    print()

    import time
    t0 = time.time()

    try:
        result = process(folder, args.mode)
        elapsed = time.time() - t0

        print()
        print("=" * 54)
        print("  处理完成! (%.1fs)" % elapsed)
        print("  总页数: %d    图纸旋转: %d    已正确: %d    封面跳过: %d" % (
            result['total'], result['rotated'], result['skipped'], result.get('cover', 0)))
        print("  输出: %s" % result['output_dir'])
        for fp in result['output_files']:
            import os
            sz = os.path.getsize(fp)
            szs = "%.1fMB" % (sz / 1048576) if sz > 1048576 else "%.0fKB" % (sz / 1024)
            print("    -> %s (%s)" % (os.path.basename(fp), szs))
        print("=" * 54)
    except Exception as e:
        print("\n错误: %s" % e)
        sys.exit(1)


def _dry_run(folder):
    """预览模式：只分析不修改"""
    import os
    from .utils import collect_pdf_files
    from .core import calc_new_rotation
    import fitz

    pdf_files = collect_pdf_files(folder)
    if not pdf_files:
        print("错误: 文件夹中没有PDF文件")
        return

    print("=" * 54)
    print("  预览模式 - 只分析不修改")
    print("=" * 54)
    print()
    print("  输入: %s" % folder)
    print("  PDF文件: %d 个" % len(pdf_files))
    print()

    total_pages = 0
    will_rotate = 0
    will_skip = 0
    will_cover = 0

    for pdf_path in pdf_files:
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print("  [错误] 无法打开: %s (%s)" % (os.path.basename(pdf_path), e))
            continue

        name = os.path.basename(pdf_path)
        print("  [%s] (%d页)" % (name, doc.page_count))

        for i in range(doc.page_count):
            pg = doc[i]
            new_rot, action, info = calc_new_rotation(pg)
            total_pages += 1

            status = ""
            if action == '封面跳过':
                will_cover += 1
                status = "跳过（封面）"
            elif action == '已正确':
                will_skip += 1
                status = "已正确"
            elif action == '已旋转':
                will_rotate += 1
                status = "将旋转 %s" % info

            print("    第%d页: %s" % (i + 1, status))

        doc.close()

    print()
    print("=" * 54)
    print("  预览结果:")
    print("  总页数: %d" % total_pages)
    print("  需要旋转: %d 页" % will_rotate)
    print("  已正确: %d 页" % will_skip)
    print("  封面跳过: %d 页" % will_cover)
    print("=" * 54)
    print()
    print("  提示: 去掉 --dry-run 参数即可实际执行处理")


if __name__ == '__main__':
    main()
