#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸定向工具 - 图形用户界面
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from .config import __version__
from .utils import collect_pdf_files, get_output_dir


class DrawingToolGUI:
    """图纸定向工具主窗口"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"图纸定向工具 v{__version__}")
        self.root.geometry("750x650")
        self.root.minsize(650, 550)
        self.root.resizable(True, True)
        
        # 设置图标（如果有的话）
        try:
            self.root.iconbitmap(default=None)
        except:
            pass
        
        # 变量
        self.folder_path = tk.StringVar()
        self.mode = tk.StringVar(value="merge")
        self.is_processing = False
        
        # 创建界面
        self._create_widgets()
        
        # 居中显示
        self._center_window()
    
    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_widgets(self):
        """创建所有界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== 标题区域 =====
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            title_frame,
            text="📐 图纸定向工具",
            font=("微软雅黑", 20, "bold")
        ).pack()
        
        ttk.Label(
            title_frame,
            text="自动旋转PDF图纸，让图签统一到底部",
            font=("微软雅黑", 10),
            foreground="gray"
        ).pack()
        
        # ===== 文件夹选择区域 =====
        folder_frame = ttk.LabelFrame(main_frame, text=" 📁 选择文件夹 ", padding="15")
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 路径输入框
        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill=tk.X)
        
        self.path_entry = ttk.Entry(
            path_frame,
            textvariable=self.folder_path,
            font=("微软雅黑", 11),
            state="readonly"
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.browse_btn = ttk.Button(
            path_frame,
            text="浏览...",
            command=self._browse_folder,
            width=10
        )
        self.browse_btn.pack(side=tk.RIGHT)
        
        # 文件信息
        self.file_info = ttk.Label(
            folder_frame,
            text="请选择包含PDF文件的文件夹",
            foreground="gray",
            font=("微软雅黑", 9)
        )
        self.file_info.pack(anchor=tk.W, pady=(10, 0))
        
        # ===== 选项区域 =====
        options_frame = ttk.LabelFrame(main_frame, text=" ⚙️ 处理选项 ", padding="15")
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 模式选择
        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(fill=tk.X)
        
        ttk.Radiobutton(
            mode_frame,
            text="📄 合并为一个PDF（推荐）",
            variable=self.mode,
            value="merge"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            mode_frame,
            text="📁 保留独立文件",
            variable=self.mode,
            value="individual"
        ).pack(anchor=tk.W)
        
        # ===== 按钮区域 =====
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.preview_btn = ttk.Button(
            btn_frame,
            text="👀 预览",
            command=self._preview,
            width=15,
            state="disabled"
        )
        self.preview_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.start_btn = ttk.Button(
            btn_frame,
            text="🚀 开始处理",
            command=self._start_process,
            width=15,
            state="disabled"
        )
        self.start_btn.pack(side=tk.LEFT)
        
        # ===== 进度区域 =====
        progress_frame = ttk.LabelFrame(main_frame, text=" 📊 处理进度 ", padding="15")
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            progress_frame,
            text="等待开始...",
            font=("微软雅黑", 10)
        )
        self.status_label.pack(anchor=tk.W)
        
        # ===== 日志区域 =====
        log_frame = ttk.LabelFrame(main_frame, text=" 📋 处理日志 ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = tk.Text(
            log_frame,
            height=10,
            font=("Consolas", 10),
            state="disabled",
            wrap=tk.WORD,
            bg="#f8f8f8"
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ===== 底部信息 =====
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            bottom_frame,
            text="💡 提示：将PDF文件夹拖拽到路径框即可快速选择",
            foreground="gray",
            font=("微软雅黑", 9)
        ).pack(side=tk.LEFT)
        
        # 支持拖拽
        self.root.drop_target_register = None  # 需要tkinterdnd2支持
    
    def _browse_folder(self):
        """浏览并选择文件夹"""
        folder = filedialog.askdirectory(title="选择包含PDF文件的文件夹")
        if folder:
            self.folder_path.set(folder)
            self._update_file_info(folder)
            self._update_buttons(True)
    
    def _update_file_info(self, folder):
        """更新文件信息显示"""
        try:
            pdf_files = collect_pdf_files(folder)
            count = len(pdf_files)
            if count > 0:
                self.file_info.config(
                    text=f"✓ 找到 {count} 个PDF文件",
                    foreground="green"
                )
            else:
                self.file_info.config(
                    text="✗ 该文件夹中没有PDF文件",
                    foreground="red"
                )
                self._update_buttons(False)
        except Exception as e:
            self.file_info.config(
                text=f"✗ 无法访问文件夹: {e}",
                foreground="red"
            )
            self._update_buttons(False)
    
    def _update_buttons(self, enabled):
        """更新按钮状态"""
        state = "normal" if enabled else "disabled"
        self.preview_btn.config(state=state)
        self.start_btn.config(state=state)
    
    def _preview(self):
        """预览模式"""
        self._start_process(dry_run=True)
    
    def _start_process(self, dry_run=False):
        """开始处理"""
        if self.is_processing:
            return
        
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("提示", "请先选择文件夹！")
            return
        
        self.is_processing = True
        self._update_buttons(False)
        self.progress_bar['value'] = 0
        
        # 在新线程中处理
        thread = threading.Thread(
            target=self._process_worker,
            args=(folder, dry_run),
            daemon=True
        )
        thread.start()
    
    def _process_worker(self, folder, dry_run):
        """处理工作线程"""
        try:
            if dry_run:
                self._log("开始预览分析...")
                self._run_preview(folder)
            else:
                self._log("开始处理...")
                self._run_process(folder)
        except Exception as e:
            self._log(f"错误: {e}")
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self._update_buttons(True))
    
    def _run_preview(self, folder):
        """执行预览"""
        import fitz
        from .core import calc_new_rotation
        
        pdf_files = collect_pdf_files(folder)
        total_pages = 0
        will_rotate = 0
        will_skip = 0
        will_cover = 0
        
        self.root.after(0, lambda: self.status_label.config(text="正在分析..."))
        
        for idx, pdf_path in enumerate(pdf_files):
            name = os.path.basename(pdf_path)
            self._log(f"[{idx+1}/{len(pdf_files)}] 分析: {name}")
            
            try:
                doc = fitz.open(pdf_path)
            except Exception as e:
                self._log(f"  无法打开: {e}")
                continue
            
            for i in range(doc.page_count):
                pg = doc[i]
                new_rot, action, info = calc_new_rotation(pg)
                total_pages += 1
                
                if action == '封面跳过':
                    will_cover += 1
                elif action == '已正确':
                    will_skip += 1
                elif action == '已旋转':
                    will_rotate += 1
                
                # 更新进度
                progress = (idx * 100 + (i + 1) * 100 / doc.page_count) / len(pdf_files)
                self.root.after(0, lambda p=progress: self.progress_bar.configure(value=p))
            
            doc.close()
        
        # 显示结果
        self._log("\n" + "=" * 40)
        self._log("【预览结果】")
        self._log(f"  总页数: {total_pages}")
        self._log(f"  需要旋转: {will_rotate} 页")
        self._log(f"  已正确: {will_skip} 页")
        self._log(f"  封面跳过: {will_cover} 页")
        self._log("=" * 40)
        
        self.root.after(0, lambda: self.status_label.config(text="预览完成！"))
        self.root.after(0, lambda: self.progress_bar.configure(value=100))
        self.root.after(100, lambda: messagebox.showinfo(
            "预览完成",
            f"分析完成！\n\n总页数: {total_pages}\n需要旋转: {will_rotate} 页\n已正确: {will_skip} 页\n封面跳过: {will_cover} 页\n\n详细信息请查看下方日志区域"
        ))
    
    def _run_process(self, folder):
        """执行处理"""
        from .file_handler import process
        from .utils import format_file_size
        
        mode = self.mode.get()
        
        # 更新状态
        self.root.after(0, lambda: self.status_label.config(text="正在处理..."))
        
        # 执行处理
        result = process(folder, mode)
        
        # 显示结果
        self._log("\n" + "=" * 40)
        self._log("【处理完成】")
        self._log(f"  总页数: {result['total']}")
        self._log(f"  图纸旋转: {result['rotated']} 页")
        self._log(f"  已正确: {result['skipped']} 页")
        self._log(f"  封面跳过: {result.get('cover', 0)} 页")
        self._log(f"\n输出目录: {result['output_dir']}")
        
        for fp in result.get('output_files', []):
            sz = os.path.getsize(fp)
            self._log(f"  → {os.path.basename(fp)} ({format_file_size(sz)})")
        
        self._log("=" * 40)
        
        # 更新UI
        self.root.after(0, lambda: self.status_label.config(text="处理完成！"))
        self.root.after(0, lambda: self.progress_bar.configure(value=100))
        
        # 询问是否打开输出目录
        self.root.after(100, lambda: self._ask_open_folder(result['output_dir']))
    
    def _ask_open_folder(self, folder):
        """询问是否打开输出目录"""
        if messagebox.askyesno("完成", "处理完成！是否打开输出文件夹？"):
            os.startfile(folder) if os.name == 'nt' else os.system(f'open "{folder}"')
    
    def _log(self, message):
        """添加日志消息"""
        def _update():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _update)
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """启动GUI"""
    app = DrawingToolGUI()
    app.run()


if __name__ == '__main__':
    main()
