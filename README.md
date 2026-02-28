# ForMooN-0118 IGDownloader

Instagram 内容监控与下载工具 - 自动监控指定账号的新内容（帖子、快拍、Reels），智能去重下载。

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📋 功能特点

- ✅ **自动监控** - 检测指定 Instagram 账号的新帖子、快拍、Reels
- ✅ **智能去重** - 自动识别已下载内容，避免重复下载
- ✅ **分类存储** - 按账号和类型（posts/stories/reels）分类保存
- ✅ **元数据提取** - 自动提取并保存标题、时间、点赞数等信息到 TXT 文件
- ✅ **手动下载** - 支持直接输入 URL 下载指定内容
- ✅ **灵活配置** - 支持自定义数据目录、代理设置、扫描范围
- ✅ **防封号机制** - 智能请求间隔，避免触发 Instagram 限制
- ✅ **打包便携** - 支持打包为独立可执行文件，无需 Python 环境

## 🚀 快速开始

### 下载程序

1. 从 [Releases](https://github.com/ForMooN-0118/IGDownloader-beta-v1/releases) 下载最新版本
2. 解压到任意目录

### 首次使用

**方式一：使用可执行文件（推荐）**
```bash
IGDownloader.exe
```

**方式二：使用 Python 运行**
```bash
# 克隆仓库
git clone https://github.com/ForMooN-0118/IGDownloader-beta-v1.git
cd IGDownloader

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行程序
python instagram_monitor.py
```

## 📖 详细使用指南

### 1. 初始化设置

首次运行时会显示软件标题和当前数据存储位置：

```
============================================================
🚀 ForMooN-0118-beta-v0.1
   Instagram 内容下载工具
============================================================

📁 当前数据存储位置: C:\Users\...\IGDownloader
```

### 2. 配置代理（必需）

进入系统设置（主菜单选项 6）：
- 默认使用 `socks5://127.0.0.1:7897`
- 根据你的网络环境修改为实际代理地址
- 支持 HTTP/HTTPS/SOCKS5 代理

### 3. 导入 Cookies（必需）

进入更新 Cookies（主菜单选项 4）：

**方法：从浏览器导出**
1. 安装浏览器扩展（如 EditThisCookie 或 Cookie-Editor）
2. 登录 Instagram 网页版
3. 导出 cookies 为 Netscape 格式
4. 将内容粘贴到程序中，或保存到 `instagram_cookies.txt` 文件

**注意事项：**
- Cookies 需要包含 `sessionid`、`ds_user_id` 等关键字段
- Cookies 会过期，需要定期更新

### 4. 添加监控账号

进入管理账号（主菜单选项 5）：
- 输入 Instagram 账号用户名（如 `instagram`）
- 可添加多个账号进行监控
- 支持删除和查看已添加的账号

### 5. 建立初始存档

使用仅扫描存档（主菜单选项 1）：
- 设置扫描范围（建议首次 10-20 个媒体文件）
- 程序会扫描现有内容并建立存档记录
- 避免首次下载时重复下载历史内容

### 6. 开始自动监控

使用扫描并下载（主菜单选项 2）：
- 自动检测所有监控账号的新内容
- 自动下载新帖子、快拍
- 智能跳过已下载内容

## 📁 文件说明

### 程序文件

| 文件 | 说明 |
|------|------|
| `IGDownloader.exe` | 可执行文件（打包后生成） |
| `instagram_monitor.py` | 主程序源码 |
| `config.py` | 配置管理模块 |
| `IGDownloader.spec` | PyInstaller 打包配置 |
| `build_exe.py` | 一键打包脚本 |
| `requirements.txt` | Python 依赖列表 |

### 数据文件

数据目录下会自动创建以下文件：

| 文件 | 用途 |
|------|------|
| `accounts.json` | 存储监控账号列表 |
| `archive.json` | 存储已下载内容ID（去重用） |
| `settings.json` | 存储系统配置参数 |
| `instagram_cookies.txt` | Instagram 登录凭证 |
| `downloads/` | 下载内容保存目录 |
| `.initialized` | 初始化标志文件 |

## 🔧 配置说明

### 系统设置（主菜单选项 6）

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| 代理地址 | 网络代理设置 | `socks5://127.0.0.1:7897` |
| 下载目录 | 内容保存位置 | `downloads/` |
| 存档文件 | 去重记录文件 | `archive.json` |
| 最大重复检测 | 连续重复停止阈值 | `3` |
| 最大扫描范围 | 单次扫描限制 | `50` |

### 休眠时间配置

在扫描时可选择启用休眠：
- **推荐设置** - 适合日常使用，平衡速度和安全性
- **自定义** - 手动设置请求间隔（秒）
- **不启用** - 最快速度，但风险较高

## 📦 自行打包

如需自行打包为可执行文件：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 执行打包脚本
python build_exe.py

# 或手动打包
python -m PyInstaller IGDownloader.spec --clean
```

打包完成后，`dist/IGDownloader.exe` 即为独立可执行文件。

## ⚠️ 注意事项

- **首次使用** - 建议先使用"仅扫描存档"模式建立初始存档
- **扫描范围** - 可限制前 N 个媒体文件，加快建档速度
- **休眠时间** - 合理设置请求间隔，避免触发反爬机制
- **权限问题** - 如遇权限错误，可尝试"以管理员权限重新运行"
- **数据目录** - 建议选择空间充足的磁盘，下载内容会占用较多空间
- **Cookies 更新** - 定期更新 Cookies 以保持登录状态

## 🐛 常见问题

### Q: 程序无法启动或闪退
A: 检查是否安装了必要的依赖，或使用打包后的可执行文件。

### Q: 扫描失败或超时
A: 
1. 检查代理设置是否正确
2. 检查 Cookies 是否有效
3. 增加超时时间或减小扫描范围

### Q: 下载内容不完整
A: 
1. 检查网络连接稳定性
2. 检查磁盘空间是否充足
3. 尝试重新扫描下载

### Q: 遇到"无法打开数据库文件"错误
A: 这是 gallery-dl 的缓存问题，程序会自动处理，如持续出现请重启程序。

## 📝 更新日志

### v0.1.0-beta (2026-02-28)
- ✨ 初始版本发布
- ✨ 支持帖子、快拍监控下载
- ✨ 智能去重和分类存储
- ✨ 元数据提取和保存
- ✨ 支持打包为可执行文件

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证开源。

## 👤 作者

**ForMooN-0118**

- GitHub: [@ForMooN-0118](https://github.com/ForMooN-0118)
- 项目地址: https://github.com/ForMooN-0118/IGDownloader-beta-v0.1

## ⚖️ 免责声明

- 本工具仅供学习和个人使用
- 请遵守 Instagram 的使用条款和相关法律法规
- 下载的内容版权归原作者所有
- 使用本工具产生的任何后果由使用者自行承担

---

⭐ 如果这个项目对你有帮助，欢迎 Star 支持！
