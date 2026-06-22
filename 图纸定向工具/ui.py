#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户交互 - 界面显示、输入处理、结果报告
"""
import os
import sys
import time
import logging

from .config import __version__
from .file_handler import process
from .utils import format_file_size

logger = logging.getLogger(__name__)


def main():
    """主程序入口 - 交互式界面"""
    os.system('cls' if os.name == 'nt' else 'clear')
    _print_header()

    # 获取输入文件夹
    folder = _get_input_folder()
    if not folder:
        return

    # 选择处理模式
    mode = _get_mode()

    # 确认并开始处理
    if not _confirm_start(folder):
        print("  已取消")
        return

    print("\n" + "-" * 54)
    t0 = time.time()

    try:
        result = process(folder, mode)
        elapsed = time.time() - t0
        _print_report(result, elapsed)
        _notify_completion()  # 处理完成提醒
    except Exception as e:
        print("\n  错误: %s" % e)
        import traceback
        traceback.print_exc()

    input("\n  按 Enter 退出...")


def _print_header():
    """打印工具标题"""
    print("=" * 54)
    print("  图纸统一定向工具 v%s" % __version__)
    print("  图签统一到底部 + 强制横向 | 封面页不动")
    print("  严格保持页面顺序")
    print("=" * 54)
    print()


def _get_input_folder():
    """获取用户输入的文件夹路径"""
    while True:
        try:
            raw = input("  文件夹路径 (可拖拽文件夹或文件) > ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            return None

        if not raw:
            print("  不能为空")
            continue

        p = os.path.abspath(raw)

        if os.path.isfile(p):
            f = os.path.dirname(p)
            print("  识别为文件，自动使用文件夹")
        elif os.path.isdir(p):
            f = p
        else:
            print("  找不到: %s" % p)
            continue

        pdfs = [x for x in os.listdir(f) if x.lower().endswith('.pdf')]
        if not pdfs:
            print("  没有 PDF 文件")
            if input("  重选? (y/n): ").strip().lower() != 'y':
                return None
            continue

        print("  PDF: %d 个\n" % len(pdfs))
        return f


def _get_mode():
    """获取处理模式"""
    print("  1) 合并为一个 PDF (推荐，顺序严格保持)")
    print("  2) 保留独立文件")
    m = input("  选择 (1/2, 默认1): ").strip()
    return 'merge' if m != '2' else 'individual'


def _confirm_start(folder):
    """确认是否开始处理"""
    from .utils import get_output_dir
    out_dir = get_output_dir(folder)
    print("\n  输出: %s" % out_dir)
    r = input("  按 Enter 开始 (n 取消): ").strip().lower()
    return r != 'n'


def _print_report(result, elapsed):
    """打印处理报告"""
    # 每页处理详情
    print("\n" + "=" * 54)
    print("  %-8s %-20s %-12s %-10s" % ("页序", "来源文件", "页码", "处理"))
    print("  " + "-" * 50)
    for pnum, src, pidx, act, note in result.get('page_log', []):
        short_name = src if len(src) <= 20 else src[:17] + "..."
        detail = act
        if note:
            detail = act + " " + note
        print("  %-8d %-20s %-12s %-10s" % (pnum, short_name, "第%d页" % pidx, detail))

    # 统计摘要
    print("\n" + "=" * 54)
    print("  处理完成! (%.1fs)" % elapsed)
    print("  总页数: %d    图纸旋转: %d    已正确: %d    封面跳过: %d" % (
        result['total'], result['rotated'], result['skipped'], result.get('cover', 0)))
    print("  源文件: %d 个" % result['files'])

    # 输出文件列表
    print("\n  输出: %s" % result['output_dir'])
    for fp in result['output_files']:
        sz = os.path.getsize(fp)
        print("    -> %s (%s)" % (os.path.basename(fp), format_file_size(sz)))
    print("=" * 54)
    
    # 生成HTML报告
    try:
        report_path = _generate_html_report(result, elapsed)
        print("\n  HTML报告已生成: %s" % report_path)
    except Exception as e:
        logger.debug("生成HTML报告失败: %s", e)


def _notify_completion():
    """处理完成后的系统通知"""
    # Windows声音提醒
    if os.name == 'nt':
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
    
    # 尝试使用系统通知（如果安装了plyer）
    try:
        from plyer import notification
        notification.notify(
            title='图纸定向工具',
            message='PDF处理已完成！',
            timeout=5
        )
    except ImportError:
        pass
    except Exception:
        pass


def _generate_html_report(result, elapsed):
    """生成HTML格式的处理报告"""
    from datetime import datetime
    
    output_dir = result['output_dir']
    report_path = os.path.join(output_dir, '处理报告.html')
    
    # 构建表格行
    rows = ""
    for pnum, src, pidx, act, note in result.get('page_log', []):
        short_name = src if len(src) <= 25 else src[:22] + "..."
        detail = act
        if note:
            detail = act + " " + note
        
        # 根据操作类型设置颜色
        if act == '已旋转':
            color = '#4CAF50'  # 绿色
        elif act == '已正确':
            color = '#2196F3'  # 蓝色
        elif act == '封面跳过':
            color = '#FF9800'  # 橙色
        else:
            color = '#757575'  # 灰色
        
        rows += """
        <tr>
            <td>%d</td>
            <td>%s</td>
            <td>第%d页</td>
            <td style="color:%s;font-weight:bold">%s</td>
        </tr>""" % (pnum, short_name, pidx, color, detail)
    
    # 生成HTML内容
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>图纸定向工具 - 处理报告</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 20px 0;
        }
        .stat-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-box h3 {
            margin: 0;
            color: #666;
            font-size: 14px;
        }
        .stat-box p {
            margin: 5px 0 0;
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #2196F3;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>图纸定向工具 - 处理报告</h1>
        
        <div class="summary">
            <div class="stat-box">
                <h3>总页数</h3>
                <p>%d</p>
            </div>
            <div class="stat-box">
                <h3>图纸旋转</h3>
                <p style="color:#4CAF50">%d</p>
            </div>
            <div class="stat-box">
                <h3>已正确</h3>
                <p style="color:#2196F3">%d</p>
            </div>
            <div class="stat-box">
                <h3>封面跳过</h3>
                <p style="color:#FF9800">%d</p>
            </div>
        </div>
        
        <p><strong>处理时间:</strong> %.1f 秒 | <strong>源文件:</strong> %d 个 | <strong>生成时间:</strong> %s</p>
        
        <table>
            <thead>
                <tr>
                    <th>页序</th>
                    <th>来源文件</th>
                    <th>页码</th>
                    <th>处理结果</th>
                </tr>
            </thead>
            <tbody>
                %s
            </tbody>
        </table>
        
        <div class="footer">
            图纸定向工具 v%s | 生成时间: %s
        </div>
    </div>
</body>
</html>""" % (
        result['total'],
        result['rotated'],
        result['skipped'],
        result.get('cover', 0),
        elapsed,
        result['files'],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        rows,
        __version__,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # 写入文件
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return report_path
