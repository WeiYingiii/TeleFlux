<div align="center">

# TeleFlux

![Version](https://img.shields.io/badge/version-1.0.4-blue.svg) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white) ![Python](https://img.shields.io/badge/Telethon-Based-yellow.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

**TeleFlux 是一个高效的 Telegram 下载机器人，旨在成为连接 Telegram 资源与 NAS/服务器的自动化桥梁。**

它不仅能自动归档文件，还拥有 **实时可视化面板**，<br>并针对 **音乐机器人**（如 `@music_v1bot`）进行了深度优化的元数据解析。

</div>

---

## ✨ 核心特性

### 📂 智能下载与管理
* **自动归档**：根据文件类型自动分流，将音乐、视频和其他文件保存至指定目录。
* **重复处理**：灵活的文件冲突策略，支持 `覆盖`、`自动编号` 或 `取消下载`。

### 📊 交互式任务面板
* **实时监控**：在 Telegram 消息中实时更新下载进度、当前速度及预计剩余时间。
* **并发安全**：优化的锁机制，避免在快速转发多个文件时出现面板冲突。
* **智能刷新**：采用防抖（Debounce）技术减少 API 请求，配合下载完成后的兜底刷新，确保状态显示的准确性。

### 🎵 音频命名增强 (Audio Smart-Rename)
针对音乐文件（尤其是来源复杂的转发文件），TeleFlux 采用了一套严谨的**四级命名策略**：

1. **元数据优先**：首选读取音频文件的 Metadata (Title/Performer)。
2. **文案解析**：若元数据缺失，自动解析消息文案中的 `歌曲：xxx - yyy` 格式（适配 `@music_v1bot`）。
3. **格式推断**：通过文案标签（如 `#flac`）智能修正文件扩展名，避免被占位符 `music.mp3` 误导。
4. **唯一性兜底**：在极度缺乏信息时，使用 Message ID / Document ID 作为文件名，杜绝覆盖风险。

---

## 🚀 快速开始 (Docker Compose)

### 1. 环境准备
确保您的服务器已安装 Docker 及 Docker Compose。

### 2. 配置部署
编辑 `docker-compose.yml` 文件，填入您的 Telegram API 凭证。

> **注意**：宿主机目录（`:` 左侧路径）可根据您的 NAS 实际结构进行修改。

```yaml
services:
  teleflux:
    image: teleflux:latest
    container_name: teleflux
    restart: unless-stopped
    environment:
      - API_ID=1234567             # 替换为您的 API_ID
      - API_HASH=your_api_hash     # 替换为您的 API_HASH
      - BOT_TOKEN=your_bot_token   # 替换为您的 BOT_TOKEN
    volumes:
      # 格式: /宿主机路径:/容器内路径
      - /vol2/1000/Music:/data/Music
      - /vol2/1000/Video:/data/Video
      - /vol2/1000/Download:/data/Download
      - ./cache:/app/cache         # 缓存持久化

# 构建并后台启动
docker compose up -d --build

# 查看运行日志
docker compose logs -f --tail=200 teleflux
```
### 📂 目录映射说明
| 资源类型 | 容器内路径 (Fixed) | 宿主机路径示例 (Host) |
|------|------|------|
| 🎵 音乐 | /data/Music | /vol2/1000/Music |
| 🎬 视频 | /data/Video | /vol2/1000/Video |
| 📦 其他 | /data/Download | /vol2/1000/Download |
| ⚡ 缓存 | /app/cache | ./cache |

🛡️ 安全提示
敏感信息保护：API_ID, API_HASH, 和 BOT_TOKEN 是您的私密凭证，切勿提交到 GitHub 或任何公开代码仓库。

Token 泄露处理：如果您不慎在群组或公开场合泄露了 BOT_TOKEN，请立即联系 @BotFather 发送 /revoke 指令重置 Token。

---

## 🧰 GitHub 自动构建并发布 Docker 镜像 (GHCR)

本项目内置 GitHub Actions 工作流：当您 **更新版本并推送 Git Tag**（例如 `v1.0.4`）后，会自动在 GitHub Container Registry (GHCR) 构建并推送镜像。

### 1. 前置条件
1. 仓库需启用 GitHub Packages（默认启用）。
2. 工作流已配置 `packages: write` 权限，通常无需额外配置。

### 2. 发布步骤（推荐）
在本地完成版本更新并提交后：

```bash
git add -A
git commit -m "chore: release v1.0.4"

# 创建并推送 tag（触发自动构建）
git tag v1.0.4
git push origin main --tags
```

### 3. 拉取并使用镜像
镜像地址格式：
- `ghcr.io/<OWNER>/<REPO>:<TAG>`

例如：
```bash
docker pull ghcr.io/<OWNER>/<REPO>:v1.0.4
```

Docker Compose 也可以直接改为使用 `image`：
```yaml
services:
  teleflux-bot:
    image: ghcr.io/<OWNER>/<REPO>:v1.0.4
    env_file:
      - .env
    restart: unless-stopped
```

