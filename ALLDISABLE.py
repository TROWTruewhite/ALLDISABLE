import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import time

class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.last_modified = {}

    def on_created(self, event):
        if not event.is_directory:
            self._process_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.app.remove_from_file_list(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.app.remove_from_file_list(event.src_path)
            self._process_file(event.dest_path)

    def _process_file(self, file_path):
        # 防止重复处理
        current_time = time.time()
        if file_path in self.last_modified and current_time - self.last_modified[file_path] < 0.5:
            return
        self.last_modified[file_path] = current_time

        # 检查是否应该添加到文件列表
        if self.app.should_include_file(file_path):
            self.app.add_to_file_list(file_path)

class AllDisableApp:
    def __init__(self, root):
        self.root = root
        self.root.title('文件一键禁用工具')
        self.root.geometry('400x300')
        try:
            self.root.iconbitmap('barrier.ico')  # 尝试加载当前目录下的图标
        except:
            try:
                # 如果当前目录没有，尝试从程序所在目录加载
                icon_path = Path(__file__).parent / 'barrier.ico'
                self.root.iconbitmap(str(icon_path))
            except:
                pass  # 如果都找不到，就忽略图标设置

        # 获取程序自身路径和文件名
        self.program_path = Path(sys.executable if getattr(sys, 'frozen', False) else __file__)
        self.program_name = self.program_path.name

        # 配置文件路径
        self.config_dir = Path(os.environ.get('APPDATA', '')) / 'TIME-TW' / 'ALLDISABLE'
        self.config_file = self.config_dir / 'config.json'

        # 初始化数据
        self.file_list = []
        self.excluded_extensions = {}
        self.excluded_files = []
        self.monitoring = False

        # 加载配置
        self.load_config()

        # 检查命令行参数
        self.check_command_line_args()

        # 创建UI
        self.create_widgets()

        # 启动文件监控
        self.start_monitoring()

    def check_command_line_args(self):
        # 如果有命令行参数，处理文件并退出
        if len(sys.argv) > 1:
            target_file = Path(sys.argv[1])
            if target_file.exists() and not target_file.is_dir():
                self.toggle_file_status(target_file)
            sys.exit(0)

    def toggle_file_status(self, file_path):
        '''切换单个文件的禁用状态'''
        if file_path.suffix == '.disabled':
            # 启用文件
            new_path = file_path.with_suffix('')
            file_path.rename(new_path)
        else:
            # 禁用文件
            new_path = file_path.with_suffix(file_path.suffix + '.disabled')
            file_path.rename(new_path)
    
    def showabout(self):
        abtroot = tk.Tk()
        abtroot.geometry('500x100')
        abtroot.title('关于')
        abtroot.resizable(False, False)
        try:
            self.root.iconbitmap('barrier.ico')  # 尝试加载当前目录下的图标
        except:
            try:
                # 如果当前目录没有，尝试从程序所在目录加载
                icon_path = Path(__file__).parent / 'barrier.ico'
                abtroot.iconbitmap(str(icon_path))
            except:
                pass  # 如果都找不到，就忽略图标设置

        ttk.Label(
            abtroot,
            text='''一键禁用工具
版本：Release 1.0
作者：True_white_
github仓库：https://github.com/TROWTruewhite/ALLDISABLE''',
            font=('微软雅黑', 12)
        ).pack(side=tk.LEFT)
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding='20')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text='文件一键禁用工具', font=('SimHei', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # 菜单
        menu_bar = tk.Menu(self.root)
        menu_bar.add_command(label='关于', command=lambda: self.showabout())
        menu_bar.add_command(label='退出', command=lambda: self.root.destroy())
        self.root.config(menu=menu_bar)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        # 禁用按钮
        self.disable_btn = ttk.Button(button_frame, text='一键禁用[f8]', command=self.disable_all_files)
        self.disable_btn.pack(side=tk.LEFT, padx=5, expand=True)
        self.root.bind('<F8>', lambda event: self.disable_btn.invoke())

        # 启用按钮
        self.enable_btn = ttk.Button(button_frame, text='一键启用[f9]', command=self.enable_all_files)
        self.enable_btn.pack(side=tk.LEFT, padx=5, expand=True)
        self.root.bind('<F9>', lambda event: self.enable_btn.invoke())

        # 设置按钮
        self.settings_btn = ttk.Button(button_frame, text='设置', command=self.open_settings)
        self.settings_btn.pack(side=tk.LEFT, padx=5, expand=True)

        # 文件列表框
        list_frame = ttk.LabelFrame(main_frame, text='监控文件列表')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.file_listbox.yview)

    def start_monitoring(self):
        '''启动文件监控'''
        if not self.monitoring:
            self.event_handler = FileMonitorHandler(self)
            self.observer = Observer()
            self.observer.schedule(self.event_handler, str(self.program_path.parent), recursive=False)
            # 初始扫描目录
        self.scan_directory()
        self.observer.start()
        self.monitoring = True

    def scan_directory(self):
        '''扫描目录并添加初始文件'''
        self.file_list = []
        self.file_listbox.delete(0, tk.END)

        for item in self.program_path.parent.iterdir():
            if item.is_file() and self.should_include_file(str(item)):
                self.add_to_file_list(str(item))

    def should_include_file(self, file_path):
        '''检查文件是否应该包含在禁用列表中'''
        file_name = Path(file_path).name

        # 排除程序本身
        if file_name == self.program_name:
            return False

        # 排除已禁用的文件
        if file_name.endswith('.disabled'):
            return False

        # 检查是否在单独排除文件列表中
        if file_path in self.excluded_files:
            return False

        # 排除配置中勾选的后缀名
        ext = Path(file_path).suffix.lower()
        if ext and ext in self.excluded_extensions and self.excluded_extensions[ext]:
            return False

        return True

    def add_to_file_list(self, file_path):
        '''添加文件到列表'''
        if file_path not in self.file_list:
            self.file_list.append(file_path)
            file_name = Path(file_path).name
            self.file_listbox.insert(tk.END, file_name)

    def remove_from_file_list(self, file_path):
        '''从列表中移除文件'''
        if file_path in self.file_list:
            index = self.file_list.index(file_path)
            self.file_list.pop(index)
            self.file_listbox.delete(index)

    def disable_all_files(self):
        '''禁用所有监控文件'''
        count = 0
        for file_path in self.file_list.copy():
            try:
                path = Path(file_path)
                new_path = path.with_suffix(path.suffix + '.disabled')
                path.rename(new_path)
                count += 1
                self.remove_from_file_list(file_path)
            except Exception as e:
                messagebox.showerror('错误', f'无法禁用文件 {path.name}: {str(e)}')
        messagebox.showinfo('完成', f'已成功禁用 {count} 个文件')

    def enable_all_files(self):
        '''启用所有.disabled文件'''
        count = 0
        for item in self.program_path.parent.iterdir():
            if item.is_file() and item.suffix == '.disabled':
                try:
                    new_path = item.with_suffix('')
                    item.rename(new_path)
                    count += 1
                except Exception as e:
                    messagebox.showerror('错误', f'无法启用文件 {item.name}: {str(e)}')
        self.scan_directory()  # 重新扫描目录以更新文件列表
        messagebox.showinfo('完成', f'已成功启用 {count} 个文件')

    def load_config(self):
        '''加载配置文件'''
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.excluded_extensions = config.get('excluded_extensions', {})
                    self.excluded_files = config.get('excluded_files', [])
            else:
                # 默认排除一些常见系统文件后缀
                self.excluded_extensions = {
                    '.txt': False,
                    '.log': False,
                    '.ini': False,
                    '.config': False,
                    '.py': True,  # 默认排除Python文件
                    '.pyc': True
                }
                self.excluded_files = []
                self.save_config()
        except Exception as e:
            messagebox.showerror('配置错误', f'加载配置失败: {str(e)}使用默认配置')
            self.excluded_extensions = {'.txt': False, '.log': False, '.ini': False}
            self.excluded_files = []

    def save_config(self):
        '''保存配置文件'''
        try:
            # 确保目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'excluded_extensions': self.excluded_extensions,
                    'excluded_files': self.excluded_files
                }, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            messagebox.showerror('保存错误', f'保存配置失败: {str(e)}')
            return False

    def open_settings(self):
        '''打开设置窗口'''
        settings_window = tk.Toplevel(self.root)
        settings_window.title('设置')
        settings_window.geometry('400x400')
        settings_window.resizable(True, True)
        settings_window.transient(self.root)
        settings_window.grab_set()
        try:
            self.root.iconbitmap('barrier.ico')  # 尝试加载当前目录下的图标
        except:
            try:
                # 如果当前目录没有，尝试从程序所在目录加载
                icon_path = Path(__file__).parent / 'barrier.ico'
                settings_window.iconbitmap(str(icon_path))
            except:
                pass  # 如果都找不到，就忽略图标设置

        # 创建主滚动区域
        canvas = tk.Canvas(settings_window)
        scrollbar = ttk.Scrollbar(settings_window, orient='vertical', command=canvas.yview)
        content_frame = ttk.Frame(canvas)

        content_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 创建主框架
        main_frame = ttk.Frame(content_frame, padding='10')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text='后缀名屏蔽设置', font=('SimHei', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        # 添加新后缀名的框架
        new_ext_frame = ttk.Frame(main_frame)
        new_ext_frame.pack(fill=tk.X, pady=10)

        ttk.Label(new_ext_frame, text='添加新后缀名:').pack(side=tk.LEFT, padx=5)
        self.new_ext_entry = ttk.Entry(new_ext_frame)
        self.new_ext_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.new_ext_button = ttk.Button(new_ext_frame, text='添加', command=lambda: self.add_new_extension(settings_window, checkboxes_frame))
        self.new_ext_button.pack(side=tk.LEFT, padx=5)
        self.new_ext_entry.bind('<Return>', lambda event: self.new_ext_button.invoke())

        # 后缀名复选框框架
        checkboxes_frame = ttk.Frame(main_frame)
        checkboxes_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # 存储复选框变量
        self.checkbox_vars = {}

        # 添加现有后缀名复选框和删除按钮
        for ext, checked in self.excluded_extensions.items():
            ext_frame = ttk.Frame(checkboxes_frame)
            ext_frame.pack(anchor='w', pady=2, fill=tk.X)

            var = tk.BooleanVar(value=checked)
            self.checkbox_vars[ext] = var
            cb = ttk.Checkbutton(ext_frame, text=ext, variable=var)
            cb.pack(side=tk.LEFT)

            # 删除按钮
            delete_btn = ttk.Button(ext_frame, text='删除', command=lambda e=ext: self.remove_extension(settings_window, e))
            delete_btn.pack(side=tk.LEFT, padx=5)


        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text='保存', command=lambda: self.save_settings(settings_window)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text='取消', command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)

    def remove_extension(self, settings_window, ext):
        '''删除后缀名'''
        if ext in self.excluded_extensions:
            del self.excluded_extensions[ext]
            if ext in self.checkbox_vars:
                del self.checkbox_vars[ext]
            self.save_config()
            # 刷新设置窗口
            settings_window.destroy()
            self.open_settings()

    def add_new_extension(self, settings_window, parent_frame):
        '''添加新的后缀名'''
        ext = self.new_ext_entry.get().strip().lower()
        if not ext:
            messagebox.showwarning('警告', '请输入后缀名')
            return

        # 确保以点开头
        if not ext.startswith('.'):
            ext = '.' + ext

        if ext in self.checkbox_vars:
            messagebox.showinfo('提示', f'后缀名 {ext} 已存在')
            return

        # 添加到配置和界面
        var = tk.BooleanVar(value=True)
        self.checkbox_vars[ext] = var
        cb = ttk.Checkbutton(parent_frame, text=ext, variable=var)
        cb.pack(anchor='w', pady=2)

        # 清空输入框
        self.new_ext_entry.delete(0, tk.END)

    def save_settings(self, settings_window):
        '''保存设置'''
        # 更新配置
        for ext, var in self.checkbox_vars.items():
            self.excluded_extensions[ext] = var.get()

        # 保存并刷新文件列表
        if self.save_config():
            self.scan_directory()
            settings_window.destroy()
            messagebox.showinfo('成功', '设置已保存')

    def on_closing(self):
        '''窗口关闭时的处理'''
        if self.monitoring:
            self.observer.stop()
            self.observer.join()
        self.root.destroy()

if __name__ == '__main__':
    # 确保中文显示正常
    root = tk.Tk()
    app = AllDisableApp(root)
    root.protocol('WM_DELETE_WINDOW', app.on_closing)
    root.mainloop()