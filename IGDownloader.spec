# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
将 Instagram 监控脚本打包成独立的 Windows 可执行文件
"""

import sys
from pathlib import Path

# 项目根目录
project_root = Path(SPECPATH)

# 分析配置
a = Analysis(
    ['instagram_monitor.py'],  # 主脚本
    pathex=[str(project_root)],  # Python 路径
    binaries=[
        # 打包 gallery-dl 可执行文件（从项目根目录的虚拟环境）
        ('..\\venv\\Scripts\\gallery-dl.exe', '.'),
    ],
    datas=[
        # 打包 README 文件
        ('README.md', '.'),
    ],
    hiddenimports=[
        # 隐式导入的模块
        'pysocks',
        'socks',  # pysocks 的别名
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 去除重复文件
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IGDownloader',  # 可执行文件名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用 UPX 压缩（如果安装了 UPX）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口（因为是命令行程序）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 图标（可选）
    # icon='icon.ico',
)
