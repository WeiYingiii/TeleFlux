<div align="center">

# TeleFlux

![Version](https://img.shields.io/badge/version-1.0.7-blue.svg) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white) ![CI](https://img.shields.io/badge/GitHub%20Actions-GHCR%20%2B%20Release-2088FF?logo=githubactions&logoColor=white) ![Python](https://img.shields.io/badge/Telethon-Based-yellow.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

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
- [CI-CD：GHCR 自动构建与 Release 离线包](#ci-cdghcr-自动构建与-release-离线包)
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

> 推荐使用 Docker Compose 部署；凭证建议写入 `.env`，避免直接提交到仓库。

### 1) 环境准备
确保您的服务器已安装 Docker 及 Docker Compose。

### 2) 配置凭证（建议 .env）

在项目目录创建 `.env`：

```bash
API_ID=1234567
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
```

### 3) 配置部署

编辑 `docker-compose.yml`，将目录映射改为符合您 NAS/服务器结构的路径。

> **注意**：宿主机目录（`:` 左侧路径）可根据您的 NAS 实际结构进行修改。

```yaml
services:
  teleflux:
    # 本地构建：image 可保持为本地名
    # image: teleflux:latest
    # 使用 GHCR：替换为 ghcr.io/<owner>/<repo>:<tag>（owner/repo 必须小写）
    image: teleflux:latest
    container_name: teleflux
    restart: unless-stopped
    env_file:
      - .env
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

## CI-CD：GHCR 自动构建与 Release 离线包

本项目内置 GitHub Actions：当您推送版本 Tag（例如 `v1.0.7`）后，会自动：

1) 构建并推送镜像到 **GHCR**
2) 创建同名 **GitHub Release**
3) 将 **离线镜像包**（`docker save` 导出）作为 Release 资产上传

```
Flow: tag push → buildx → GHCR push → docker save → Release asset
```

### 1. 前置条件
1. 仓库启用 GitHub Packages（默认启用）。
2. 仓库 Settings → Actions → General → Workflow permissions 选择 **Read and write permissions**。

> 说明：GHCR 对镜像路径有强制规则：**仓库名必须为小写**。工作流已自动处理（小写化），命令行拉取建议使用下方“自动小写化”写法。

### 2. 发布步骤（推荐）
在本地完成版本更新并提交后：

```bash
git add -A
git commit -m "chore: release v1.0.7"

# 创建并推送 tag（触发自动构建）
git tag v1.0.7
git push origin main --tags
```

### 3. 拉取并使用镜像（自动小写化，复制即用）

GHCR 镜像格式：
- `ghcr.io/<owner>/<repo>:<tag>`（注意 **owner/repo 必须小写**）

推荐用一条命令自动小写化（避免复制粘贴踩坑）：

```bash
OWNER_REPO="<OWNER>/<REPO>"  # 例如 "WeiYingiii/TeleFlux"
IMAGE="ghcr.io/$(echo "$OWNER_REPO" | tr '[:upper:]' '[:lower:]')"

docker pull "$IMAGE:1.0.7"
```

Docker Compose 推荐用固定镜像地址（已小写）或在 `.env` 中维护：

```yaml
services:
  teleflux-bot:
    image: ghcr.io/<owner>/<repo>:1.0.7
    env_file:
      - .env
    restart: unless-stopped
```

### 4. 自动上传到 GitHub Releases（离线分发）
当您推送 `vX.Y.Z` Tag 后，工作流除了会推送到 GHCR，还会自动创建同名 GitHub Release，并附带一个离线镜像包：
- `teleflux-image-<version>-linux-amd64.tar.gz`

下载该 Release 资产后，可在任意已安装 Docker 的 Linux x86_64 机器上离线导入：
```bash
gunzip -c teleflux-image-1.0.7-linux-amd64.tar.gz | docker load
# 或者
# gzip -d teleflux-image-1.0.7-linux-amd64.tar.gz
# docker load -i teleflux-image-1.0.7-linux-amd64.tar

docker images | grep teleflux
```

说明：
1. Release 附件默认导出的是 `linux/amd64`（与 GitHub Actions Runner 架构一致）。`linux/arm64` 请直接使用 GHCR 拉取。
2. GitHub Release 单个附件存在大小限制；若镜像体积较大，建议以 GHCR 作为主要分发渠道。

---

## 安全与合规

- **敏感信息保护**：`API_ID` / `API_HASH` / `BOT_TOKEN` 属于私密凭证，建议只放 `.env`，并确保 `.env` 在 `.gitignore` 中。
- **Token 泄露处理**：如 `BOT_TOKEN` 泄露，请立即联系 `@BotFather` 执行 `/revoke` 重置。

---

## 故障排查

### 1) `repository name must be lowercase`
这是 GHCR / Docker 对镜像引用格式的限制。请使用 README 中的“自动小写化”拉取命令，或手动将 `OWNER/REPO` 全部改为小写。

### 2) `ModuleNotFoundError: No module named 'task_manager'`
请确认镜像内包含 `task_manager.py`（Dockerfile 已显式 COPY），并确保没有 volume 覆盖 `/app` 导致镜像内文件被宿主目录“盖掉”。
