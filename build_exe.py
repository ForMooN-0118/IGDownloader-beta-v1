#!/usr/bin/env python3
"""
一键打包脚本
将 Instagram 监控脚本打包成独立的 Windows 可执行文件
"""

import subprocess
import sys
import shutil
from pathlib import Path


def check_pyinstaller():
    """检查是否安装了 PyInstaller"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller 已安装 (版本: {PyInstaller.__version__})")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装")
        return False


def install_pyinstaller():
    """安装 PyInstaller"""
    print("📦 正在安装 PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e}")
        return False


def clean_build():
    """清理之前的构建文件"""
    print("🧹 清理构建文件...")
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   已删除: {dir_name}")
    
    # 删除 spec 文件（除了我们自定义的）
    for spec_file in Path('.').glob('*.spec'):
        if spec_file.name != 'IGDownloader.spec':
            spec_file.unlink()
            print(f"   已删除: {spec_file.name}")


def build_exe():
    """执行打包"""
    print("\n🔨 开始打包...")
    print("=" * 50)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "IGDownloader.spec",  # 使用自定义 spec 文件
        "--clean",  # 清理临时文件
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 50)
        print("✅ 打包成功！")
        print(f"📁 输出目录: {Path('dist').absolute()}")
        print(f"📄 可执行文件: {Path('dist/IGDownloader.exe').absolute()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False


def show_info():
    """显示打包信息"""
    print("\n📋 打包信息:")
    print("-" * 50)
    print("包含组件:")
    print("  • IGDownloader.exe - 主程序")
    print("  • gallery-dl.exe - 下载工具")
    print("  • Python 运行时")
    print("\n首次运行:")
    print("  1. 选择数据存储目录")
    print("  2. 导入 Instagram cookies")
    print("  3. 添加监控账号")
    print("-" * 50)


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 IGDownloader 打包工具")
    print("=" * 50)
    
    # 检查 PyInstaller
    if not check_pyinstaller():
        if input("是否安装 PyInstaller? (y/n): ").lower() == 'y':
            if not install_pyinstaller():
                sys.exit(1)
        else:
            print("❌ 无法继续，请先安装 PyInstaller")
            sys.exit(1)
    
    # 询问是否清理
    if input("\n是否清理之前的构建文件? (y/n): ").lower() == 'y':
        clean_build()
    
    # 执行打包
    if build_exe():
        show_info()
        
        # 询问是否复制到桌面
        if input("\n是否复制到桌面? (y/n): ").lower() == 'y':
            desktop = Path.home() / "Desktop"
            src = Path("dist/IGDownloader.exe")
            dst = desktop / "IGDownloader.exe"
            if src.exists():
                shutil.copy2(src, dst)
                print(f"✅ 已复制到桌面: {dst}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
