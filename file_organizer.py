import os
import shutil
import json
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter import ttk

# ---------- 整理逻辑 ----------
FILE_CATEGORIES = {
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico"],
    "文档": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".md", ".rtf"],
    "视频": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
    "音乐": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "代码": [".py", ".js", ".html", ".css", ".cpp", ".java", ".json", ".xml", ".yaml", ".sh"],
    "可执行文件": [".exe", ".msi", ".bat", ".cmd", ".app"],
    "其他": []  # 兜底
}

def get_category_by_ext(file_path):
    ext = Path(file_path).suffix.lower()
    for cat, exts in FILE_CATEGORIES.items():
        if ext in exts:
            return cat
    return "其他"

def organize_by_type(src_dir, dest_dir, method="move", log=None):
    """按类型整理，返回(成功移动/复制列表, 错误列表)"""
    files_moved = []
    errors = []
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    for entry in os.scandir(src_dir):
        if entry.is_file():
            try:
                cat = get_category_by_type(entry.path) if method != "date" else None
                # 此项仅为兼容，实际在UI中调用时分别处理，这里定义一个整合函数
            except Exception as e:
                errors.append((entry.path, str(e)))
    return files_moved, errors

# 主整理函数
def organize_by_type_real(src_dir, dest_root, method="move"):
    files_moved = []  # (src, dest)
    errors = []
    for entry in os.scandir(src_dir):
        if entry.is_file():
            try:
                cat = get_category_by_ext(entry.path)
                dest_folder = os.path.join(dest_root, cat)
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                dest_path = os.path.join(dest_folder, entry.name)
                # 避免重名冲突
                base, ext = os.path.splitext(entry.name)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                    counter += 1
                if method == "move":
                    shutil.move(entry.path, dest_path)
                else:
                    shutil.copy2(entry.path, dest_path)
                files_moved.append((entry.path, dest_path))
            except Exception as e:
                errors.append((entry.path, str(e)))
    return files_moved, errors

def organize_by_date(src_dir, dest_root, date_format="%Y-%m", method="move"):
    files_moved = []
    errors = []
    for entry in os.scandir(src_dir):
        if entry.is_file():
            try:
                mtime = os.path.getmtime(entry.path)
                dt = datetime.fromtimestamp(mtime)
                folder_name = dt.strftime(date_format)
                dest_folder = os.path.join(dest_root, folder_name)
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                dest_path = os.path.join(dest_folder, entry.name)
                base, ext = os.path.splitext(entry.name)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                    counter += 1
                if method == "move":
                    shutil.move(entry.path, dest_path)
                else:
                    shutil.copy2(entry.path, dest_path)
                files_moved.append((entry.path, dest_path))
            except Exception as e:
                errors.append((entry.path, str(e)))
    return files_moved, errors

# ---------- UI ----------
class FileOrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("智能文件夹整理工具")
        self.geometry("900x700")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.source_dir = ""
        self.dest_dir = ""   # 默认同源目录，可自定义
        self.undo_data = None
        self.preview_data = None

        self.create_widgets()

    def create_widgets(self):
        # 主框架
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 顶部标题
        title_label = ctk.CTkLabel(self, text="📁 智能文件夹整理工具", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.grid(row=0, column=0, pady=20, padx=20, sticky="w")

        # 设置区域
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        # 源文件夹
        ctk.CTkLabel(settings_frame, text="源文件夹：").grid(row=0, column=0, padx=15, pady=(15,5), sticky="w")
        self.source_entry = ctk.CTkEntry(settings_frame, placeholder_text="选择需要整理的文件夹")
        self.source_entry.grid(row=0, column=1, padx=(0,10), pady=(15,5), sticky="ew")
        ctk.CTkButton(settings_frame, text="浏览", width=80, command=self.browse_source).grid(row=0, column=2, padx=(0,15), pady=(15,5))

        # 目标文件夹（可选）
        ctk.CTkLabel(settings_frame, text="目标根目录：").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.dest_entry = ctk.CTkEntry(settings_frame, placeholder_text="留空则整理到源文件夹内子文件夹")
        self.dest_entry.grid(row=1, column=1, padx=(0,10), pady=5, sticky="ew")
        ctk.CTkButton(settings_frame, text="浏览", width=80, command=self.browse_dest).grid(row=1, column=2, padx=(0,15), pady=5)

        # 整理模式
        ctk.CTkLabel(settings_frame, text="整理方式：").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.mode_var = ctk.StringVar(value="type")
        mode_frame = ctk.CTkFrame(settings_frame)
        mode_frame.grid(row=2, column=1, columnspan=2, pady=5, sticky="w")
        ctk.CTkRadioButton(mode_frame, text="按文件类型", variable=self.mode_var, value="type").pack(side="left", padx=10)
        ctk.CTkRadioButton(mode_frame, text="按修改日期", variable=self.mode_var, value="date").pack(side="left", padx=10)

        # 日期格式（仅日期模式激活）
        self.date_format_var = ctk.StringVar(value="%Y-%m")
        self.date_format_menu = ctk.CTkOptionMenu(settings_frame, values=["%Y-%m (年-月)", "%Y-%m-%d (年-月-日)"],
                                                variable=self.date_format_var, width=200)
        self.date_format_menu.grid(row=3, column=1, pady=5, padx=(0,10), sticky="w")
        ctk.CTkLabel(settings_frame, text="日期子文件夹格式：").grid(row=3, column=0, padx=15, pady=5, sticky="w")
        # 这里需要转换一下显示值
        self.date_format_menu.configure(command=self.on_date_format_change)
        self.date_format_map = {"%Y-%m (年-月)": "%Y-%m", "%Y-%m-%d (年-月-日)": "%Y-%m-%d"}
        self.date_format_var.set("%Y-%m")  # actual format

        # 操作类型
        ctk.CTkLabel(settings_frame, text="操作方式：").grid(row=4, column=0, padx=15, pady=5, sticky="w")
        self.method_var = ctk.StringVar(value="move")
        method_frame = ctk.CTkFrame(settings_frame)
        method_frame.grid(row=4, column=1, columnspan=2, pady=5, sticky="w")
        ctk.CTkRadioButton(method_frame, text="移动", variable=self.method_var, value="move").pack(side="left", padx=10)
        ctk.CTkRadioButton(method_frame, text="复制", variable=self.method_var, value="copy").pack(side="left", padx=10)

        # 按钮行
        button_frame = ctk.CTkFrame(settings_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20, padx=15, sticky="ew")
        ctk.CTkButton(button_frame, text="🔍 预览整理效果", width=160, command=self.preview_organize).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="⚡ 开始整理", width=160, fg_color="#28a745", hover_color="#218838", command=self.start_organize).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="↩️ 撤销上一次整理", width=160, fg_color="#ffc107", hover_color="#e0a800", command=self.undo_last).pack(side="left", padx=5)

        # 预览/结果区域
        self.preview_text = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=13))
        self.preview_text.grid(row=2, column=0, padx=20, pady=(0,10), sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        # 进度条
        self.progress = ctk.CTkProgressBar(self, width=500)
        self.progress.grid(row=3, column=0, padx=20, pady=(0,10), sticky="ew")
        self.progress.set(0)

        # 状态栏
        self.status_label = ctk.CTkLabel(self, text="就绪", anchor="w")
        self.status_label.grid(row=4, column=0, padx=20, pady=(0,10), sticky="ew")

    def on_date_format_change(self, choice):
        actual_format = self.date_format_map.get(choice, "%Y-%m")
        self.date_format_var.set(actual_format)

    def browse_source(self):
        path = filedialog.askdirectory(title="选择要整理的文件夹")
        if path:
            self.source_entry.delete(0, "end")
            self.source_entry.insert(0, path)
            self.source_dir = path

    def browse_dest(self):
        path = filedialog.askdirectory(title="选择目标根文件夹（可选）")
        if path:
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, path)

    def get_source_dir(self):
        src = self.source_entry.get().strip()
        if not src or not os.path.isdir(src):
            messagebox.showerror("错误", "请先选择有效的源文件夹")
            return None
        return src

    def get_dest_root(self):
        dest = self.dest_entry.get().strip()
        if dest and not os.path.isdir(dest):
            messagebox.showerror("错误", "目标根目录无效")
            return None
        if not dest:
            dest = self.get_source_dir()  # 默认源目录
        return dest

    def preview_organize(self):
        src = self.get_source_dir()
        if not src: return
        dest_root = self.dest_entry.get().strip() or src
        mode = self.mode_var.get()
        date_format = self.date_format_var.get() if mode == "date" else None

        self.preview_text.delete("1.0", "end")
        self.status_label.configure(text="正在扫描...")
        self.update()

        # 在后台线程扫描
        def scan():
            preview_lines = []
            files_by_dest = defaultdict(list)
            errors = []
            for entry in os.scandir(src):
                if entry.is_file():
                    try:
                        if mode == "type":
                            cat = get_category_by_ext(entry.path)
                            dest_folder = os.path.join(dest_root, cat)
                        else:
                            mtime = os.path.getmtime(entry.path)
                            dt = datetime.fromtimestamp(mtime)
                            folder_name = dt.strftime(date_format)
                            dest_folder = os.path.join(dest_root, folder_name)
                        files_by_dest[dest_folder].append(entry.name)
                    except Exception as e:
                        errors.append(f"❌ 读取错误 {entry.name}: {e}")
            total_files = sum(len(v) for v in files_by_dest.values())
            for folder, names in files_by_dest.items():
                preview_lines.append(f"📂 {folder}/")
                for n in sorted(names)[:20]:  # 每类最多显示20个
                    preview_lines.append(f"   ↳ {n}")
                if len(names) > 20:
                    preview_lines.append(f"   ... 还有 {len(names)-20} 个文件")
                preview_lines.append("")
            if errors:
                preview_lines.append("⚠️ 错误:")
                preview_lines.extend(errors)
            preview_text = "\n".join(preview_lines) if preview_lines else "没有文件需要整理。"
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", preview_text)
            self.status_label.configure(text=f"扫描完成，共 {total_files} 个文件")
            self.preview_data = {"mode": mode, "date_format": date_format, "files_by_dest": files_by_dest, "total": total_files}
        threading.Thread(target=scan, daemon=True).start()

    def start_organize(self):
        src = self.get_source_dir()
        if not src: return
        dest_root = self.get_dest_root()
        if not dest_root: return
        method = self.method_var.get()
        mode = self.mode_var.get()
        date_format = self.date_format_var.get() if mode == "date" else None

        confirm = messagebox.askyesno("确认整理", f"将按{mode}方式{method}文件。\n源: {src}\n目标根: {dest_root}\n\n确认执行吗？")
        if not confirm:
            return

        self.progress.set(0)
        self.status_label.configure(text="正在整理...")
        self.preview_text.delete("1.0", "end")
        self.update()

        def run():
            if mode == "type":
                moved, errors = organize_by_type_real(src, dest_root, method)
            else:
                moved, errors = organize_by_date(src, dest_root, date_format, method)

            # 保存撤销日志
            undo_info = {
                "method": method,
                "moved": moved,
                "errors": errors,
                "time": datetime.now().isoformat()
            }
            with open("undo_log.json", "w", encoding="utf-8") as f:
                json.dump(undo_info, f, ensure_ascii=False, indent=2)
            self.undo_data = moved  # 仅保存成功的移动记录

            # 显示结果
            result_text = []
            if moved:
                result_text.append(f"✅ 成功 {method} {len(moved)} 个文件:")
                for src_p, dst_p in moved[:30]:
                    result_text.append(f"  {os.path.basename(src_p)} -> {os.path.dirname(dst_p)}")
                if len(moved) > 30:
                    result_text.append(f"  ... 还有 {len(moved)-30} 个")
            if errors:
                result_text.append(f"❌ 错误 {len(errors)}:")
                for p, e in errors[:10]:
                    result_text.append(f"  {os.path.basename(p)}: {e}")
            if not moved and not errors:
                result_text.append("没有文件被整理。")

            self.progress.set(1)
            self.status_label.configure(text="整理完成")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "\n".join(result_text))

        threading.Thread(target=run, daemon=True).start()
        # 模拟进度
        self.animate_progress()

    def animate_progress(self):
        for i in range(0, 101, 5):
            self.progress.set(i / 100)
            self.update()
            self.after(50)
        self.progress.set(1)

    def undo_last(self):
        if not os.path.exists("undo_log.json"):
            messagebox.showinfo("无操作", "没有可撤销的整理记录。")
            return
        with open("undo_log.json", "r", encoding="utf-8") as f:
            undo_info = json.load(f)
        moved = undo_info.get("moved", [])
        if not moved:
            messagebox.showinfo("无操作", "没有可撤销的移动记录。")
            return
        confirm = messagebox.askyesno("撤销确认", f"将撤销 {len(moved)} 个文件的移动/复制操作。\n确定要恢复到原来位置吗？")
        if not confirm:
            return

        self.status_label.configure(text="正在撤销...")
        self.update()
        success = 0
        errors = []
        for src, dest in moved:
            try:
                if os.path.exists(dest):
                    # 如果是复制，原文件应该还在src；如果是移动，源已不存在
                    if undo_info["method"] == "move":
                        shutil.move(dest, src)
                    else:
                        # 复制模式：删除目标文件
                        os.remove(dest)
                    success += 1
                else:
                    errors.append(f"文件不存在: {dest}")
            except Exception as e:
                errors.append(f"{dest}: {e}")
        # 清除日志
        os.remove("undo_log.json")
        self.undo_data = None
        result = f"✅ 成功撤销 {success} 个文件。"
        if errors:
            result += f"\n❌ 失败 {len(errors)}: " + "; ".join(errors[:5])
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", result)
        self.status_label.configure(text="撤销完成")

if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()