#!/usr/bin/env python3
"""
配置文件 - Instagram 内容监控
支持动态修改配置和数据目录选择
"""

import json
import os
from pathlib import Path

# 配置文件路径（固定在当前目录）
CONFIG_FILE = "settings.json"

# 数据目录配置文件（存储用户选择的数据目录）
DATA_DIR_CONFIG = ".data_dir"

# 默认配置
DEFAULT_CONFIG = {
    # 数据存储目录（空表示使用当前目录）
    "DATA_DIR": "",
    
    # 账号存档文件（相对于DATA_DIR）
    "ACCOUNTS_FILE": "accounts.json",
    
    # 下载设置（相对于DATA_DIR）
    "DOWNLOAD_DIR": "downloads",
    "ARCHIVE_FILE": "archive.json",
    "COOKIES_FILE": "instagram_cookies.txt",
    
    # 代理设置
    "PROXY": "socks5://127.0.0.1:7897",
    
    # 请求间隔（秒）- 防止触发 Instagram 限制
    "SLEEP_REQUEST": "30-90",
    "SLEEP_DOWNLOAD": "20-60",
    
    # 重复检测设置
    "MAX_CONSECUTIVE_DUPLICATES": 3,
    "MAX_SCAN_RANGE": 50,
}


def get_data_dir():
    """获取数据存储目录"""
    # 首先检查环境变量（用于打包后的EXE）
    env_dir = os.environ.get('IGDOWNLOADER_DATA_DIR', '')
    if env_dir and Path(env_dir).exists():
        return Path(env_dir)
    
    # 然后检查配置文件
    if Path(DATA_DIR_CONFIG).exists():
        try:
            with open(DATA_DIR_CONFIG, 'r', encoding='utf-8') as f:
                data_dir = f.read().strip()
                if data_dir and Path(data_dir).exists():
                    return Path(data_dir)
        except:
            pass
    
    # 最后检查settings.json中的配置
    settings = load_settings()
    data_dir = settings.get('DATA_DIR', '')
    if data_dir and Path(data_dir).exists():
        return Path(data_dir)
    
    # 默认使用当前目录
    return Path('.')


def set_data_dir(data_dir):
    """设置数据存储目录"""
    data_dir_path = Path(data_dir)
    
    # 确保目录存在
    if not data_dir_path.exists():
        try:
            data_dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"无法创建目录: {e}"
    
    # 测试目录写入权限
    try:
        test_file = data_dir_path / '.write_test'
        test_file.write_text('test', encoding='utf-8')
        test_file.unlink()
    except PermissionError:
        return False, f"权限错误: 无法在 '{data_dir_path}' 中创建文件\n建议: 使用用户目录，如 D:\\MyData\\insdownload"
    except Exception as e:
        return False, f"写入测试失败: {e}"
    
    # 保存到配置文件
    try:
        with open(DATA_DIR_CONFIG, 'w', encoding='utf-8') as f:
            f.write(str(data_dir_path.absolute()))
        
        # 同时更新settings.json
        set_config('DATA_DIR', str(data_dir_path.absolute()))
        
        return True, str(data_dir_path.absolute())
    except Exception as e:
        return False, f"保存配置失败: {e}"


def resolve_path(filename):
    """将相对路径解析为基于数据目录的绝对路径"""
    data_dir = get_data_dir()
    return data_dir / filename


def load_settings():
    """从配置文件加载设置"""
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
    return {}


def save_settings(settings):
    """保存设置到配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False


def get_config(key, default=None):
    """获取配置项"""
    settings = load_settings()
    return settings.get(key, DEFAULT_CONFIG.get(key, default))


def set_config(key, value):
    """设置配置项"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)


def reset_to_defaults():
    """重置为默认配置"""
    return save_settings(DEFAULT_CONFIG.copy())


def get_all_config():
    """获取所有配置（合并默认和用户设置）"""
    config = DEFAULT_CONFIG.copy()
    config.update(load_settings())
    return config


# 初始化配置
_settings = get_all_config()

# 导出配置变量（保持向后兼容）
ACCOUNTS_FILE = _settings["ACCOUNTS_FILE"]
DOWNLOAD_DIR = _settings["DOWNLOAD_DIR"]
ARCHIVE_FILE = _settings["ARCHIVE_FILE"]
COOKIES_FILE = _settings["COOKIES_FILE"]
PROXY = _settings["PROXY"]
SLEEP_REQUEST = _settings["SLEEP_REQUEST"]
SLEEP_DOWNLOAD = _settings["SLEEP_DOWNLOAD"]
MAX_CONSECUTIVE_DUPLICATES = _settings["MAX_CONSECUTIVE_DUPLICATES"]
MAX_SCAN_RANGE = _settings["MAX_SCAN_RANGE"]


def reload_config():
    """重新加载配置"""
    global ACCOUNTS_FILE, DOWNLOAD_DIR, ARCHIVE_FILE, COOKIES_FILE
    global PROXY, SLEEP_REQUEST, SLEEP_DOWNLOAD
    global MAX_CONSECUTIVE_DUPLICATES, MAX_SCAN_RANGE
    
    _settings = get_all_config()
    
    ACCOUNTS_FILE = _settings["ACCOUNTS_FILE"]
    DOWNLOAD_DIR = _settings["DOWNLOAD_DIR"]
    ARCHIVE_FILE = _settings["ARCHIVE_FILE"]
    COOKIES_FILE = _settings["COOKIES_FILE"]
    PROXY = _settings["PROXY"]
    SLEEP_REQUEST = _settings["SLEEP_REQUEST"]
    SLEEP_DOWNLOAD = _settings["SLEEP_DOWNLOAD"]
    MAX_CONSECUTIVE_DUPLICATES = _settings["MAX_CONSECUTIVE_DUPLICATES"]
    MAX_SCAN_RANGE = _settings["MAX_SCAN_RANGE"]


# ========== 账号管理 ==========

def load_accounts():
    """从存档加载账号列表"""
    data_dir = get_data_dir()
    accounts_file = data_dir / get_config("ACCOUNTS_FILE", "accounts.json")
    if accounts_file.exists():
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("accounts", [])
        except:
            return []
    return []


def save_accounts(accounts):
    """保存账号列表到存档"""
    data_dir = get_data_dir()
    accounts_file = data_dir / get_config("ACCOUNTS_FILE", "accounts.json")
    try:
        # 确保父目录存在
        accounts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(accounts_file, 'w', encoding='utf-8') as f:
            json.dump({"accounts": accounts}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存账号失败: {e}")
        return False


# 要监控的 Instagram 账号列表（从存档加载）
# 如果存档不存在，使用默认账号初始化
DEFAULT_ACCOUNTS = [
    "zhaosibo46",
    # 添加更多账号，例如:
    # "instagram",
    # "natgeo",
]

# 加载存档的账号
ACCOUNTS = load_accounts()

# 如果存档文件不存在（第一次运行），使用默认账号并创建存档
if not Path(ACCOUNTS_FILE).exists():
    ACCOUNTS = DEFAULT_ACCOUNTS.copy()
    save_accounts(ACCOUNTS)


def init_all_files(data_dir=None):
    """初始化所有必要的文件和目录（用于首次运行或打包后的EXE）
    
    Args:
        data_dir: 指定的数据目录，None则使用get_data_dir()
    """
    created_files = []
    
    # 确定数据目录
    if data_dir is None:
        data_dir = get_data_dir()
    else:
        data_dir = Path(data_dir)
    
    # 确保数据目录存在
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            created_files.append(f"✅ 创建数据目录: {data_dir}")
        except Exception as e:
            created_files.append(f"❌ 无法创建数据目录: {e}")
            return created_files
    
    # 测试目录写入权限
    try:
        test_file = data_dir / '.write_test'
        test_file.write_text('test', encoding='utf-8')
        test_file.unlink()
    except PermissionError:
        created_files.append(f"❌ 权限错误: 无法在 '{data_dir}' 中创建文件")
        created_files.append(f"   建议: 使用用户目录，如 D:\\MyData\\insdownload")
        return created_files
    except Exception as e:
        created_files.append(f"❌ 写入测试失败: {e}")
        return created_files
    
    # 1. 创建设置文件（固定在当前目录）
    settings_path = Path(CONFIG_FILE)
    if not settings_path.exists():
        if save_settings(DEFAULT_CONFIG.copy()):
            created_files.append(f"✅ 创建设置文件: {CONFIG_FILE}")
    
    # 2. 创建账号文件（在数据目录）
    accounts_path = data_dir / ACCOUNTS_FILE
    if not accounts_path.exists():
        try:
            accounts_path.write_text(json.dumps({"accounts": DEFAULT_ACCOUNTS.copy()}, indent=2, ensure_ascii=False), encoding='utf-8')
            created_files.append(f"✅ 创建账号文件: {accounts_path}")
        except Exception as e:
            created_files.append(f"❌ 无法创建账号文件: {e}")
    
    # 3. 创建下载目录（在数据目录）
    download_path = data_dir / DOWNLOAD_DIR
    if not download_path.exists():
        try:
            download_path.mkdir(parents=True, exist_ok=True)
            created_files.append(f"✅ 创建下载目录: {download_path}")
        except Exception as e:
            created_files.append(f"❌ 无法创建下载目录: {e}")
    
    # 4. 创建存档文件（在数据目录）
    archive_path = data_dir / ARCHIVE_FILE
    if not archive_path.exists():
        try:
            archive_path.write_text('{}', encoding='utf-8')
            created_files.append(f"✅ 创建存档文件: {archive_path}")
        except Exception as e:
            created_files.append(f"❌ 无法创建存档文件: {e}")
    
    # 5. 创建cookies文件（在数据目录）
    cookies_path = data_dir / COOKIES_FILE
    if not cookies_path.exists():
        try:
            cookies_path.write_text('', encoding='utf-8')
            created_files.append(f"✅ 创建Cookies文件: {cookies_path}")
        except Exception as e:
            created_files.append(f"❌ 无法创建Cookies文件: {e}")
    
    # 显示数据目录位置
    if data_dir != Path('.'):
        created_files.append(f"📁 数据存储位置: {data_dir.absolute()}")
    
    # 6. 创建初始化标志文件（标记已完成首次初始化）
    init_flag_path = data_dir / '.initialized'
    if not init_flag_path.exists():
        try:
            init_flag_path.write_text(datetime.now().isoformat(), encoding='utf-8')
            created_files.append(f"✅ 首次初始化完成")
        except Exception as e:
            created_files.append(f"❌ 无法创建初始化标志: {e}")
    
    return created_files


def is_first_run():
    """检查是否是首次运行（通过检查初始化标志文件）"""
    data_dir = get_data_dir()
    init_flag_path = data_dir / '.initialized'
    return not init_flag_path.exists()


# 自动初始化所有文件（导入时执行）
INIT_RESULTS = init_all_files()
