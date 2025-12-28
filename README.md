<div align="center">

# TeleFlux

![Version](https://img.shields.io/badge/version-1.0.9-blue.svg) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white) ![Python](https://img.shields.io/badge/Telethon-Based-yellow.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

**Telegram → NAS 的“Flux 通道”**：将转发的文件自动归档到服务器目录，并提供实时可视化任务面板。

它支持并发下载、智能命名（尤其对音乐来源的消息做了深度解析）、以及面板的防抖刷新与空闲清理。

> [!TIP]
> 如果您使用的是 NAS / 家用服务器，建议将 `.env`、`cache/`、以及数据目录独立出来做备份；容器随时可重建，数据与凭证不可丢。

```
┌──────────────────────────────────────────────────────────────┐
│  TeleFlux  |  Telegram ↔ Storage  |  Fast, Safe, Observable  │
└──────────────────────────────────────────────────────────────┘
```

</div>

---

## 目录

- [核心能力](#核心能力)
- [快速开始](#快速开始)
- [目录映射](#目录映射)
- [自动命名策略](#自动命名策略)
- [安全与合规](#安全与合规)
- [故障排查](#故障排查)

---

## 核心能力

| 模块 | 能力 | 说明 |
|---|---|---|
| 下载与归档 | 自动分流到 Music/Video/Download | 可按文件类型自动落盘到不同目录 |
| 并发与一致性 | 并发安全（面板/状态） | 并发转发多文件时避免 UI 冲突 |
| 面板体验 | 实时进度 + 防抖刷新 + 空闲清理 | 降低 API 压力，同时避免“完成项长期残留” |
| 音乐场景 | 四级命名策略（Metadata → 文案解析 → 标签推断 → 唯一兜底） | 适配 `@music_v1bot` 等来源复杂的消息 |

---

## 快速开始

本项目提供 **GHCR 镜像**，您无需克隆仓库：

- **Docker Compose**：只需要创建一个 `docker-compose.yml`，然后 `docker compose up -d`。
- **Docker Run**：只需要一条命令即可启动。

> [!IMPORTANT]
> GHCR 对镜像地址有强制要求：`owner/repo` 必须全小写。
> 
> 例如 GitHub 仓库是 `WeiYingiii/TeleFlux`，镜像地址必须写为：`ghcr.io/weiyingiii/teleflux:latest`。

### 方式 A：只创建一个 docker-compose.yml 即可运行（推荐）

在任意目录新建 `docker-compose.yml`（把 `API_ID / API_HASH / BOT_TOKEN` 填上；目录映射按您的 NAS 实际路径改）：

```yaml
services:
  teleflux:
    # 可用 latest，或固定到某个版本号（更可控）：ghcr.io/weiyingiii/teleflux:1.0.9
    image: ghcr.io/weiyingiii/teleflux:latest
    container_name: teleflux-bot
    restart: unless-stopped

    environment:
      API_ID: "1234567"
      API_HASH: "your_api_hash"
      BOT_TOKEN: "your_bot_token"
      TZ: "Asia/Shanghai"

      # 容器内固定路径（一般无需改）
      MUSIC_PATH: /data/Music
      VIDEO_PATH: /data/Video
      DOWNLOAD_PATH: /data/Download
      CACHE_PATH: /app/cache

    volumes:
      # 将宿主机目录映射到容器（按您的 NAS 路径调整）
      - /vol2/1000/Music:/data/Music
      - /vol2/1000/Video:/data/Video
      - /vol2/1000/Download:/data/Download
      - ./cache:/app/cache
```

启动：

```bash
docker compose up -d
docker compose logs -f --tail=200 teleflux
```

### 方式 B：一条 docker run 命令启动

把参数替换成您的真实值与真实路径：

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID="1234567" \
  -e API_HASH="your_api_hash" \
  -e BOT_TOKEN="your_bot_token" \
  -e TZ="Asia/Shanghai" \
  -e MUSIC_PATH=/data/Music \
  -e VIDEO_PATH=/data/Video \
  -e DOWNLOAD_PATH=/data/Download \
  -e CACHE_PATH=/app/cache \
  -v /vol2/1000/Music:/data/Music \
  -v /vol2/1000/Video:/data/Video \
  -v /vol2/1000/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  ghcr.io/weiyingiii/teleflux:latest  # 或固定版本：ghcr.io/weiyingiii/teleflux:1.0.9
```

查看日志：

```bash
docker logs -f --tail=200 teleflux-bot
```

---

## 目录映射

| 资源类型 | 容器内路径 (Fixed) | 宿主机路径示例 (Host) |
|------|------|------|
| 🎵 音乐 | /data/Music | /vol2/1000/Music |
| 🎬 视频 | /data/Video | /vol2/1000/Video |
| 📦 其他 | /data/Download | /vol2/1000/Download |
| ⚡ 缓存 | /app/cache | ./cache |

---

## 自动命名策略

针对音乐文件（尤其是来源复杂的转发文件），TeleFlux 采用一套严格的“四级命名策略”，最大限度避免出现 `music.mp3` 之类的占位文件名：

1. **元数据优先**：首选读取音频 Metadata (Title/Performer)
2. **文案解析**：若缺失元数据，则解析消息文案的 `歌曲：xxx - yyy` 等格式（适配 `@music_v1bot`）
3. **格式推断**：从文案标签（如 `#flac`）修正扩展名，避免被占位扩展名误导
4. **唯一性兜底**：使用 Message ID / Document ID 生成唯一文件名，杜绝覆盖风险

---

## 安全与合规

- **敏感信息保护**：`API_ID` / `API_HASH` / `BOT_TOKEN` 属于私密凭证。您可以写在 `docker-compose.yml`，也可以使用 `.env`（更便于管理/备份）；务必避免提交到公开仓库。
- **Token 泄露处理**：如 `BOT_TOKEN` 泄露，请立即联系 `@BotFather` 执行 `/revoke` 重置。

---

## 故障排查

### 1) `repository name must be lowercase`
这是 GHCR / Docker 对镜像引用格式的限制。请确保镜像地址中的 `owner/repo` 全小写（例如 `ghcr.io/weiyingiii/teleflux:latest`），不要直接复制带大写字母的 GitHub 仓库名。

### 2) `ModuleNotFoundError: No module named 'task_manager'`
请确认镜像内包含 `task_manager.py`（Dockerfile 已显式 COPY），并确保没有 volume 覆盖 `/app` 导致镜像内文件被宿主目录“盖掉”。
