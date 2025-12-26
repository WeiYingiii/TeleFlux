# TeleFlux 📥

<div align="center">

![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)

**智能 Telegram 文件下载机器人：自动分类、断点续传、进度控制**

</div>

---

## <a id="toc"></a>目录

- [项目简介](#intro)
- [功能概览](#features)
- [快速开始（Docker Compose）](#quickstart)
- [容器更新（升级到新版本）](#update)
- [配置说明](#config)
- [使用方式](#usage)
- [目录映射与持久化](#volumes)
- [常见问题](#faq)
- [许可证](#license)

---

## <a id="intro"></a>项目简介

TeleFlux 是一个 Telegram 机器人，用于接收并下载你发送给机器人的文件，并按类型自动分类保存。

核心目标：

- 省事：发文件即可自动落盘
- 可控：支持暂停/继续/取消
- 稳定：支持大文件与断点续传（`.downloading` 临时文件）

[返回目录](#toc)

---

## <a id="features"></a>功能概览

- 自动分类下载  
  - 🎵 音乐 → `MUSIC_PATH`
  - 🎬 视频 → `VIDEO_PATH`
  - 📄 其他 → `DOWNLOAD_PATH`

- 智能文件名处理  
  - 去除常见广告/特殊字符
  - 音乐优先按“歌名-歌手”命名（若可从元数据读取）
  - 自动移除尾部时间戳类后缀（例如：`xxx_1756486628200.mp4` → `xxx.mp4`）

- 重复文件处理  
  - 自动检测同名文件
  - 提供：覆盖 / 加序号 / 取消

- 多任务统一面板（重要变更）  
  - 同一聊天内，所有下载任务统一展示在一个“下载任务面板”消息中
  - 每个任务都有独立的暂停/继续与取消按钮
  - 支持并发下载（不再“一任务一条进度消息”刷屏）

[返回目录](#toc)

---

## <a id="quickstart"></a>快速开始（Docker Compose）

### 1) 准备 Telegram 配置

- `BOT_TOKEN`：从 `@BotFather` 获取
- `API_ID` / `API_HASH`：从 `https://my.telegram.org/apps` 获取

### 2) 创建 `.env`

```bash
cp .env.example .env
```

编辑 `.env`（至少填写三项）：

```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# 可选：自定义目录（容器内路径）
MUSIC_PATH=/data/Music
VIDEO_PATH=/data/Video
DOWNLOAD_PATH=/data/Download
CACHE_PATH=/app/cache
```

### 3) 启动

```bash
docker compose up -d --build
```

[返回目录](#toc)

---


## <a id="update"></a>容器更新（升级到新版本）

> 说明：更新只会替换容器镜像/代码，不会影响你映射到宿主机的下载目录与 `./cache`（除非你手动删除它们）。

### A) 使用远程镜像（推荐：GHCR / Docker Hub）

1) **更新镜像**
```bash
docker compose pull teleflux
```

2) **滚动重建并后台启动**
```bash
docker compose up -d --remove-orphans
```

3) （可选）**清理旧镜像**
```bash
docker image prune -f
```

> 如果你不是用 `latest`，而是使用固定版本号，请先在 `docker-compose.yml` 把 `image:` 改为 `...:v1.1.1`，再执行 `pull`。

### B) 从源码构建镜像（本地 build）

1) **更新代码**
```bash
git pull
```

2) **重新构建并启动**
```bash
docker compose build --pull teleflux
docker compose up -d --remove-orphans
```

### 验证与排错

- 查看日志：
```bash
docker compose logs -f teleflux
```
- 查看容器状态：
```bash
docker compose ps
```

---
## <a id="config"></a>配置说明

### 必需环境变量

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`

### 可选环境变量（有默认值）

- `MUSIC_PATH`：音乐保存目录
- `VIDEO_PATH`：视频保存目录
- `DOWNLOAD_PATH`：其他文件保存目录
- `CACHE_PATH`：会话与缓存目录（建议映射到宿主机持久化）

[返回目录](#toc)

---

## <a id="usage"></a>使用方式

1. 在 Telegram 与机器人对话，直接发送文件（音乐/视频/其他均可）。
2. 机器人会生成“下载任务面板”，并在面板内持续更新任务进度。
3. 面板按钮说明：
   - `⏸ n` / `▶️ n`：暂停/继续第 n 个任务
   - `❌ n`：取消第 n 个任务
   - `🔄 刷新`：手动刷新面板显示

重复文件时，会额外发送一条“重复文件处理”提示消息，按提示选择即可。

[返回目录](#toc)

---

## <a id="volumes"></a>目录映射与持久化

建议在 `docker-compose.yml` 中映射数据目录与缓存目录，例如：

```yaml
services:
  teleflux:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - /your/path/Music:/data/Music
      - /your/path/Video:/data/Video
      - /your/path/Download:/data/Download
      - ./cache:/app/cache
```

注意：`.env` 中的 `MUSIC_PATH/VIDEO_PATH/DOWNLOAD_PATH/CACHE_PATH` 应与容器内路径一致（上例为 `/data/...` 与 `/app/cache`）。

[返回目录](#toc)

---

## <a id="faq"></a>常见问题

### 1) 为什么取消会“卡住”？
已改为直接取消后台下载任务，并在面板中即时显示“取消中/已取消”。若网络极差，取消可能需要短暂时间完成清理。

### 2) 下载中断后能否续传？
可以。未完成文件会以 `.downloading` 结尾保存；重新启动容器后，同名任务会从已有大小继续下载。

### 3) 文件名为什么会被改？
为避免广告/非法字符/过长名称影响保存与管理；同时会移除常见的尾部时间戳后缀。

[返回目录](#toc)

---

## <a id="license"></a>许可证

MIT License. 详见 `LICENSE`。

[返回目录](#toc)
