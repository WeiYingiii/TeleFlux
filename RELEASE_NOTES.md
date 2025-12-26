# TeleFlux v1.0.0 - 首次发布 🎉

## 📦 下载

- **源码 (tar.gz)**: [TeleFlux-v1.0.0.tar.gz](../../releases/download/v1.0.0/TeleFlux-v1.0.0.tar.gz)
- **源码 (zip)**: [TeleFlux-v1.0.0.zip](../../releases/download/v1.0.0/TeleFlux-v1.0.0.zip)

## 🎊 首次发布

这是 TeleFlux 的首个正式版本,一个功能完整的 Telegram 文件自动下载机器人!

## ✨ 主要功能

### 🎯 自动分类下载
- 🎵 音乐文件自动保存到 Music 目录
- 🎬 视频文件自动保存到 Video 目录  
- 📄 其他文件自动保存到 Download 目录

### 🧹 智能文件名处理
- 音乐文件按 "歌名-歌手" 格式命名
- 视频文件自动提取关键词(超过7字自动精简)
- 自动清理特殊字符和广告信息
- 搜索不到关键词时保留原名

### 🔄 重复文件处理
- 自动检测重复文件
- 提供三个选项:
  - ♻️ 覆盖下载
  - ➕ 加序号保存
  - ❌ 取消下载

### 📊 下载控制
- 实时进度条显示(百分比 + 大小)
- ⏸ 暂停/继续下载
- ❌ 取消下载(自动清理临时文件)
- 无文件大小限制
- 支持大文件下载(MTProto)
- 断点续传(容器重启可恢复)

### 🐳 容器化部署
- 完整的 Docker 支持
- Docker Compose 一键部署
- 可自定义文件保存路径
- 持久化存储

## 📋 快速开始

### 1. 获取代码

```bash
git clone https://github.com/WeiYingiii/TeleFlux.git
cd TeleFlux
```

### 2. 配置参数

```bash
cp .env.example .env
nano .env
```

填入你的配置:
```env
API_ID=你的_API_ID
API_HASH=你的_API_HASH
BOT_TOKEN=你的_BOT_TOKEN
```

### 3. 快速部署

```bash
chmod +x deploy.sh
./deploy.sh
```

或使用 Docker Compose:

```bash
docker build -t teleflux:latest .
docker-compose up -d
```

详细安装步骤请查看 [INSTALL.md](INSTALL.md)

## 📚 文档

- [README.md](README.md) - 项目介绍和使用说明
- [INSTALL.md](INSTALL.md) - 详细安装指南
- [CHANGELOG.md](CHANGELOG.md) - 版本更新日志
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构说明

## 🔧 配置说明

### 必需参数
- `API_ID` - Telegram API ID (从 [my.telegram.org](https://my.telegram.org/apps) 获取)
- `API_HASH` - Telegram API Hash
- `BOT_TOKEN` - Bot Token (从 [@BotFather](https://t.me/botfather) 获取)

### 可选参数
- `MUSIC_PATH` - 音乐文件保存路径(默认: /data/Music)
- `VIDEO_PATH` - 视频文件保存路径(默认: /data/Video)
- `DOWNLOAD_PATH` - 其他文件保存路径(默认: /data/Download)
- `CACHE_PATH` - 缓存文件路径(默认: /app/cache)

## 🐛 已知问题

目前没有已知的重大问题。如果发现问题,请在 [Issues](../../issues) 中报告。

## 📝 更新说明

这是首个稳定版本,包含所有核心功能。

完整的更新日志请查看 [CHANGELOG.md](CHANGELOG.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

详细的贡献指南请查看 [README.md](README.md#贡献)

## 📄 许可证

本项目采用 MIT 许可证。详情请查看 [LICENSE](LICENSE)

## 🙏 致谢

感谢以下开源项目:
- [Telethon](https://github.com/LonamiWebs/Telethon) - 强大的 Telegram 客户端库
- [Docker](https://www.docker.com/) - 容器化平台

---

## 💬 获取帮助

如果遇到问题:
1. 查看 [README.md](README.md) 中的故障排查部分
2. 查看 [INSTALL.md](INSTALL.md) 中的常见问题
3. 在 [Issues](../../issues) 中搜索类似问题
4. 提交新的 Issue

---

**如果这个项目对你有帮助,请给一个 ⭐ Star!**

Made with ❤️ by TeleFlux Team
