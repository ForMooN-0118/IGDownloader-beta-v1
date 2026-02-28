#!/usr/bin/env python3
"""
Instagram 内容监控脚本 - 扫描测试版本（支持帖子和快拍分别计数）
功能：验证扫描能获取哪些信息
"""

import subprocess
import json
import os
import re
import time
import random
import sys
from datetime import datetime
from pathlib import Path

# ========== 打包环境检测 ==========
def get_gallery_dl_path():
    """
    获取 gallery-dl 可执行文件路径
    支持开发环境和 PyInstaller 打包后的环境
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        # sys._MEIPASS 是 PyInstaller 解压资源的临时目录
        base_path = sys._MEIPASS
        gallery_dl_exe = os.path.join(base_path, "gallery-dl.exe")
        if os.path.exists(gallery_dl_exe):
            return gallery_dl_exe
        # 如果在 _MEIPASS 中找不到，尝试同级目录
        gallery_dl_exe = os.path.join(os.path.dirname(sys.executable), "gallery-dl.exe")
        if os.path.exists(gallery_dl_exe):
            return gallery_dl_exe
    
    # 开发环境：使用虚拟环境中的 gallery-dl
    if os.path.exists("venv\\Scripts\\gallery-dl.exe"):
        return "venv\\Scripts\\gallery-dl.exe"
    
    # 最后尝试系统 PATH 中的 gallery-dl
    return "gallery-dl"

# ========== 管理员权限检查 ==========
def is_admin():
    """检查是否以管理员权限运行"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """请求以管理员权限重新运行"""
    import ctypes
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

# 如果需要管理员权限，取消下面的注释
# if not is_admin():
#     print("需要管理员权限来访问某些目录...")
#     run_as_admin()

import config


def validate_and_fix_path(path_str, path_type='file', create_if_missing=True):
    """
    验证并修复路径
    
    Args:
        path_str: 路径字符串
        path_type: 'file' 或 'dir'
        create_if_missing: 如果不存在是否自动创建
    
    Returns:
        (is_valid, fixed_path, message): 是否有效、修复后的路径、提示信息
    """
    path = Path(path_str)
    
    # 检查路径是否为空
    if not path_str.strip():
        return False, path_str, "路径不能为空"
    
    # 检查是否是保留字（导航命令）
    if path_str.upper() in ['B', 'M', 'Q']:
        return False, path_str, f"'{path_str}' 是导航命令，不能作为路径"
    
    # 如果是文件类型，检查是否有文件名
    if path_type == 'file':
        # 如果路径以分隔符结尾或没有扩展名，可能是目录
        if path_str.endswith(os.sep) or path_str.endswith('/') or path_str.endswith('\\'):
            return False, path_str, "这是一个目录路径，请提供文件路径（例如: D:\\insdownload\\archive.json）"
        
        if not path.suffix:
            # 没有扩展名，可能是目录
            return False, path_str, f"'{path_str}' 看起来是目录，请提供文件路径（例如: {path_str}\\archive.json）"
    
    # 检查路径是否存在
    if path.exists():
        if path_type == 'file' and path.is_dir():
            return False, path_str, f"'{path}' 是目录，但需要的是文件路径"
        if path_type == 'dir' and path.is_file():
            return False, path_str, f"'{path}' 是文件，但需要的是目录路径"
        return True, str(path), "路径有效"
    
    # 路径不存在，尝试创建
    if create_if_missing:
        try:
            if path_type == 'dir':
                path.mkdir(parents=True, exist_ok=True)
                return True, str(path), f"已创建目录: {path}"
            else:
                # 文件类型：先创建父目录，再创建包含默认内容的文件
                parent_dir = path.parent
                if parent_dir and str(parent_dir) != '.':
                    # 确保父目录存在
                    parent_dir.mkdir(parents=True, exist_ok=True)
                
                # 根据文件类型创建相应的内容
                if path.name.endswith('.json'):
                    # JSON 文件：创建包含空对象的内容
                    if 'archive' in path.name.lower():
                        # 存档文件：空对象
                        path.write_text('{}', encoding='utf-8')
                    elif 'account' in path.name.lower():
                        # 账号文件：空数组
                        path.write_text('[]', encoding='utf-8')
                    elif 'setting' in path.name.lower() or 'config' in path.name.lower():
                        # 设置文件：默认配置
                        import json
                        path.write_text(json.dumps(config.DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding='utf-8')
                    else:
                        # 其他 JSON 文件：空对象
                        path.write_text('{}', encoding='utf-8')
                elif 'cookies' in path.name.lower() or path.name.endswith('.txt'):
                    # Cookies 文件：创建空文本文件
                    path.write_text('', encoding='utf-8')
                else:
                    # 其他文件：创建空文件
                    path.touch()
                
                return True, str(path), f"已创建文件: {path}"
        except PermissionError as e:
            # 权限错误，提供友好提示
            error_msg = f"创建路径失败: 权限不足\n"
            error_msg += f"无法创建: {path}\n"
            error_msg += f"\n可能的原因:\n"
            error_msg += f"  • 目标目录需要管理员权限（如 D:\\ 根目录）\n"
            error_msg += f"  • 磁盘被写保护\n"
            error_msg += f"  • 防病毒软件阻止\n"
            error_msg += f"\n建议:\n"
            error_msg += f"  1. 选择用户目录下的路径，如 D:\\MyData\\insdownload\n"
            error_msg += f"  2. 以管理员身份运行程序\n"
            error_msg += f"  3. 手动创建目录后再设置路径"
            return False, path_str, error_msg
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return False, path_str, f"创建路径失败: {e}\n{error_detail}"
    
    # 不自动创建，但检查父目录是否可写
    try:
        parent = path.parent
        if not parent.exists():
            return False, path_str, f"父目录不存在: {parent}"
        # 测试是否可写
        test_file = parent / '.write_test'
        test_file.touch()
        test_file.unlink()
        return True, str(path), "路径有效（父目录可写）"
    except Exception as e:
        return False, path_str, f"路径不可写: {e}"


def ensure_directories_exist():
    """确保所有必要的目录和文件存在"""
    results = []
    
    # 检查下载目录
    download_dir = Path(config.DOWNLOAD_DIR)
    if not download_dir.exists():
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
            results.append(f"✅ 创建下载目录: {download_dir}")
        except Exception as e:
            results.append(f"❌ 无法创建下载目录: {e}")
    
    # 检查存档文件
    archive_file = Path(config.ARCHIVE_FILE)
    if not archive_file.exists():
        try:
            archive_file.parent.mkdir(parents=True, exist_ok=True)
            archive_file.write_text('{}', encoding='utf-8')
            results.append(f"✅ 创建存档文件: {archive_file}")
        except Exception as e:
            results.append(f"❌ 无法创建存档文件: {e}")
    
    # 检查账号文件
    accounts_file = Path(config.ACCOUNTS_FILE)
    if not accounts_file.exists():
        try:
            accounts_file.parent.mkdir(parents=True, exist_ok=True)
            accounts_file.write_text('[]', encoding='utf-8')
            results.append(f"✅ 创建账号文件: {accounts_file}")
        except Exception as e:
            results.append(f"❌ 无法创建账号文件: {e}")
    
    # 检查设置文件
    settings_file = Path(config.CONFIG_FILE)
    if not settings_file.exists():
        try:
            settings_file.write_text(json.dumps(config.DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding='utf-8')
            results.append(f"✅ 创建设置文件: {settings_file}")
        except Exception as e:
            results.append(f"❌ 无法创建设置文件: {e}")
    
    return results


def load_archive():
    """加载已下载的内容记录"""
    data_dir = config.get_data_dir()
    archive_path = data_dir / config.ARCHIVE_FILE
    if archive_path.exists():
        try:
            with open(archive_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    # 文件为空，返回空字典
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️  存档文件损坏: {archive_path}")
            print(f"   错误: {e}")
            print(f"   将使用空存档继续...")
            return {}
        except Exception as e:
            print(f"⚠️  读取存档失败: {e}")
            return {}
    return {}


def save_archive(archive):
    """保存已下载的内容记录"""
    data_dir = config.get_data_dir()
    archive_path = data_dir / config.ARCHIVE_FILE
    # 确保父目录存在
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)


def run_gallery_dl_scan_posts(url, downloaded_ids, max_range=None):
    """
    扫描帖子（Posts），遇到2个连续重复则停止扫描，或达到最大范围停止
    
    Args:
        url: 账号URL
        downloaded_ids: 已下载的完整ID集合（含扩展名）
        max_range: 最大扫描范围（媒体文件数量），None表示不限制
    
    Returns:
        (media_list, success, stopped_early): 媒体信息列表、是否成功、是否提前终止
    """
    # 从已下载的完整ID中提取post_id集合（用于帖子级别的重复检测）
    downloaded_post_ids = set()
    for full_id in downloaded_ids:
        # 去掉扩展名，提取post_id（下划线前部分）
        id_without_ext = full_id.rsplit('.', 1)[0] if '.' in full_id else full_id
        post_id = id_without_ext.split('_')[0]
        downloaded_post_ids.add(post_id)
    
    # 使用当前目录的cookies文件（避免data_dir权限问题）
    cookies_path = config.COOKIES_FILE
    if not Path(cookies_path).exists():
        # 如果当前目录不存在，尝试使用data_dir
        data_dir = config.get_data_dir()
        cookies_path = str(data_dir / config.COOKIES_FILE)
    
    # 构建命令
    cmd = [
        get_gallery_dl_path(),
        "--simulate",
        "--proxy", config.PROXY,
        "--cookies", cookies_path,
        "-o", "extractor.instagram.include=posts",
    ]
    
    # 如果设置了最大扫描范围，使用 --range 参数限制 gallery-dl 的输出
    # 注意：--range 限制的是媒体文件数量
    if max_range:
        cmd.extend(["--range", f"1-{max_range}"])
    
    cmd.append(url)
    
    print(f"  [扫描帖子] {url}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=120  # 增加超时时间到120秒
        )
        
        # 解析输出，提取媒体文件ID，并检测连续重复
        media_list = []
        duplicate_count = 0  # 重复计数器，不清零
        max_duplicates = config.MAX_CONSECUTIVE_DUPLICATES  # 从配置读取重复检测阈值
        stopped_early = False
        new_content_count = 0  # 新内容计数器
        last_post_id = None  # 记录上一个帖子的ID
        post_index = 0  # 帖子位置索引（从1开始）
        media_index = 0  # 媒体文件全局位置索引（从1开始，用于range参数）
        
        for line in result.stdout.split('\n'):
            line = line.strip().upper()
            if line.startswith('# '):
                line = line[2:]
            if line and any(ext in line.lower() for ext in ['.jpg', '.mp4', '.webp']):
                # 使用完整文件名（含扩展名）进行重复检测
                filename = line
                # 提取帖子ID（下划线前部分），用于判断是否是同一帖子
                full_id = line.rsplit('.', 1)[0]
                post_id = full_id.split('_')[0]
                # 提取扩展名判断类型
                ext = line.rsplit('.', 1)[1].lower() if '.' in line else ''
                media_type = '视频' if ext == 'mp4' else '图片'
                
                # 检查是否是新帖子（前缀不同）
                is_new_post = (post_id != last_post_id)
                last_post_id = post_id
                
                # 增加媒体文件全局位置索引
                media_index += 1
                
                # 新帖子，增加帖子位置索引
                if is_new_post:
                    post_index += 1
                
                # 检查帖子是否重复（使用post_id进行帖子级别的重复检测）
                if post_id in downloaded_post_ids:
                    # 只有新帖子才增加重复计数
                    if is_new_post:
                        duplicate_count += 1
                        print(f"     📝 帖子 {post_id} ({media_type}, 重复 {duplicate_count}/{max_duplicates}, 帖子位置{post_index}, 媒体位置{media_index})")
                        
                        # 如果重复达到阈值，停止扫描
                        if duplicate_count >= max_duplicates:
                            print(f"     ⏹️  检测到{max_duplicates}个重复，停止扫描")
                            stopped_early = True
                            break
                else:
                    # 新内容，增加计数
                    new_content_count += 1
                    if is_new_post:
                        print(f"     ✨ 帖子 {post_id} ({media_type}, 新帖子, 帖子位置{post_index}, 媒体位置{media_index})")
                    else:
                        print(f"     ✨ 帖子 {post_id} ({media_type}, 同一帖子的媒体, 媒体位置{media_index})")
                    
                    # 记录完整信息到媒体列表
                    media_list.append({
                        "id": full_id,
                        "post_id": post_id,
                        "post_index": post_index,  # 帖子位置
                        "media_index": media_index,  # 媒体文件全局位置（用于range）
                        "filename": filename,  # 完整文件名含扩展名
                        "type": "post",
                        "media_type": media_type  # 媒体类型：图片/视频
                    })
                    
                    # 检查是否达到最大扫描范围
                    if max_range and media_index >= max_range:
                        print(f"     ⏹️  达到最大扫描范围 ({max_range} 个媒体文件)，停止扫描")
                        stopped_early = True
                        break
        
        unique_new_posts = len(set(m["post_id"] for m in media_list))
        max_media_index = max((m["media_index"] for m in media_list), default=0) if media_list else 0
        total_scanned = new_content_count + duplicate_count
        if stopped_early:
            print(f"     📊 扫描统计: 发现 {new_content_count} 个新内容 ({unique_new_posts} 个帖子, 最大媒体位置{max_media_index})，{duplicate_count} 个重复后停止")
        else:
            print(f"     📊 扫描统计: 发现 {new_content_count} 个新内容 ({unique_new_posts} 个帖子, 最大媒体位置{max_media_index})，{duplicate_count} 个重复")
        
        # 判断成功：只要有媒体文件返回就认为成功（即使gallery-dl返回非零退出码）
        success = len(media_list) > 0 or result.returncode == 0
        return media_list, success, stopped_early
        
    except subprocess.TimeoutExpired:
        print(f"  [错误] 帖子扫描超时")
        return [], False, False
    except Exception as e:
        print(f"  [错误] {e}")
        return [], False, False


def run_gallery_dl_scan_stories(url, downloaded_ids):
    """
    扫描快拍（Stories），全部扫描（快拍数量少，且顺序不确定）
    
    Args:
        url: 账号URL
        downloaded_ids: 已下载的快拍ID集合
    
    Returns:
        (media_list, success): 媒体信息列表、是否成功
    """
    cmd = [
        get_gallery_dl_path(),
        "--simulate",
        "--proxy", config.PROXY,
        "--cookies", config.COOKIES_FILE,
        "-o", "extractor.instagram.include=stories",
        url
    ]
    
    print(f"  [扫描快拍] {url}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=60
        )
        
        # 解析输出，提取媒体文件ID（全部扫描，不提前终止）
        media_list = []
        total_scanned = 0
        
        for line in result.stdout.split('\n'):
            line = line.strip().upper()
            if line.startswith('# '):
                line = line[2:]
            if line and any(ext in line.lower() for ext in ['.jpg', '.mp4', '.webp']):
                filename = line
                media_id = line.rsplit('.', 1)[0]
                # 提取扩展名判断类型
                ext = line.rsplit('.', 1)[1].lower() if '.' in line else ''
                media_type = '视频' if ext == 'mp4' else '图片'
                
                if media_id.replace('_', '').isdigit():
                    total_scanned += 1
                    
                    # 检查是否重复（使用完整文件名含扩展名）
                    if filename in downloaded_ids:
                        print(f"     📝 {media_id} ({media_type}, 已存在)")
                    else:
                        print(f"     ✨ {media_id} ({media_type}, 新内容)")
                        media_list.append({
                            "id": media_id,
                            "filename": filename,  # 完整文件名含扩展名
                            "type": "story",
                            "media_type": media_type  # 媒体类型：图片/视频
                        })
        
        print(f"     📊 扫描统计: 发现 {len(media_list)} 个新内容，共 {total_scanned} 个")
        
        return media_list, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"  [错误] 快拍扫描超时")
        return [], False
    except Exception as e:
        print(f"  [错误] {e}")
        return [], False


def check_account(account, archive, max_range=None):
    """检查账号的新内容（帖子和快拍分别统计，支持提前终止和范围限制）
    
    Args:
        account: 账号名
        archive: 存档数据
        max_range: 最大扫描范围（媒体文件数量），None表示不限制
    """
    url = f"https://www.instagram.com/{account}/"
    
    print(f"\n{'='*60}")
    print(f"📱 账号: {account}")
    print(f"{'='*60}")
    
    # 获取已下载的ID（完整文件名含扩展名）
    downloaded_posts = set(archive.get(account, {}).get("posts", []))
    downloaded_stories = set(archive.get(account, {}).get("stories", []))
    
    # 扫描帖子
    print()
    if max_range:
        print(f"  [扫描范围] 最多扫描前 {max_range} 个媒体文件")
    posts_list, posts_success, posts_stopped = run_gallery_dl_scan_posts(url, downloaded_posts, max_range)
    
    if posts_success:
        new_posts = posts_list  # 扫描函数已经过滤了重复
        # 计算唯一帖子数量和帖子位置范围
        unique_post_ids = set(m.get("post_id", m["id"].split('_')[0]) for m in new_posts)
        post_indices = [m.get("post_index", 0) for m in new_posts]
        min_post_idx = min(post_indices) if post_indices else 0
        max_post_idx = max(post_indices) if post_indices else 0
        post_range_str = f"帖子位置{min_post_idx}-{max_post_idx}" if len(unique_post_ids) > 1 else f"帖子位置{min_post_idx}"
        print(f"  📊 帖子: 发现 {len(unique_post_ids)} 个新帖子 ({len(new_posts)} 个媒体文件, {post_range_str})", end="")
        if posts_stopped:
            print(" (已提前终止)")
        else:
            print(" (全部扫描)")
        for i, media in enumerate(new_posts[:5], 1):
            print(f"     ✨ [帖子{media.get('post_index', '?')}/媒体{media.get('media_index', '?')}] {media['id']}")
        if len(new_posts) > 5:
            print(f"     ... 还有 {len(new_posts) - 5} 个")
    else:
        print(f"  ❌ 帖子扫描失败")
        new_posts = []
    
    # 请求间隔休眠
    if hasattr(__builtins__, 'REQUEST_SLEEP') and REQUEST_SLEEP[1] > 0:
        sleep_time = random.randint(REQUEST_SLEEP[0], REQUEST_SLEEP[1])
        sleep_with_progress_bar(sleep_time, "请求间隔")
    
    # 扫描快拍
    print()
    stories_list, stories_success = run_gallery_dl_scan_stories(url, downloaded_stories)
    
    if stories_success:
        new_stories = stories_list  # 扫描函数已经过滤了重复
        print(f"  📊 快拍: 发现 {len(new_stories)} 个新内容 (全部扫描)")
        for i, media in enumerate(new_stories[:5], 1):
            print(f"     ✨ {media['id']}")
        if len(new_stories) > 5:
            print(f"     ... 还有 {len(new_stories) - 5} 个")
    else:
        print(f"  ❌ 快拍扫描失败")
        new_stories = []
    
    # 合并新内容
    all_new = new_posts + new_stories
    
    # 计算唯一帖子数量（使用post_id去重）
    unique_post_count = len(set(m.get("post_id", m["id"].split('_')[0]) for m in new_posts))
    
    print(f"\n{'='*60}")
    print(f"📊 汇总: {len(all_new)} 个新内容")
    print(f"   - 帖子: {unique_post_count} 个帖子 ({len(new_posts)} 个媒体文件) {'(提前终止)' if posts_stopped else ''}")
    print(f"   - 快拍: {len(new_stories)} 个")
    print(f"{'='*60}")
    
    return all_new, new_posts, new_stories


def update_archive(account, new_posts, new_stories):
    """更新存档记录（帖子和快拍分开存储，使用完整ID含扩展名）"""
    archive = load_archive()
    
    if account not in archive:
        archive[account] = {"posts": [], "stories": []}
    
    # 添加新帖子ID（使用完整文件名含扩展名）
    new_post_ids = [m["filename"] for m in new_posts]
    archive[account]["posts"].extend(new_post_ids)
    archive[account]["posts"] = list(dict.fromkeys(archive[account]["posts"]))
    
    # 添加新快拍ID（使用完整文件名含扩展名）
    new_story_ids = [m["filename"] for m in new_stories]
    archive[account]["stories"].extend(new_story_ids)
    archive[account]["stories"] = list(dict.fromkeys(archive[account]["stories"]))
    
    save_archive(archive)
    print(f"\n  💾 已更新存档:")
    print(f"     帖子: {len(archive[account]['posts'])} 个媒体文件")
    print(f"     快拍: {len(archive[account]['stories'])} 个媒体文件")


def sleep_with_progress_bar(total_seconds, label="等待"):
    """
    带进度条的休眠
    
    Args:
        total_seconds: 总等待秒数
        label: 显示的标签文字
    """
    import sys
    
    bar_length = 30  # 进度条长度
    
    for i in range(total_seconds + 1):
        # 计算进度
        progress = i / total_seconds if total_seconds > 0 else 1
        filled = int(bar_length * progress)
        empty = bar_length - filled
        
        # 构建进度条
        bar = "█" * filled + "░" * empty
        
        # 显示进度
        sys.stdout.write(f"\r  ⏱️  {label}: [{bar}] {i}/{total_seconds} 秒")
        sys.stdout.flush()
        
        # 最后一秒不sleep
        if i < total_seconds:
            time.sleep(1)
    
    # 换行
    sys.stdout.write("\n")
    sys.stdout.flush()


def extract_and_save_post_info_from_paths(account, json_file_paths):
    """
    从元数据JSON文件（完整路径）中提取帖子信息并保存到TXT
    
    Args:
        account: 账号名
        json_file_paths: JSON文件的完整路径列表
    """
    import json
    import re
    from pathlib import Path
    
    def extract_caption(data):
        """提取帖子文字内容"""
        caption = data.get('description', '')
        if not caption:
            caption = data.get('caption', '')
        if not caption and 'edge_media_to_caption' in data:
            edges = data['edge_media_to_caption'].get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')
        return caption or '无'
    
    def extract_hashtags(data):
        """提取标签"""
        tags = data.get('tags', [])
        if tags:
            return tags
        caption = extract_caption(data)
        return re.findall(r'#(\w+)', caption)
    
    def extract_tagged_users(data):
        """提取提及的用户"""
        tagged = data.get('tagged_users', [])
        users = []
        for user in tagged:
            if isinstance(user, dict):
                username = user.get('username', '')
                full_name = user.get('full_name', '')
                if username:
                    display = f"{username}" + (f" ({full_name})" if full_name else "")
                    users.append(display)
            elif isinstance(user, str):
                users.append(user)
        return users
    
    def extract_location(data):
        """提取地理位置"""
        location_slug = data.get('location_slug', '')
        if location_slug:
            return location_slug
        location = data.get('location', {})
        if isinstance(location, dict):
            name = location.get('name', '')
            slug = location.get('slug', '')
            return name or slug or '无'
        return '无'
    
    def format_timestamp(data):
        """格式化时间戳"""
        post_date = data.get('post_date', '')
        if post_date:
            return post_date
        
        timestamp = data.get('timestamp', '')
        if not timestamp:
            return '未知'
        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return str(timestamp)
        except:
            return str(timestamp)
    
    # 提取所有JSON文件的信息
    info_list = []
    for json_path_str in json_file_paths:
        try:
            json_path = Path(json_path_str)
            if not json_path.exists():
                print(f"     ⚠️  文件不存在: {json_path}")
                continue
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            caption = extract_caption(data)
            hashtags = extract_hashtags(data)
            mentions = extract_tagged_users(data)
            location = extract_location(data)
            
            info = {
                'file': json_path.name,
                'username': data.get('username', '') or data.get('owner', {}).get('username', account),
                'fullname': data.get('fullname', '') or data.get('owner', {}).get('full_name', ''),
                'timestamp': format_timestamp(data),
                'caption': caption,
                'hashtags': hashtags,
                'mentions': mentions,
                'location': location,
                'likes': data.get('likes', 0),
                'comments': data.get('comments', 0),
                'media_type': '视频' if data.get('is_video') or data.get('video_url') else '图片',
                'shortcode': data.get('shortcode', '') or data.get('post_shortcode', ''),
                'post_url': data.get('post_url', '')
            }
            info_list.append(info)
            print(f"     ✅ 解析成功: {json_path.name}")
        except Exception as e:
            print(f"     ⚠️  解析 {json_path_str} 失败: {e}")
    
    if not info_list:
        print(f"     ⚠️  没有成功解析任何帖子信息")
        return
    
    # 保存到TXT文件（放在第一个JSON文件所在目录）
    if json_file_paths:
        output_dir = Path(json_file_paths[0]).parent
        output_file = output_dir / '帖子信息.txt'
    else:
        return
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"╔{'═'*68}╗\n")
        f.write(f"║{'Instagram 帖子信息汇总':^68}║\n")
        f.write(f"║{f'账号: {account}':^68}║\n")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"║{f'生成时间: {current_time}':^68}║\n")
        f.write(f"╠{'═'*68}╣\n")
        f.write(f"║  共 {len(info_list)} 个帖子{' '*56}║\n")
        f.write(f"╚{'═'*68}╝\n\n")
        
        for i, info in enumerate(info_list, 1):
            f.write(f"┌{'─'*68}┐\n")
            f.write(f"│ 【帖子 {i}】{' '*57}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 📄 文件: {info['file']:<57}│\n")
            f.write(f"│ 👤 发帖人: {info['fullname'] or info['username']:<55}│\n")
            f.write(f"│ 📝 用户名: @{info['username']:<54}│\n")
            f.write(f"│ ⏰ 发布时间: {info['timestamp']:<53}│\n")
            f.write(f"│ 📍 地理位置: {info['location']:<53}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 💬 帖子内容:\n")
            caption_lines = info['caption'].split('\n')
            for line in caption_lines:
                while line:
                    display_line = line[:64]
                    f.write(f"│    {display_line:<64}│\n")
                    line = line[64:]
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 🏷️  标签: {', '.join(['#' + h for h in info['hashtags']]) if info['hashtags'] else '无':<54}│\n")
            f.write(f"│ 👥 提及: {', '.join(['@' + m.split(' ')[0] for m in info['mentions']]) if info['mentions'] else '无':<55}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ ❤️  点赞: {info['likes']:<54}│\n")
            f.write(f"│ 💬 评论: {info['comments']:<55}│\n")
            f.write(f"│ 📎 类型: {info['media_type']:<55}│\n")
            post_link = info['post_url'] or f"https://instagram.com/p/{info['shortcode']}/"
            f.write(f"│ 🔗 链接: {post_link:<55}│\n")
            f.write(f"└{'─'*68}┘\n\n")
    
    print(f"     📝 已保存帖子信息: {output_file}")


def extract_and_save_post_info(account, json_files, subdir='posts'):
    """
    从元数据JSON文件中提取帖子信息并保存到TXT（兼容旧版本，使用文件名列表）
    
    Args:
        account: 账号名
        json_files: JSON文件名列表（不含路径）
        subdir: 子目录名称（默认为 'posts'）
    """
    import json
    import re
    from pathlib import Path
    
    def extract_caption(data):
        """提取帖子文字内容"""
        # 优先使用 description 字段（gallery-dl 提取的）
        caption = data.get('description', '')
        if not caption:
            caption = data.get('caption', '')
        if not caption and 'edge_media_to_caption' in data:
            edges = data['edge_media_to_caption'].get('edges', [])
            if edges:
                caption = edges[0].get('node', {}).get('text', '')
        return caption or '无'
    
    def extract_hashtags(data):
        """提取标签"""
        # 优先使用 tags 字段（gallery-dl 提取的）
        tags = data.get('tags', [])
        if tags:
            return tags
        # 从文字中提取
        caption = extract_caption(data)
        return re.findall(r'#(\w+)', caption)
    
    def extract_tagged_users(data):
        """提取提及的用户"""
        tagged = data.get('tagged_users', [])
        users = []
        for user in tagged:
            if isinstance(user, dict):
                username = user.get('username', '')
                full_name = user.get('full_name', '')
                if username:
                    display = f"{username}" + (f" ({full_name})" if full_name else "")
                    users.append(display)
            elif isinstance(user, str):
                users.append(user)
        return users
    
    def extract_location(data):
        """提取地理位置"""
        # 优先使用 location_slug 字段
        location_slug = data.get('location_slug', '')
        if location_slug:
            return location_slug
        # 使用 location 字段
        location = data.get('location', {})
        if isinstance(location, dict):
            name = location.get('name', '')
            slug = location.get('slug', '')
            return name or slug or '无'
        return '无'
    
    def format_timestamp(data):
        """格式化时间戳"""
        # 优先使用 post_date 字段（gallery-dl 提取的）
        post_date = data.get('post_date', '')
        if post_date:
            return post_date
        
        timestamp = data.get('timestamp', '')
        if not timestamp:
            return '未知'
        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            return str(timestamp)
        except:
            return str(timestamp)
    
    # 获取数据目录
    data_dir = config.get_data_dir()
    
    # 提取所有JSON文件的信息
    info_list = []
    for json_file in json_files:
        try:
            # 构建路径（如果 subdir 为空，则直接放在账号目录下）
            if subdir:
                json_path = data_dir / config.DOWNLOAD_DIR / account / subdir / json_file
            else:
                json_path = data_dir / config.DOWNLOAD_DIR / account / json_file
            
            if not json_path.exists():
                # 如果找不到，尝试其他可能的目录
                alt_paths = [
                    data_dir / config.DOWNLOAD_DIR / account / 'posts' / json_file,
                    data_dir / config.DOWNLOAD_DIR / account / 'manual' / json_file,
                    data_dir / config.DOWNLOAD_DIR / 'temp_manual' / json_file,
                ]
                for alt_path in alt_paths:
                    if alt_path.exists():
                        json_path = alt_path
                        break
                else:
                    print(f"     ⚠️  文件不存在: {json_path}")
                    continue
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            caption = extract_caption(data)
            hashtags = extract_hashtags(data)
            mentions = extract_tagged_users(data)
            location = extract_location(data)
            
            info = {
                'file': json_file,
                'username': data.get('username', '') or data.get('owner', {}).get('username', account),
                'fullname': data.get('fullname', '') or data.get('owner', {}).get('full_name', ''),
                'timestamp': format_timestamp(data),
                'caption': caption,
                'hashtags': hashtags,
                'mentions': mentions,
                'location': location,
                'likes': data.get('likes', 0),
                'comments': data.get('comments', 0),
                'media_type': '视频' if data.get('is_video') or data.get('video_url') else '图片',
                'shortcode': data.get('shortcode', '') or data.get('post_shortcode', ''),
                'post_url': data.get('post_url', '')
            }
            info_list.append(info)
            print(f"     ✅ 解析成功: {json_file}")
        except Exception as e:
            print(f"     ⚠️  解析 {json_file} 失败: {e}")
    
    if not info_list:
        print(f"     ⚠️  没有成功解析任何帖子信息")
        return
    
    # 保存到TXT文件（放在对应的子目录下，如果 subdir 为空则直接放在账号目录下）
    if subdir:
        output_file = data_dir / config.DOWNLOAD_DIR / account / subdir / '帖子信息.txt'
    else:
        output_file = data_dir / config.DOWNLOAD_DIR / account / '帖子信息.txt'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"╔{'═'*68}╗\n")
        f.write(f"║{'Instagram 帖子信息汇总':^68}║\n")
        f.write(f"║{f'账号: {account}':^68}║\n")
        f.write(f"║{f'生成时间: {current_time}':^68}║\n")
        f.write(f"╠{'═'*68}╣\n")
        f.write(f"║  共 {len(info_list)} 个帖子{' '*56}║\n")
        f.write(f"╚{'═'*68}╝\n\n")
        
        for i, info in enumerate(info_list, 1):
            f.write(f"┌{'─'*68}┐\n")
            f.write(f"│ 【帖子 {i}】{' '*57}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 📄 文件: {info['file']:<57}│\n")
            f.write(f"│ 👤 发帖人: {info['fullname'] or info['username']:<55}│\n")
            f.write(f"│ 📝 用户名: @{info['username']:<54}│\n")
            f.write(f"│ ⏰ 发布时间: {info['timestamp']:<53}│\n")
            f.write(f"│ 📍 地理位置: {info['location']:<53}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 💬 帖子内容:\n")
            # 处理多行内容
            caption_lines = info['caption'].split('\n')
            for line in caption_lines:
                # 每行最多显示 64 个字符
                while line:
                    display_line = line[:64]
                    f.write(f"│    {display_line:<64}│\n")
                    line = line[64:]
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ 🏷️  标签: {', '.join(['#' + h for h in info['hashtags']]) if info['hashtags'] else '无':<54}│\n")
            f.write(f"│ 👥 提及: {', '.join(['@' + m.split(' ')[0] for m in info['mentions']]) if info['mentions'] else '无':<55}│\n")
            f.write(f"├{'─'*68}┤\n")
            f.write(f"│ ❤️  点赞: {info['likes']:<54}│\n")
            f.write(f"│ 💬 评论: {info['comments']:<55}│\n")
            f.write(f"│ 📎 类型: {info['media_type']:<55}│\n")
            post_link = info['post_url'] or f"https://instagram.com/p/{info['shortcode']}/"
            f.write(f"│ 🔗 链接: {post_link:<55}│\n")
            f.write(f"└{'─'*68}┘\n\n")
    
    print(f"     📝 已保存帖子信息: {output_file}")


def download_content_v2(account, posts_range, new_stories_count):
    """
    下载新内容（使用正确的 --range 参数）
    
    Args:
        account: 账号名
        posts_range: 帖子range元组 (start, end) 或 None
        new_stories_count: 新快拍数量
    
    Returns:
        (posts_success, stories_success): 下载是否成功
    """
    url = f"https://www.instagram.com/{account}/"
    posts_success = True
    stories_success = True
    
    # 下载新帖子（同时下载元数据）
    if posts_range and posts_range[0] > 0 and posts_range[1] >= posts_range[0]:
        start, end = posts_range
        print(f"\n  [下载帖子] 下载媒体位置 {start}-{end}（含元数据）")
        # 使用绝对路径
        data_dir = config.get_data_dir()
        download_path = str(data_dir / config.DOWNLOAD_DIR / account / "posts")
        cmd = [
            get_gallery_dl_path(),
            "--range", f"{start}-{end}",
            "--write-metadata",  # 同时下载元数据
            "--proxy", config.PROXY,
            "--cookies", config.COOKIES_FILE,
            "-o", "extractor.instagram.include=posts",
            "-D", download_path,
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=300
            )
            
            if result.returncode == 0:
                # 解析下载的文件（保持原始大小写）
                downloaded_files = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                media_files = [f for f in downloaded_files if not f.lower().endswith('.json')]
                json_files = [f for f in downloaded_files if f.lower().endswith('.json')]
                print(f"     ✅ 下载完成: {len(media_files)} 个媒体文件, {len(json_files)} 个元数据文件")
                for f in media_files[:5]:
                    print(f"        📥 {f}")
                if len(media_files) > 5:
                    print(f"        ... 还有 {len(media_files) - 5} 个媒体文件")
                
                # 提取并保存文本信息
                if json_files:
                    # 构建完整的 JSON 文件路径（使用绝对路径）
                    data_dir = config.get_data_dir()
                    output_dir = data_dir / config.DOWNLOAD_DIR / account / "posts"
                    json_paths = [str(output_dir / f) for f in json_files]
                    print(f"     [调试] 自动下载 - JSON 路径: {json_paths[:2]}...")  # 只显示前2个
                    extract_and_save_post_info_from_paths(account, json_paths)
                
                # 下载间隔休眠
                if hasattr(__builtins__, 'DOWNLOAD_SLEEP') and DOWNLOAD_SLEEP[1] > 0:
                    sleep_time = random.randint(DOWNLOAD_SLEEP[0], DOWNLOAD_SLEEP[1])
                    sleep_with_progress_bar(sleep_time, "下载间隔")
            else:
                print(f"     ⚠️  下载可能有问题，返回码: {result.returncode}")
                if result.stderr:
                    print(f"     错误: {result.stderr[:500]}")
                posts_success = False
                
        except subprocess.TimeoutExpired:
            print(f"     ❌ 下载超时")
            posts_success = False
        except Exception as e:
            print(f"     ❌ 下载错误: {e}")
            posts_success = False
    
    # 下载新快拍（不使用 range 限制，下载全部快拍）
    if new_stories_count > 0:
        print(f"\n  [下载快拍] 下载全部 {new_stories_count} 个新快拍")
        # 使用绝对路径
        stories_download_path = str(data_dir / config.DOWNLOAD_DIR / account / "stories")
        cmd = [
            get_gallery_dl_path(),
            # 不使用 --range 参数
            "--proxy", config.PROXY,
            "--cookies", config.COOKIES_FILE,
            "-o", "extractor.instagram.include=stories",
            "-D", stories_download_path,
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=300
            )
            
            if result.returncode == 0:
                # 解析下载的文件
                downloaded_files = [line.strip().upper() for line in result.stdout.split('\n') if line.strip().upper()]
                print(f"     ✅ 下载完成: {len(downloaded_files)} 个文件")
                for f in downloaded_files[:5]:
                    print(f"        📥 {f}")
                if len(downloaded_files) > 5:
                    print(f"        ... 还有 {len(downloaded_files) - 5} 个")
            else:
                print(f"     ⚠️  下载可能有问题，返回码: {result.returncode}")
                if result.stderr:
                    print(f"     错误: {result.stderr[:500]}")
                stories_success = False
                
        except subprocess.TimeoutExpired:
            print(f"     ❌ 下载超时")
            stories_success = False
        except Exception as e:
            print(f"     ❌ 下载错误: {e}")
            stories_success = False
    
    return posts_success, stories_success


import sys

def ask_yes_no(question, default="y", auto_mode=False):
    """询问用户是/否"""
    if auto_mode:
        print(f"{question} (Y/n): Y (自动模式)")
        return True
    
    while True:
        try:
            answer = input(f"{question} (Y/n): ").strip().upper().lower()
            if answer == '' or answer == 'y' or answer == 'yes':
                return True
            elif answer == 'n' or answer == 'no':
                return False
            else:
                print("  请输入 Y 或 n")
        except EOFError:
            # 非交互式环境，使用默认值
            print(f"{question} (Y/n): {default.upper()} (非交互模式)")
            return default == 'y'


def show_account_management_menu():
    """显示账号管理菜单"""
    print(f"\n{'='*60}")
    print("👤 账号管理")
    print(f"{'='*60}")
    
    # 显示当前账号
    print(f"\n📋 当前监控账号 ({len(config.ACCOUNTS)} 个):")
    for i, account in enumerate(config.ACCOUNTS, 1):
        print(f"   {i}. {account}")
    
    print(f"\n{'='*60}")
    print("请选择操作:")
    print("  1. 添加账号 - 新增监控账号")
    print("  2. 删除账号 - 移除监控账号")
    print("  B. 返回上一级")
    print("  M. 返回主菜单")
    print(f"{'='*60}")


def manage_accounts_menu():
    """管理账号菜单"""
    while True:
        show_account_management_menu()
        
        choice = input("请输入选项 (1/2/B/M): ").strip().upper()
        
        if choice == '1':
            # 添加账号
            print(f"\n{'='*60}")
            print("➕ 添加账号")
            print(f"{'='*60}")
            print("说明: 输入 Instagram 用户名（不需要 @ 符号）")
            print("      例如: Instagram")
            print("      输入 B 返回上一级，输入 M 返回主菜单")
            print(f"{'='*60}\n")
            
            new_account = input("请输入用户名: ").strip().upper().lower()
            
            if new_account == 'b':
                print("\n⏭️  返回上一级")
                continue  # 重新显示菜单
            
            if new_account == 'm':
                print("\n⏭️  返回主菜单")
                return  # 返回主菜单
            
            if not new_account:
                print("\n⚠️  用户名不能为空")
                continue  # 重新显示菜单
            
            # 去除 @ 符号
            new_account = new_account.lstrip('@')
            
            if new_account in config.ACCOUNTS:
                print(f"\n⚠️  账号 {new_account} 已存在")
                continue
            
            # 验证用户名格式（只允许字母、数字、下划线、点）
            if not re.match(r'^[a-zA-Z0-9_.]+$', new_account):
                print(f"\n⚠️  用户名格式不正确，只允许字母、数字、下划线和点")
                continue
            
            if ask_yes_no(f"确定要添加账号 {new_account}?"):
                config.ACCOUNTS.append(new_account)
                # 保存到存档
                if config.save_accounts(config.ACCOUNTS):
                    print(f"\n✅ 已添加账号: {new_account}")
                    print(f"   当前共有 {len(config.ACCOUNTS)} 个账号")
                    print(f"   账号列表: {', '.join(config.ACCOUNTS)}")
                    print(f"   已保存到: {config.ACCOUNTS_FILE}")
                else:
                    print(f"\n⚠️  已添加账号到内存，但保存失败")
            else:
                print("\n⏭️  已取消")
            continue  # 重新显示菜单
        
        elif choice == '2':
            # 删除账号
            if not config.ACCOUNTS:
                print("\n⚠️  没有可删除的账号")
                continue
            
            print(f"\n{'='*60}")
            print("➖ 删除账号")
            print(f"{'='*60}")
            print("选择要删除的账号:")
            for i, account in enumerate(config.ACCOUNTS, 1):
                print(f"  {i}. {account}")
            print(f"  B. 返回上一级")
            print(f"  M. 返回主菜单")
            print(f"{'='*60}")
            
            try:
                acc_choice = input(f"\n请输入选项 (1-{len(config.ACCOUNTS)}/9/0): ").strip().upper()
                if acc_choice == 'B':
                    print("\n⏭️  返回上一级")
                    continue  # 重新显示菜单
                
                if acc_choice == 'M':
                    print("\n⏭️  返回主菜单")
                    return  # 返回主菜单
                
                acc_choice = int(acc_choice)
                if 1 <= acc_choice <= len(config.ACCOUNTS):
                    account = config.ACCOUNTS[acc_choice - 1]
                    if ask_yes_no(f"⚠️  确定要删除账号 {account}?"):
                        config.ACCOUNTS.remove(account)
                        # 保存到存档
                        if config.save_accounts(config.ACCOUNTS):
                            print(f"\n✅ 已删除账号: {account}")
                            print(f"   当前共有 {len(config.ACCOUNTS)} 个账号")
                            account_list = ', '.join(config.ACCOUNTS) if config.ACCOUNTS else '（空）'
                            print(f"   账号列表: {account_list}")
                            print(f"   已保存到: {config.ACCOUNTS_FILE}")
                        else:
                            print(f"\n⚠️  已从内存删除账号，但保存失败")
                    else:
                        print("\n⏭️  已取消")
                else:
                    print("\n❌ 输入无效")
            except:
                print("\n❌ 输入无效")
            continue  # 重新显示菜单
        
        elif choice == 'B':
            print("\n⏭️  返回上一级")
            return  # 返回上一级（这里上一级就是主菜单）
        
        elif choice == 'M':
            print("\n⏭️  返回主菜单")
            return  # 返回主菜单
        
        else:
            print("  请输入 1、2、B 或 M")


def download_from_url_menu():
    """从链接手动下载菜单"""
    print(f"\n{'='*60}")
    print("🔗 手动下载链接")
    print(f"{'='*60}")
    print("说明: 输入 Instagram 帖子或快拍的完整链接")
    print("      例如:")
    print("        帖子: https://www.instagram.com/p/ABC123DEF/")
    print("        快拍: https://www.instagram.com/stories/username/1234567890/")
    print("      输入 B 返回上一级，输入 M 返回主菜单")
    print(f"{'='*60}\n")
    
    while True:
        url = input("请输入链接: ").strip()
        
        if url.lower() == 'b':
            print("\n⏭️  返回上一级")
            return
        
        if url.lower() == 'm':
            print("\n⏭️  返回主菜单")
            return 'main_menu'
        
        if not url:
            print("⚠️  链接不能为空")
            continue
        
        # 验证链接格式
        if not url.startswith('https://www.instagram.com/'):
            print("❌ 无效的 Instagram 链接")
            print("   链接应以 https://www.instagram.com/ 开头")
            continue
        
        # 确定内容类型
        content_type = None
        if '/p/' in url or '/reel/' in url:
            content_type = '帖子/Reel'
        elif '/stories/' in url:
            content_type = '快拍'
        else:
            print("⚠️  无法识别链接类型，将尝试下载")
            content_type = '未知'
        
        print(f"\n📋 链接信息:")
        print(f"   类型: {content_type}")
        print(f"   URL: {url}")
        
        if not ask_yes_no("确认下载?"):
            print("⏭️  已取消")
            continue
        
        # 执行下载
        print(f"\n📥 开始下载...")
        success = download_single_url(url)
        
        if success:
            print("\n✅ 下载完成")
        else:
            print("\n❌ 下载失败")
        
        print(f"\n{'='*60}")
        print("是否继续下载其他链接?")
        if not ask_yes_no("继续?"):
            print("\n⏭️  返回上一级")
            return


def download_single_url(url):
    """
    下载单个链接的内容
    
    Args:
        url: Instagram 链接
    
    Returns:
        bool: 是否成功
    """
    import re
    
    # 从链接中提取账号名（如果是快拍）
    account = None
    if '/stories/' in url:
        # 快拍链接: /stories/username/id/
        match = re.search(r'/stories/([^/]+)/', url)
        if match:
            account = match.group(1)
    
    # 构建输出目录（先使用临时目录，下载后再根据元数据移动）
    data_dir = config.get_data_dir()
    output_dir = str(data_dir / config.DOWNLOAD_DIR / "temp_manual")
    print(f"   [调试] 临时目录: {output_dir}")
    
    # 构建下载命令
    cmd = [
        get_gallery_dl_path(),
        "--write-metadata",  # 下载元数据
        "--proxy", config.PROXY,
        "--cookies", config.COOKIES_FILE,
        "-D", output_dir,
        url
    ]
    
    try:
        print(f"   输出目录: {output_dir}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=300
        )
        
        if result.returncode == 0:
            # 解析下载的文件
            downloaded_files = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            media_files = [f for f in downloaded_files if not f.lower().endswith('.json')]
            json_files = [f for f in downloaded_files if f.lower().endswith('.json')]
            
            print(f"   ✅ 下载完成: {len(media_files)} 个媒体文件")
            for f in media_files:
                print(f"      📥 {f}")
            
            # 如果有元数据，提取信息
            if json_files:
                # 从第一个 JSON 文件中提取真实账号名
                real_account = account
                try:
                    json_path = Path(output_dir) / json_files[0]
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        real_account = data.get('username', '') or data.get('owner', {}).get('username', account)
                except Exception as e:
                    print(f"   ⚠️  无法从元数据提取账号名: {e}")
                
                if real_account:
                    # 将文件移动到正确的账号目录（直接放在账号目录下，不加 manual）
                    new_output_dir = str(data_dir / config.DOWNLOAD_DIR / real_account)
                    print(f"   [调试] 目标目录: {new_output_dir}")
                    Path(new_output_dir).mkdir(parents=True, exist_ok=True)
                    
                    moved_files = []
                    for f in downloaded_files:
                        src = Path(output_dir) / f
                        dst = Path(new_output_dir) / f
                        print(f"   [调试] 移动: {src} -> {dst}")
                        if src.exists():
                            src.rename(dst)
                            moved_files.append(f)
                        else:
                            print(f"   [调试] 源文件不存在: {src}")
                    
                    # 构建完整的 JSON 文件路径列表（在新目录中）
                    new_json_paths = [str(Path(new_output_dir) / f) for f in json_files]
                    print(f"   [调试] JSON 路径: {new_json_paths}")
                    
                    # 提取信息（传入完整路径）
                    if new_json_paths:
                        print(f"   [调试] 调用提取函数，账号: {real_account}")
                        extract_and_save_post_info_from_paths(real_account, new_json_paths)
                    
                    # 清理临时目录
                    try:
                        Path(output_dir).rmdir()
                        print(f"   [调试] 已清理临时目录")
                    except Exception as e:
                        print(f"   [调试] 清理临时目录失败: {e}")
            
            return True
        else:
            print(f"   ❌ 下载失败，返回码: {result.returncode}")
            if result.stderr:
                print(f"   错误: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ 下载超时")
        return False
    except Exception as e:
        print(f"   ❌ 下载错误: {e}")
        return False


def select_mode():
    """交互式选择运行模式"""
    print(f"\n{'='*60}")
    print("请选择运行模式:")
    print("  1. 仅扫描存档 - 只扫描并存档，不下载")
    print("  2. 扫描并下载 - 扫描、存档并下载新内容")
    print("  3. 手动下载 - 输入链接直接下载")
    print("  4. 清除存档 - 管理或删除存档记录")
    print("  5. 更新 Cookies - 更新 Instagram 登录凭证")
    print("  6. 管理账号 - 添加或删除监控账号")
    print("  7. 系统设置 - 修改文件路径和参数")
    print("  Q. 退出程序")
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input("请输入选项 (1/2/3/4/5/6/7/Q): ").strip().upper()
            if choice == '1':
                return 'scan_only'
            elif choice == '2':
                return 'full'
            elif choice == '3':
                return 'manual_download'
            elif choice == '4':
                return 'clear_archive'
            elif choice == '5':
                return 'update_cookies'
            elif choice == '6':
                return 'manage_accounts'
            elif choice == '7':
                return 'settings'
            elif choice == 'Q':
                return 'exit'
            else:
                print("  请输入 1、2、3、4、5、6、7 或 Q")
        except EOFError:
            # 非交互式环境，默认选择完整模式
            print("非交互环境，默认选择: 扫描并下载")
            return 'full'


def select_account_and_clear_type(archive, clear_type_name):
    """
    选择账号并确认清除类型
    
    Args:
        archive: 存档数据
        clear_type_name: 清除类型名称（"帖子"或"快拍"）
    """
    print(f"\n{'='*60}")
    print(f"选择要清除{clear_type_name}记录的账号:")
    accounts = list(archive.keys())
    for i, account in enumerate(accounts, 1):
        if clear_type_name == "帖子":
            count = len(archive[account].get("posts", []))
        else:
            count = len(archive[account].get("stories", []))
        print(f"  {i}. {account} ({count} 个{clear_type_name})")
    print(f"  {len(accounts) + 1}. 全部账号")
    print(f"  {len(accounts) + 2}. 返回")
    
    try:
        acc_choice = int(input(f"\n请输入选项 (1-{len(accounts) + 2}): ").strip().upper())
        if 1 <= acc_choice <= len(accounts):
            account = accounts[acc_choice - 1]
            if ask_yes_no(f"⚠️  确定要清除 {account} 的{clear_type_name}记录?"):
                if clear_type_name == "帖子":
                    archive[account]["posts"] = []
                else:
                    archive[account]["stories"] = []
                save_archive(archive)
                print(f"\n✅ 已清除 {account} 的{clear_type_name}记录")
            else:
                print("\n⏭️  已取消")
        elif acc_choice == len(accounts) + 1:
            # 全部账号
            if ask_yes_no(f"⚠️  确定要清除所有账号的{clear_type_name}记录?"):
                for acc in archive:
                    if clear_type_name == "帖子":
                        archive[acc]["posts"] = []
                    else:
                        archive[acc]["stories"] = []
                save_archive(archive)
                print(f"\n✅ 已清除所有账号的{clear_type_name}记录")
            else:
                print("\n⏭️  已取消")
        elif acc_choice == len(accounts) + 2:
            print("\n⏭️  返回")
    except:
        print("\n❌ 输入无效")


def clear_archive_menu():
    """清除存档菜单"""
    print(f"\n{'='*60}")
    print("🗑️  清除存档")
    print(f"{'='*60}")
    
    archive = load_archive()
    
    if not archive:
        print("\n📭 存档为空，无需清理")
        return
    
    # 显示当前存档统计
    print("\n📊 当前存档统计:")
    for account, data in archive.items():
        posts_count = len(data.get("posts", []))
        stories_count = len(data.get("stories", []))
        print(f"   📱 {account}: {posts_count} 个帖子, {stories_count} 个快拍")
    
    print(f"\n{'='*60}")
    print("请选择操作:")
    print("  1. 清除全部存档 - 删除所有记录")
    print("  2. 清除指定账号 - 选择账号并选择清除内容")
    print("  B. 返回上一级")
    print("  M. 返回主菜单")
    print(f"{'='*60}")
    
    while True:
        choice = input("请输入选项 (1/2/B/M): ").strip().upper()
        
        if choice == '1':
            # 清除全部
            if ask_yes_no("⚠️  确定要清除全部存档?"):
                save_archive({})
                print("\n✅ 已清除全部存档")
                print("\n📭 存档已清空")
                print(f"\n{'='*60}")
                print("请选择操作:")
                print("  1. 清除全部存档 - 删除所有记录")
                print("  2. 清除指定账号 - 选择账号并选择清除内容")
                print("  B. 返回上一级")
                print("  M. 返回主菜单")
                print(f"{'='*60}")
            else:
                print("\n⏭️  已取消")
                print(f"\n{'='*60}")
                print("请选择操作:")
                print("  1. 清除全部存档 - 删除所有记录")
                print("  2. 清除指定账号 - 选择账号并选择清除内容")
                print("  B. 返回上一级")
                print("  M. 返回主菜单")
                print(f"{'='*60}")
            continue  # 继续显示菜单
        
        elif choice == '2':
            # 清除指定账号 - 先选账号，再选类型
            while True:  # 账号选择循环
                print(f"\n{'='*60}")
                print("选择要清除的账号:")
                accounts = list(archive.keys())
                for i, account in enumerate(accounts, 1):
                    posts_count = len(archive[account].get("posts", []))
                    stories_count = len(archive[account].get("stories", []))
                    print(f"  {i}. {account} ({posts_count} 个帖子, {stories_count} 个快拍)")
                print(f"  B. 返回上一级")
                print(f"  M. 返回主菜单")
                print(f"{'='*60}")
                
                try:
                    acc_choice = input(f"\n请输入选项 (1-{len(accounts)}/9/0): ").strip().upper()
                    if acc_choice == 'B':
                        print("\n⏭️  返回上一级")
                        break  # 跳出账号选择循环，回到清除存档菜单
                    
                    if acc_choice == 'M':
                        print("\n⏭️  返回主菜单")
                        return  # 返回主菜单
                    
                    acc_choice = int(acc_choice)
                    if 1 <= acc_choice <= len(accounts):
                        account = accounts[acc_choice - 1]
                        
                        # 选择清除类型
                        while True:  # 清除类型选择循环
                            print(f"\n{'='*60}")
                            print(f"📱 账号: {account}")
                            print("请选择要清除的内容:")
                            print("  1. 清除帖子记录")
                            print("  2. 清除快拍记录")
                            print("  3. 清除全部记录（帖子和快拍）")
                            print("  B. 返回上一级")
                            print("  M. 返回主菜单")
                            print(f"{'='*60}")
                            
                            type_choice = input("请输入选项 (1/2/3/B/M): ").strip().upper()
                            
                            if type_choice == 'B':
                                print("\n⏭️  返回上一级")
                                break  # 跳出清除类型循环，回到账号选择
                            
                            if type_choice == 'M':
                                print("\n⏭️  返回主菜单")
                                return  # 返回主菜单
                            
                            if type_choice == '1':
                                if ask_yes_no(f"⚠️  确定要清除 {account} 的帖子记录?"):
                                    archive[account]["posts"] = []
                                    save_archive(archive)
                                    print(f"\n✅ 已清除 {account} 的帖子记录")
                                else:
                                    print("\n⏭️  已取消")
                                continue  # 继续显示清除类型菜单
                            
                            elif type_choice == '2':
                                if ask_yes_no(f"⚠️  确定要清除 {account} 的快拍记录?"):
                                    archive[account]["stories"] = []
                                    save_archive(archive)
                                    print(f"\n✅ 已清除 {account} 的快拍记录")
                                else:
                                    print("\n⏭️  已取消")
                                continue  # 继续显示清除类型菜单
                            
                            elif type_choice == '3':
                                if ask_yes_no(f"⚠️  确定要清除 {account} 的全部记录?"):
                                    del archive[account]
                                    save_archive(archive)
                                    print(f"\n✅ 已清除 {account} 的全部记录")
                                else:
                                    print("\n⏭️  已取消")
                                continue  # 继续显示清除类型菜单
                            
                            else:
                                print("\n❌ 输入无效")
                                continue
                        
                        # 完成账号操作后继续账号选择
                        continue
                    else:
                        print("\n❌ 输入无效")
                        continue
                except:
                    print("\n❌ 输入无效")
                    continue
        
        elif choice == 'B':
            print("\n⏭️  返回上一级")
            return  # 返回上一级（主菜单）
        
        elif choice == 'M':
            print("\n⏭️  返回主菜单")
            return  # 返回主菜单
        
        else:
            print("  请输入 1、2、B 或 M")


def validate_cookies_format(content):
    """
    验证 Cookies 格式是否正确
    
    Args:
        content: Cookies 内容
    
    Returns:
        (is_valid, message): 是否有效，提示信息
    """
    lines = content.strip().split('\n')
    
    # 检查是否为空
    if not lines or not content.strip():
        return False, "Cookies 内容为空"
    
    # 检查是否有 Netscape 格式标记
    has_netscape_header = any('# netscape' in line.lower() for line in lines[:5])
    
    # 检查是否有 sessionid（关键 cookie）
    has_sessionid = any('sessionid' in line.lower() for line in lines)
    
    # 检查是否有 csrftoken
    has_csrftoken = any('csrftoken' in line.lower() for line in lines)
    
    # 统计有效 cookie 行数（以 .instagram.com 开头）
    valid_cookie_lines = [line for line in lines if line.strip().lower().startswith('.instagram.com')]
    
    if len(valid_cookie_lines) == 0:
        return False, "未找到有效的 Instagram Cookies 行（应以 .instagram.com 开头）"
    
    if not has_sessionid:
        return False, "未找到 sessionid，Cookies 可能无效"
    
    if not has_csrftoken:
        return False, "未找到 csrftoken，Cookies 可能无效"
    
    return True, f"格式正确，找到 {len(valid_cookie_lines)} 个 Cookies"


def update_cookies_menu():
    """更新 Cookies 菜单"""
    print(f"\n{'='*60}")
    print("🍪 更新 Cookies")
    print(f"{'='*60}")
    
    # 显示当前 cookies 状态
    cookies_file = Path(config.COOKIES_FILE)
    if cookies_file.exists():
        with open(cookies_file, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        valid_lines = [line for line in lines if line.strip().lower().startswith('.instagram.com')]
        is_valid, msg = validate_cookies_format(content)
        print(f"\n📊 当前状态: {msg}")
        print(f"   文件: {config.COOKIES_FILE}")
        print(f"   行数: {len(valid_lines)} 个有效 Cookies")
    else:
        print(f"\n⚠️  当前没有 Cookies 文件")
        print(f"   文件路径: {config.COOKIES_FILE}")
    
    print(f"\n{'='*60}")
    print("请选择更新方式:")
    print("  1. 粘贴文本 - 直接粘贴 Cookies 内容")
    print("  2. 选择文件 - 从文件导入 Cookies")
    print("  B. 返回上一级")
    print("  M. 返回主菜单")
    print(f"{'='*60}")
    
    while True:
        choice = input("请输入选项 (1/2/B/M): ").strip().upper()
        
        if choice == '1':
            # 粘贴文本方式
            print(f"\n{'='*60}")
            print("📋 粘贴 Cookies 文本")
            print(f"{'='*60}")
            print("说明: 从浏览器插件（如 EditThisCookie）导出 Netscape 格式")
            print("      然后全选复制，粘贴到下方")
            print("      粘贴完成后，输入 END 并按回车结束")
            print("      输入 B 返回上一级，输入 M 返回主菜单")
            print(f"{'='*60}\n")
            
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip().upper() == 'END':
                        break
                    if line.strip().upper() == '9':
                        print("\n⏭️  返回上一级")
                        break  # 跳出输入循环
                    if line.strip().upper() == '0':
                        print("\n⏭️  返回主菜单")
                        return  # 返回主菜单
                    lines.append(line)
                except EOFError:
                    break
            
            # 如果是因为输入9而跳出，继续显示更新方式菜单
            if lines and lines[-1].strip().upper() == '9' if lines else False:
                continue
            
            content = '\n'.join(lines)
            
            if not content.strip().upper():
                print("\n⚠️  未输入任何内容，已取消")
                continue  # 继续显示菜单
            
            # 验证格式
            is_valid, msg = validate_cookies_format(content)
            print(f"\n{'='*60}")
            print(f"验证结果: {msg}")
            
            if is_valid:
                if ask_yes_no("✅ 格式正确，是否保存?"):
                    try:
                        with open(config.COOKIES_FILE, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"\n✅ Cookies 已保存到: {config.COOKIES_FILE}")
                    except Exception as e:
                        print(f"\n❌ 保存失败: {e}")
                else:
                    print("\n⏭️  已取消保存")
            else:
                print(f"\n❌ 格式错误: {msg}")
                print("建议: 请使用浏览器插件导出 Netscape 格式的 Cookies")
            
            continue  # 继续显示菜单
        
        elif choice == '2':
            # 选择文件方式
            print(f"\n{'='*60}")
            print("📁 选择 Cookies 文件")
            print(f"{'='*60}")
            print("提示: 输入文件的完整路径，例如:")
            print("     C:\\Users\\用户名\\Downloads\\instagram_cookies.txt")
            print("     或拖拽文件到此处")
            print("     输入 B 返回上一级，输入 M 返回主菜单")
            print(f"{'='*60}\n")
            
            file_path = input("请输入文件路径: ").strip().upper().strip('"')
            
            if file_path == 'B':
                print("\n⏭️  返回上一级")
                continue  # 继续显示菜单
            
            if file_path == 'M':
                print("\n⏭️  返回主菜单")
                return  # 返回主菜单
            
            if not file_path:
                print("\n⚠️  未输入路径，已取消")
                continue  # 继续显示菜单
            
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"\n❌ 文件不存在: {file_path}")
                continue  # 继续显示菜单
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 验证格式
                is_valid, msg = validate_cookies_format(content)
                print(f"\n{'='*60}")
                print(f"验证结果: {msg}")
                
                if is_valid:
                    if ask_yes_no(f"✅ 格式正确，是否导入到 {config.COOKIES_FILE}?"):
                        try:
                            with open(config.COOKIES_FILE, 'w', encoding='utf-8') as f:
                                f.write(content)
                            print(f"\n✅ Cookies 已导入")
                            print(f"   来源: {file_path}")
                            print(f"   目标: {config.COOKIES_FILE}")
                        except Exception as e:
                            print(f"\n❌ 导入失败: {e}")
                    else:
                        print("\n⏭️  已取消导入")
                else:
                    print(f"\n❌ 格式错误: {msg}")
                    print("建议: 请使用浏览器插件导出 Netscape 格式的 Cookies")
                
            except Exception as e:
                print(f"\n❌ 读取文件失败: {e}")
            
            continue  # 继续显示菜单
        
        elif choice == 'B':
            print("\n⏭️  返回上一级")
            return  # 返回上一级（主菜单）
        
        elif choice == 'M':
            print("\n⏭️  返回主菜单")
            return  # 返回主菜单
        
        else:
            print("  请输入 1、2、B 或 M")


def show_settings_menu():
    """显示当前设置"""
    settings = config.get_all_config()
    
    print(f"\n{'='*60}")
    print("⚙️  系统设置")
    print(f"{'='*60}")
    
    print("\n📁 文件路径设置:")
    print(f"   1. 下载目录: {settings['DOWNLOAD_DIR']}")
    print(f"   2. 存档文件: {settings['ARCHIVE_FILE']}")
    print(f"   3. Cookies文件: {settings['COOKIES_FILE']}")
    print(f"   4. 账号存档: {settings['ACCOUNTS_FILE']}")
    
    print("\n🌐 网络设置:")
    print(f"   5. 代理地址: {settings['PROXY']}")
    
    print("\n⏱️  性能设置:")
    print(f"   6. 请求间隔: {settings['SLEEP_REQUEST']} 秒")
    print(f"   7. 下载间隔: {settings['SLEEP_DOWNLOAD']} 秒")
    print(f"   8. 重复检测阈值: {settings['MAX_CONSECUTIVE_DUPLICATES']} 个")
    print(f"   9. 最大扫描范围: {settings['MAX_SCAN_RANGE']} 个")
    
    print(f"\n{'='*60}")
    print("操作选项:")
    print("  1-9. 修改对应设置")
    print("  R.   重置为默认设置")
    print("  B.   返回上一级")
    print("  M.   返回主菜单")
    print(f"{'='*60}")


def settings_menu():
    """系统设置菜单"""
    while True:
        show_settings_menu()
        
        choice = input("\n请输入选项 (1-9/R/B/M): ").strip().upper().upper()
        
        if choice == 'R':
            if ask_yes_no("⚠️  确定要重置所有设置为默认值?"):
                if config.reset_to_defaults():
                    config.reload_config()
                    print("\n✅ 已重置为默认设置")
                else:
                    print("\n❌ 重置失败")
            else:
                print("\n⏭️  已取消")
            continue
        
        if choice == 'B':
            print("\n⏭️  返回上一级")
            return
        
        if choice == 'M':
            print("\n⏭️  返回主菜单")
            return
        
        # 修改具体设置
        if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
            setting_map = {
                '1': ('DOWNLOAD_DIR', '下载目录', 'downloads'),
                '2': ('ARCHIVE_FILE', '存档文件', 'archive.json'),
                '3': ('COOKIES_FILE', 'Cookies文件', 'instagram_cookies.txt'),
                '4': ('ACCOUNTS_FILE', '账号存档文件', 'accounts.json'),
                '5': ('PROXY', '代理地址', 'socks5://127.0.0.1:7897'),
                '6': ('SLEEP_REQUEST', '请求间隔（格式: 最小-最大）', '30-90'),
                '7': ('SLEEP_DOWNLOAD', '下载间隔（格式: 最小-最大）', '20-60'),
                '8': ('MAX_CONSECUTIVE_DUPLICATES', '重复检测阈值', '3'),
            }
            
            key, name, default_val = setting_map[choice]
            current_val = config.get_config(key, default_val)
            
            print(f"\n{'='*60}")
            print(f"修改 {name}")
            print(f"{'='*60}")
            print(f"当前值: {current_val}")
            print(f"默认值: {default_val}")
            print("提示: 直接回车保持当前值")
            print("      输入 B 返回上一级，M 返回主菜单，Q 退出")
            print(f"{'='*60}")
            
            new_val = input(f"请输入新的{name}: ").strip()
            
            # 检查是否是导航命令（不区分大小写）
            new_val_upper = new_val.upper()
            if new_val_upper == 'B':
                print("\n⏭️  返回上一级")
                continue
            
            if new_val_upper == 'M':
                print("\n⏭️  返回主菜单")
                return
            
            # 检查是否是 Q（退出）
            if new_val_upper == 'Q':
                print("\n👋 退出程序")
                sys.exit(0)
            
            if not new_val:
                print("\n⚠️  输入为空，未修改")
                continue
            
            # 路径类型设置验证（1-4是路径设置）
            if choice in ['1', '2', '3', '4']:
                path_type = 'dir' if choice == '1' else 'file'
                
                # 对于文件类型，先检查用户输入的是否是目录路径
                if path_type == 'file':
                    path_obj = Path(new_val)
                    # 获取路径的最后一部分（文件名或目录名）
                    path_name = path_obj.name
                    # 检查是否像目录路径（以分隔符结尾或没有扩展名）
                    is_dir_like = (new_val.endswith(os.sep) or 
                                   new_val.endswith('/') or 
                                   new_val.endswith('\\') or
                                   '.' not in path_name)  # 路径名中没有点号，说明没有扩展名
                    
                    # 调试信息
                    print(f"   [调试] 路径: {new_val}, 名称: {path_name}, 像目录: {is_dir_like}")
                    
                    if is_dir_like:
                        # 可能是想创建目录，询问用户
                        print(f"\n{'='*60}")
                        print(f"⚠️  您输入的路径 '{new_val}' 看起来像是一个目录")
                        print(f"{'='*60}")
                        print("\n请选择操作:")
                        print(f"  1. 在该目录下创建默认文件 ({path_obj / default_val})")
                        print(f"  2. 重新输入文件路径")
                        print(f"  B. 返回上一级")
                        print(f"{'='*60}")
                        
                        dir_choice = input("请输入选项 (1/2/B): ").strip().upper()
                        
                        if dir_choice == 'B':
                            print("\n⏭️  返回上一级")
                            continue
                        elif dir_choice == '1':
                            # 使用默认文件名
                            new_val = str(path_obj / default_val)
                            print(f"\n✅ 已设置路径: {new_val}")
                        elif dir_choice == '2':
                            print("\n⏭️  请重新输入")
                            continue
                        else:
                            print("\n❌ 无效选项，请重新输入")
                            continue
                
                is_valid, fixed_path, message = validate_and_fix_path(new_val, path_type, create_if_missing=True)
                
                print(f"\n{'='*60}")
                if is_valid:
                    print(f"✅ {message}")
                    if fixed_path != new_val:
                        print(f"   路径已修正: {new_val} → {fixed_path}")
                        new_val = fixed_path
                else:
                    print(f"❌ {message}")
                    print(f"{'='*60}")
                    print("\n请重新输入，或输入 B 返回上一级")
                    continue
                print(f"{'='*60}")
            
            # 验证输入
            if choice in ['6', '7']:  # 时间间隔格式验证
                if not re.match(r'^\d+-\d+$', new_val):
                    print("\n❌ 格式错误，应为: 最小值-最大值（例如: 30-90）")
                    continue
            
            if choice == '8':  # 数字验证
                try:
                    int(new_val)
                except:
                    print("\n❌ 请输入数字")
                    continue
            
            # 保存设置
            if config.set_config(key, new_val):
                config.reload_config()
                print(f"\n✅ {name}已修改:")
                print(f"   {current_val} → {new_val}")
                print(f"   已保存到: {config.CONFIG_FILE}")
            else:
                print(f"\n❌ 保存失败")
            continue
        
        print("  请输入 1-9、R、B 或 M")


def configure_sleep_settings(auto_mode=False):
    """
    配置休眠时间设置
    
    Args:
        auto_mode: 是否为自动模式（非交互式）
    
    Returns:
        (request_sleep, download_sleep): 请求休眠时间和下载休眠时间（秒）
    """
    if auto_mode:
        # 自动模式使用默认配置
        return config.SLEEP_REQUEST, config.SLEEP_DOWNLOAD
    
    print(f"\n{'='*60}")
    print("⏱️  休眠时间配置")
    print(f"{'='*60}")
    print("\n📖 为什么需要休眠时间？")
    print("   Instagram 有反爬虫机制，短时间内大量请求会导致：")
    print("   • 临时限制访问（需要等待几小时）")
    print("   • 账号被标记为异常活动")
    print("   • IP 地址被封禁")
    print("   • 账号被暂时或永久封禁")
    print("\n💡 建议：")
    print("   • 首次测试或少量内容：可以不启用休眠")
    print("   • 日常使用：建议启用推荐设置")
    print("   • 大量下载：增加休眠时间更安全")
    
    print(f"\n{'='*60}")
    choice = input("\n是否启用请求休眠? (y/n/推荐): ").strip().upper().lower()
    
    if choice == '推荐' or choice == 'r':
        # 使用推荐设置
        request_sleep = (30, 90)
        download_sleep = (5, 15)
        print(f"\n✅ 已启用推荐设置：")
        print(f"   • 请求间隔: {request_sleep[0]}-{request_sleep[1]} 秒")
        print(f"   • 下载间隔: {download_sleep[0]}-{download_sleep[1]} 秒")
        return request_sleep, download_sleep
    
    elif choice == 'y' or choice == 'yes':
        # 自定义设置
        print(f"\n{'='*60}")
        print("📊 请求间隔设置（扫描帖子、快拍之间）")
        print(f"{'='*60}")
        print("推荐值: 30-90 秒")
        print("说明: 每次向 Instagram 服务器发送请求后的等待时间")
        print("      包括：扫描帖子后、扫描快拍后、切换账号前")
        
        try:
            req_min = int(input(f"\n请求间隔最小值 (秒) [推荐30]: ") or "30")
            req_max = int(input(f"请求间隔最大值 (秒) [推荐90]: ") or "90")
            request_sleep = (max(0, req_min), max(req_min, req_max))
        except:
            print("   ⚠️  输入无效，使用推荐值 30-90 秒")
            request_sleep = (30, 90)
        
        print(f"\n{'='*60}")
        print("📊 下载间隔设置（下载操作之间）")
        print(f"{'='*60}")
        print("推荐值: 5-15 秒")
        print("说明: 下载操作完成后的等待时间")
        print("      包括：下载帖子后、下载快拍后")
        
        try:
            dl_min = int(input(f"\n下载间隔最小值 (秒) [推荐5]: ") or "5")
            dl_max = int(input(f"下载间隔最大值 (秒) [推荐15]: ") or "15")
            download_sleep = (max(0, dl_min), max(dl_min, dl_max))
        except:
            print("   ⚠️  输入无效，使用推荐值 5-15 秒")
            download_sleep = (5, 15)
        
        print(f"\n✅ 已设置自定义休眠：")
        print(f"   • 请求间隔: {request_sleep[0]}-{request_sleep[1]} 秒")
        print(f"   • 下载间隔: {download_sleep[0]}-{download_sleep[1]} 秒")
        return request_sleep, download_sleep
    
    else:
        # 不启用休眠
        print(f"\n⏭️  已禁用休眠（快速模式）")
        print("   ⚠️  注意：频繁使用可能导致账号被限制")
        return (0, 0), (0, 0)


def run_scan_and_download(scan_only_mode=False, auto_mode=False):
    """
    执行扫描和下载流程
    
    Args:
        scan_only_mode: 是否仅扫描
        auto_mode: 是否自动模式
    """
    # 配置休眠时间
    request_sleep, download_sleep = configure_sleep_settings(auto_mode)
    
    # 将休眠设置保存到全局，供其他函数使用
    import builtins
    builtins.REQUEST_SLEEP = request_sleep
    builtins.DOWNLOAD_SLEEP = download_sleep
    
    # 询问扫描范围（仅扫描模式下）
    scan_range = None
    if scan_only_mode and not auto_mode:
        print(f"\n{'='*60}")
        print("📏 扫描范围设置")
        print(f"{'='*60}")
        print("说明: 限制扫描的媒体文件数量，可以加快建档速度")
        print("      建议首次建档扫描 10-20 个即可")
        print("      输入数字指定范围，或直接回车不限制")
        print(f"{'='*60}")
        
        range_input = input("\n请输入扫描范围 (默认不限制): ").strip()
        if range_input.isdigit():
            scan_range = int(range_input)
            print(f"  ✅ 将扫描前 {scan_range} 个媒体文件")
        else:
            print(f"  ⏭️  不限制扫描范围")
    
    # 检查是否有账号
    if not config.ACCOUNTS:
        print(f"\n{'='*60}")
        print("⚠️  没有监控账号")
        print(f"{'='*60}")
        print("请先添加至少一个账号：")
        print("  1. 返回主菜单")
        print("  2. 进入账号管理")
        print(f"{'='*60}")
        choice = input("请输入选项 (1/2): ").strip()
        if choice == '2':
            manage_accounts_menu()
        return
    
    # 询问是否开始扫描
    print(f"\n{'='*60}")
    if not ask_yes_no("🤔 是否开始扫描?", auto_mode=auto_mode or scan_only_mode):
        print("  已取消扫描")
        return
    
    archive = load_archive()
    
    # 记录每个账号的操作结果
    account_results = {}
    
    for account in config.ACCOUNTS:
        # 初始化账号结果记录
        account_results[account] = {
            "new_posts": [],
            "new_stories": [],
            "archived": False,
            "downloaded": False
        }
        
        all_new, new_posts, new_stories = check_account(account, archive, scan_range)
        
        # 记录扫描结果
        account_results[account]["new_posts"] = new_posts
        account_results[account]["new_stories"] = new_stories
        
        if all_new:
            # 计算唯一帖子数量
            unique_post_count = len(set(m.get("post_id", m["id"].split('_')[0]) for m in new_posts))
            print(f"\n  [新内容] 发现 {len(all_new)} 个新内容")
            print(f"     新帖子: {unique_post_count} 个帖子 ({len(new_posts)} 个媒体文件)")
            print(f"     新快拍: {len(new_stories)} 个")
            
            # 询问是否更新存档
            print(f"\n{'='*60}")
            if ask_yes_no(f"💾 是否将新内容记录到存档?", auto_mode=auto_mode or scan_only_mode):
                update_archive(account, new_posts, new_stories)
                account_results[account]["archived"] = True
                print(f"  ✅ 已更新存档")
            else:
                print(f"  ⏭️  跳过存档更新")
            
            # 仅扫描模式下跳过下载
            if scan_only_mode:
                print(f"\n  ⏭️  仅扫描模式: 跳过下载")
            else:
                # 询问是否下载
                print(f"\n{'='*60}")
                if ask_yes_no(f"📥 是否下载这些新内容?", auto_mode=auto_mode):
                    print(f"\n  [开始下载] 账号: {account}")
                    # 计算正确的range：从第一个新内容的media_index到最后一个
                    if new_posts:
                        min_media_index = min(m.get("media_index", 0) for m in new_posts)
                        max_media_index = max(m.get("media_index", 0) for m in new_posts)
                        print(f"     📊 新内容媒体位置范围: {min_media_index}-{max_media_index}")
                        # 使用正确的range参数
                        posts_range = (min_media_index, max_media_index)
                    else:
                        posts_range = None
                    posts_ok, stories_ok = download_content_v2(
                        account, 
                        posts_range,  # 使用正确的range (start, end)
                        len(new_stories)
                    )
                    
                    if posts_ok and stories_ok:
                        account_results[account]["downloaded"] = True
                        print(f"\n  ✅ 全部下载完成")
                    else:
                        print(f"\n  ⚠️  部分下载可能失败")
                else:
                    print(f"  ⏭️  跳过下载")
        else:
            print(f"\n  ℹ️  没有发现新内容，无需更新")
    
    # 账号切换前的休眠（如果不是最后一个账号）
    if account != config.ACCOUNTS[-1]:
        if hasattr(__builtins__, 'REQUEST_SLEEP') and REQUEST_SLEEP[1] > 0:
            sleep_time = random.randint(REQUEST_SLEEP[0], REQUEST_SLEEP[1])
            sleep_with_progress_bar(sleep_time, "切换账号间隔")
    
    # 显示操作总结
    print(f"\n{'='*60}")
    print(f"📋 操作总结:")
    print(f"{'='*60}")
    print(f"  📱 账号: {', '.join(config.ACCOUNTS)}")
    print(f"  🔍 扫描模式: {'仅扫描' if scan_only_mode else '扫描并下载'}")
    
    # 显示每个账号的操作详情
    for account in config.ACCOUNTS:
        result = account_results[account]
        new_posts = result["new_posts"]
        new_stories = result["new_stories"]
        
        print(f"\n  📱 {account}:")
        
        # 扫描结果
        if new_posts or new_stories:
            unique_posts = len(set(m.get("post_id", m["id"].split('_')[0]) for m in new_posts))
            print(f"     � 扫描到: {unique_posts} 个新帖子 ({len(new_posts)} 个媒体文件), {len(new_stories)} 个新快拍")
        else:
            print(f"     🔍 未发现新内容")
        
        # 存档状态
        if result["archived"]:
            print(f"     💾 存档: 已更新")
        else:
            print(f"     💾 存档: 未更新")
        
        # 下载状态
        if scan_only_mode:
            print(f"     📥 下载: 已跳过 (仅扫描模式)")
        elif result["downloaded"]:
            print(f"     📥 下载: 已完成")
        elif new_posts or new_stories:
            print(f"     📥 下载: 未执行")
        else:
            print(f"     � 下载: 无需下载")
    
    print(f"\n{'='*60}")
    print(f"✅ 扫描完成")


def show_help():
    """显示使用说明"""
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║              📘 Instagram 内容监控 - 使用说明                ║
╠══════════════════════════════════════════════════════════════╣
║  核心功能:                                                   ║
║    • 扫描 Instagram 账号的新帖子(Posts)和快拍(Stories)       ║
║    • 自动检测重复内容，避免重复下载                          ║
║    • 支持仅扫描存档或扫描并下载两种模式                      ║
║                                                              ║
║  菜单导航:                                                   ║
║    B = 返回上一级    M = 返回主菜单    Q = 退出程序          ║
║                                                              ║
║  运行模式:                                                   ║
║    1. 仅扫描存档 - 快速建立存档，不下载文件                  ║
║    2. 扫描并下载 - 检测新内容并下载到本地                    ║
║    3. 清除存档   - 管理或删除存档记录                        ║
║    4. 更新 Cookies - 更新 Instagram 登录凭证                 ║
║    5. 管理账号   - 添加或删除监控账号                        ║
║    6. 系统设置   - 修改文件路径和扫描参数                    ║
║                                                              ║
║  首次使用步骤:                                               ║
║    ① 选择数据存储位置（当前目录或自定义路径）               ║
║    ② 进入"系统设置"(模式6)配置代理IP                        ║
║    ③ 进入"更新 Cookies"(模式4)导入登录凭证                  ║
║    ④ 进入"管理账号"(模式5)添加监控账号                      ║
║    ⑤ 使用"仅扫描存档"(模式1)建立初始存档                    ║
║    ⑥ 后续使用"扫描并下载"(模式2)获取新内容                  ║
║                                                              ║
║  使用提示:                                                   ║
║    • 首次使用请先添加监控账号(模式5)                         ║
║    • 建议首次使用"仅扫描存档"模式建立初始存档                ║
║    • 扫描范围可限制前N个媒体文件，加快建档速度               ║
║    • 休眠时间设置可避免触发 Instagram 反爬机制               ║
║    • 如遇权限问题，选择"以管理员权限重新运行"                ║
║                                                              ║
║  文件说明:                                                   ║
║    • archive.json    - 存储已下载内容ID(自动创建)            ║
║    • accounts.json   - 存储监控账号列表(自动创建)            ║
║    • settings.json   - 存储系统配置参数(自动创建)            ║
║    • downloads/      - 下载内容保存目录                      ║
║                                                              ║
║  项目创建人: ForMooN-0118                                    ║
║  项目地址: https://github.com/ForMooN-0118                   ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(help_text)


def main():
    """主函数 - 循环显示菜单直到退出"""
    # 检查命令行参数
    auto_mode = "--auto" in sys.argv or "-a" in sys.argv
    scan_only_mode = "--scan-only" in sys.argv or "-s" in sys.argv
    show_help_flag = "--help" in sys.argv or "-h" in sys.argv
    
    # 显示帮助信息
    if show_help_flag:
        show_help()
        return
    
    # 显示配置文件初始化结果（由config.py自动创建）
    if config.INIT_RESULTS:
        print(f"\n{'='*60}")
        print("🔧 初始化检查...")
        for result in config.INIT_RESULTS:
            print(f"   {result}")
        print(f"{'='*60}")
        
        # 首次使用提示
        print(f"\n{'='*60}")
        print("📋 欢迎使用 ForMooN-0118 IGDownloader beta V0.1")
        print("📋 首次使用指南")
        print(f"{'='*60}")
        print("请按以下步骤完成初始化:")
        print("  1. 选择数据存储位置（当前界面）")
        print("  2. 进入系统设置(主菜单选项6)配置代理IP")
        print("  3. 进入更新Cookies(主菜单选项4)导入登录凭证")
        print("  4. 进入管理账号(主菜单选项5)添加监控账号")
        print("  5. 使用仅扫描存档(主菜单选项1)建立初始存档")
        print(f"{'='*60}")
    
    # 显示软件标题
    print(f"\n{'='*60}")
    print("🚀 ForMooN-0118-beta-v0.1")
    print("   Instagram 内容下载工具")
    print(f"{'='*60}")
    
    # 显示当前数据存储位置
    current_data_dir = config.get_data_dir()
    print(f"\n📁 当前数据存储位置: {current_data_dir.absolute()}")
    
    # 命令行模式直接执行后退出
    if auto_mode or scan_only_mode:
        if scan_only_mode:
            print(f"\n🚀 Instagram 内容监控 - 仅扫描存档模式")
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📋 账号列表: {', '.join(config.ACCOUNTS)}")
            print(f"\n⚠️  仅扫描模式: 只扫描并记录存档，不下载任何内容")
            print(f"     用于初始化存档或更新现有存档")
        else:
            print(f"\n🚀 Instagram 内容监控 - 扫描并下载")
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📋 账号列表: {', '.join(config.ACCOUNTS)}")
            print(f"\n⚠️  自动模式: 将自动执行扫描、存档和下载")
        
        run_scan_and_download(scan_only_mode=scan_only_mode, auto_mode=auto_mode)
        print(f"\n{'='*60}")
        print(f"✅ 程序执行完成")
        return
    
    # 交互式模式 - 每次运行都显示使用说明
    show_help()
    
    # 交互式模式 - 循环显示菜单
    while True:
        print(f"\n🚀 Instagram 内容监控")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 账号列表 ({len(config.ACCOUNTS)} 个): {', '.join(config.ACCOUNTS)}")
        
        mode = select_mode()
        
        if mode == 'exit':
            print("\n👋 程序退出")
            break
        elif mode == 'scan_only':
            print(f"\n⚠️  已选择: 仅扫描存档模式")
            run_scan_and_download(scan_only_mode=True, auto_mode=False)
        elif mode == 'full':
            print(f"\n⚠️  已选择: 扫描并下载模式")
            run_scan_and_download(scan_only_mode=False, auto_mode=False)
        elif mode == 'manual_download':
            # 手动下载链接模式
            result = download_from_url_menu()
            if result == 'main_menu':
                continue  # 直接继续循环，显示主菜单
        elif mode == 'clear_archive':
            # 清除存档模式
            clear_archive_menu()
        elif mode == 'update_cookies':
            # 更新 Cookies 模式
            update_cookies_menu()
        elif mode == 'manage_accounts':
            # 账号管理模式
            manage_accounts_menu()
        elif mode == 'settings':
            # 系统设置模式
            settings_menu()
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

