# TeleFlux 📥

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![Docker](https://img.shields.io/badge/docker-ghcr.io-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

**智能 Telegram 文件下载机器人,支持自动分类、断点续传、进度控制**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [配置说明](#-配置说明) • [更新日志](#-更新日志)

</div>

---

## 📖 项目介绍

TeleFlux 是一个强大的 Telegram 文件下载机器人,能够自动接收并分类保存文件。支持音乐、视频、文档等多种文件类型,具备智能文件名清理、重复检测、实时进度显示等功能。

### ✨ 功能特性

- 🎯 **自动分类下载**
  - 🎵 音乐文件 → Music 目录
  - 🎬 视频文件 → Video 目录
  - 📄 其他文件 → Download 目录

- 🧹 **智能文件名处理**
  - 自动清理特殊字符和广告信息
  - 音乐文件按 "歌名-歌手" 格式命名
  - 视频文件自动提取关键词(超过7字自动精简)
  - 保留原名兜底机制

- 🔄 **重复文件智能处理**
  - 自动检测重复文件
  - 提供三种选项:覆盖 / 加序号 / 取消
  - 避免文件冲突

- 📊 **实时进度控制**
  - 图形化进度条显示
  - 显示下载速度和剩余时间
  - 支持暂停/继续下载
  - 支持取消下载(自动清理临时文件)

- 💪 **强大下载能力**
  - 无文件大小限制
  - 支持大文件下载(使用 MTProto)
  - 断点续传功能(跨容器重启可恢复)
  - 自动清理未完成的下载

- 🐳 **容器化部署**
  - Docker 镜像支持
  - Docker Compose 一键部署
  - 持久化存储
  - 可自定义路径配置

---

## 🚀 快速开始

### 前置要求

- Docker 和 Docker Compose
- Telegram Bot Token (从 [@BotFather](https://t.me/botfather) 获取)
- Telegram API 凭证 (从 [my.telegram.org](https://my.telegram.org/apps) 获取)

### 获取 Telegram 配置

#### 1. 获取 Bot Token

1. 在 Telegram 中搜索 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 获得 Bot Token (格式: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### 2. 获取 API_ID 和 API_HASH

1. 访问 [my.telegram.org](https://my.telegram.org/apps)
2. 使用手机号登录
3. 点击 "API development tools"
4. 填写应用信息(随意填写即可)
5. 获得 `api_id` 和 `api_hash`

---

## 📦 安装部署

### 方法一: 使用 GitHub Container Registry (推荐)

#### 1. 直接拉取镜像

```bash
# 拉取最新版本
docker pull ghcr.io/yourusername/teleflux:latest

# 或拉取指定版本
docker pull ghcr.io/yourusername/teleflux:v1.1.0
```

#### 2. 创建配置文件

创建一个 `.env` 文件：

```bash
cat > .env << 'EOF'
API_ID=你的_API_ID
API_HASH=你的_API_HASH
BOT_TOKEN=你的_BOT_TOKEN
EOF
```

#### 3. 运行容器

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  --env-file .env \
  -v /your/path/Music:/data/Music \
  -v /your/path/Video:/data/Video \
  -v /your/path/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  ghcr.io/yourusername/teleflux:latest
```

#### 4. 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  teleflux:
    image: ghcr.io/yourusername/teleflux:latest
    container_name: teleflux-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - /your/path/Music:/data/Music
      - /your/path/Video:/data/Video
      - /your/path/Download:/data/Download
      - ./cache:/app/cache
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

然后运行：

```bash
docker-compose up -d
```

---

### 方法二: Docker Compose 从源码构建

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/TeleFlux.git
cd TeleFlux
```

#### 2. 配置环境变量

复制环境变量示例文件:

```bash
cp .env.example .env
```

编辑 `.env` 文件,填入你的配置:

```bash
nano .env
```

```env
# 必需配置
API_ID=你的_API_ID
API_HASH=你的_API_HASH
BOT_TOKEN=你的_BOT_TOKEN

# 可选配置(使用默认值即可)
MUSIC_PATH=/data/Music
VIDEO_PATH=/data/Video
DOWNLOAD_PATH=/data/Download
CACHE_PATH=/app/cache
```

#### 3. 修改 docker-compose.yml (可选)

如果需要自定义宿主机存储路径,编辑 `docker-compose.yml`:

```yaml
volumes:
  # 修改冒号左边的路径为你的实际路径
  - /your/custom/path/Music:/data/Music
  - /your/custom/path/Video:/data/Video
  - /your/custom/path/Download:/data/Download
  - ./cache:/app/cache
```

#### 4. 构建镜像

```bash
docker build -t teleflux:latest .
```

#### 5. 启动服务

```bash
docker-compose up -d
```

#### 6. 查看日志

```bash
docker-compose logs -f
```

#### 7. 停止服务

```bash
docker-compose down
```

---

### 方法三: Docker Run 自定义构建

#### 1. 构建镜像

```bash
docker build -t teleflux:latest .
```

#### 2. 运行容器

**基础运行命令:**

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=你的_API_ID \
  -e API_HASH=你的_API_HASH \
  -e BOT_TOKEN=你的_BOT_TOKEN \
  -v /vol2/1000/Music:/data/Music \
  -v /vol2/1000/Video:/data/Video \
  -v /vol2/1000/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  teleflux:latest
```

**自定义路径运行:**

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=你的_API_ID \
  -e API_HASH=你的_API_HASH \
  -e BOT_TOKEN=你的_BOT_TOKEN \
  -e MUSIC_PATH=/custom/music \
  -e VIDEO_PATH=/custom/video \
  -e DOWNLOAD_PATH=/custom/download \
  -v /your/custom/path/music:/custom/music \
  -v /your/custom/path/video:/custom/video \
  -v /your/custom/path/download:/custom/download \
  -v $(pwd)/cache:/app/cache \
  teleflux:latest
```

#### 3. 查看日志

```bash
docker logs -f teleflux-bot
```

#### 4. 停止容器

```bash
docker stop teleflux-bot
docker rm teleflux-bot
```

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `API_ID` | ✅ | - | Telegram API ID |
| `API_HASH` | ✅ | - | Telegram API Hash |
| `BOT_TOKEN` | ✅ | - | Telegram Bot Token |
| `MUSIC_PATH` | ❌ | `/data/Music` | 音乐文件保存路径 |
| `VIDEO_PATH` | ❌ | `/data/Video` | 视频文件保存路径 |
| `DOWNLOAD_PATH` | ❌ | `/data/Download` | 其他文件保存路径 |
| `CACHE_PATH` | ❌ | `/app/cache` | 缓存和会话文件路径 |

### 目录映射

容器内的路径需要映射到宿主机:

```yaml
volumes:
  - 宿主机路径:容器内路径
```

**示例:**

```yaml
volumes:
  - /vol2/1000/Music:/data/Music      # 音乐目录
  - /vol2/1000/Video:/data/Video      # 视频目录
  - /vol2/1000/Download:/data/Download # 其他文件目录
  - ./cache:/app/cache                # 缓存目录(建议使用相对路径)
```

---

## 📝 使用说明

### 1. 启动机器人

在 Telegram 中搜索你的机器人,发送 `/start` 启动。

### 2. 发送文件

直接向机器人发送任何文件,机器人会:
- 自动识别文件类型
- 清理和格式化文件名
- 检查是否重复
- 显示下载进度
- 保存到对应目录

### 3. 处理重复文件

如果检测到重复文件,机器人会提供三个选项:
- **♻️ 覆盖**: 覆盖原有文件
- **➕ 加序号**: 保留原文件,新文件加序号 (例: `song_1.mp3`)
- **❌ 取消**: 取消本次下载

### 4. 控制下载

下载过程中可以:
- **⏸ 暂停**: 暂停当前下载
- **▶️ 继续**: 继续下载
- **❌ 取消**: 取消下载并清理临时文件

---

## 🎨 文件命名规则

### 音乐文件
- 尝试提取歌曲信息: `歌名-歌手.mp3`
- 无元数据时清理文件名: `Song Name.mp3`

### 视频文件
- 提取关键词(最多15字符)
- 移除广告和特殊字符
- 超过7字自动精简: `Movie.mp4`

### 其他文件
- 移除特殊字符
- 清理广告信息
- 保留有意义的文件名

---

## 🔧 故障排查

### 问题 1: 容器无法启动 / invalid literal for int() 错误

这通常是环境变量配置问题。

**快速解决:**

1. 确保已创建 `.env` 文件:
```bash
cp .env.example .env
nano .env
```

2. 填入实际配置(不要用示例值):
```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

3. 确保 `docker-compose.yml` 包含:
```yaml
env_file:
  - .env
```

4. 重启服务:
```bash
docker-compose down
docker-compose up -d
```

**详细解决方法请查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

### 问题 2: 文件下载失败

**检查权限:**

```bash
# 检查目录权限
ls -la /vol2/1000/

# 如果权限不足,修改权限
sudo chmod -R 755 /vol2/1000/Music
sudo chmod -R 755 /vol2/1000/Video
sudo chmod -R 755 /vol2/1000/Download
```

### 问题 3: 断点续传不工作

确保 `cache` 目录已正确映射:

```yaml
volumes:
  - ./cache:/app/cache  # 必须映射此目录
```

### 问题 4: 查看详细日志

```bash
# Docker Compose
docker-compose logs -f --tail=100

# Docker
docker logs -f --tail=100 teleflux-bot
```

**更多问题请查看完整的 [故障排查指南](TROUBLESHOOTING.md)**

---

## 🔄 更新升级

### 更新到最新版本

```bash
# 1. 停止当前服务
docker-compose down

# 2. 拉取最新代码
git pull origin main

# 3. 重新构建镜像
docker build -t teleflux:latest .

# 4. 启动服务
docker-compose up -d
```

---

## 📜 更新日志

### v1.1.0 (2024-12-25)

#### 🎉 重大更新

**GitHub Actions 自动化:**
- ✅ 自动构建 Docker 镜像并推送到 GitHub Container Registry
- ✅ 支持多架构构建 (linux/amd64, linux/arm64)
- ✅ 自动创建 Release 并附带源码 zip 包
- ✅ 版本标签管理 (latest, vX.X.X, main)

**下载体验改进:**
- ✅ 取消下载立即反馈提示
- ✅ 超长文件名智能优化（提取关键词，过滤广告）
- ✅ 进度条优化（缩短50%，10字符）
- ✅ 新增下载速度显示（MB/s 或 KB/s）
- ✅ 新增剩余时间预测（智能格式化）
- ✅ 进度条显示文件名（自动截断）

**文件名处理增强:**
- ✅ 视频文件智能提取（标题、年份、S01E05等）
- ✅ 自动识别并移除广告关键词
- ✅ 文件名长度控制（40-50字符）
- ✅ 显示优化提示信息

**用户体验提升:**
- ✅ 点击取消按钮立即弹窗确认
- ✅ 界面更新显示取消状态
- ✅ 临时文件自动清理提示
- ✅ 更清晰的信息展示

---

### v1.0.0 (2024-12-25)

#### 🎉 初始版本

**核心功能:**
- ✅ 自动文件下载和分类
- ✅ 智能文件名清理(音乐/视频/其他)
- ✅ 重复文件检测(覆盖/加序号/取消)
- ✅ 实时进度条显示
- ✅ 暂停/继续/取消下载
- ✅ 无文件大小限制
- ✅ MTProto 大文件下载
- ✅ 断点续传功能
- ✅ Docker 容器化部署
- ✅ 可自定义路径配置
- ✅ 取消下载自动清理临时文件

**文件命名:**
- ✅ 音乐文件: "歌名-歌手" 格式
- ✅ 视频文件: 关键词提取(>7字自动精简)
- ✅ 清理特殊字符和广告
- ✅ 原名兜底机制

**用户体验:**
- ✅ 友好的交互界面
- ✅ 详细的进度信息
- ✅ 按钮精简优化
- ✅ 多选项处理重复文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

### 开发指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram 客户端库
- [Docker](https://www.docker.com/) - 容器化平台

---

## 📧 联系方式

- 项目主页: [https://github.com/yourusername/TeleFlux](https://github.com/yourusername/TeleFlux)
- 问题反馈: [https://github.com/yourusername/TeleFlux/issues](https://github.com/yourusername/TeleFlux/issues)

---

<div align="center">

**如果这个项目对你有帮助,请给一个 ⭐ Star!**

Made with ❤️ by TeleFlux Team

</div>
