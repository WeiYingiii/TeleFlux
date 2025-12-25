# 安装指南 🚀

本文档提供 TeleFlux 的详细安装步骤。

---

## 📋 目录

1. [前置要求](#前置要求)
2. [获取 Telegram 配置](#获取-telegram-配置)
3. [安装方式](#安装方式)
   - [方式一: 快速部署(推荐)](#方式一-快速部署推荐)
   - [方式二: Docker Compose](#方式二-docker-compose)
   - [方式三: Docker Run](#方式三-docker-run)
4. [验证安装](#验证安装)
5. [常见问题](#常见问题)

---

## 前置要求

### 系统要求

- Linux / macOS / Windows (需要 WSL2)
- Docker 20.10+
- Docker Compose 2.0+ (可选,推荐)
- 至少 500MB 可用磁盘空间

### 安装 Docker

#### Ubuntu / Debian

```bash
# 更新软件源
sudo apt-get update

# 安装依赖
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 软件源
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 添加当前用户到 docker 组(可选)
sudo usermod -aG docker $USER
```

#### CentOS / RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 软件源
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### macOS

使用 Docker Desktop:

1. 访问 [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
2. 下载并安装 Docker Desktop
3. 启动 Docker Desktop

#### Windows

使用 Docker Desktop with WSL2:

1. 启用 WSL2: [WSL2 安装指南](https://docs.microsoft.com/zh-cn/windows/wsl/install)
2. 安装 Docker Desktop: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
3. 在设置中启用 "Use WSL 2 based engine"

---

## 获取 Telegram 配置

### 步骤 1: 创建 Telegram Bot

1. 在 Telegram 中搜索 **@BotFather**
2. 发送 `/newbot` 命令
3. 按提示输入机器人名称(例: `My File Bot`)
4. 输入机器人用户名(必须以 `bot` 结尾,例: `myfilebot`)
5. 获得 **Bot Token** (格式: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
6. 保存此 Token,稍后需要用到

### 步骤 2: 获取 API 凭证

1. 访问 [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. 使用手机号登录(需要接收验证码)
3. 点击 **"API development tools"**
4. 填写应用信息:
   - **App title**: 随意填写(例: TeleFlux)
   - **Short name**: 随意填写(例: teleflux)
   - **Platform**: 选择 Other
   - **Description**: 可选
5. 点击 **"Create application"**
6. 获得:
   - **api_id**: 一串数字(例: `12345678`)
   - **api_hash**: 一串字母数字(例: `abcdef1234567890abcdef1234567890`)
7. 保存这两个值,稍后需要用到

⚠️ **重要**: 请妥善保管这些凭证,不要泄露给他人!

---

## 安装方式

### 方式一: 快速部署(推荐)

最简单的部署方式,使用自动化脚本。

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/TeleFlux.git
cd TeleFlux
```

#### 2. 运行部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

#### 3. 配置参数

首次运行会创建 `.env` 文件,编辑它:

```bash
nano .env
```

填入你的配置:

```env
API_ID=你的_api_id
API_HASH=你的_api_hash
BOT_TOKEN=你的_bot_token
```

保存后(Ctrl+X, Y, Enter),再次运行:

```bash
./deploy.sh
```

#### 4. 完成

脚本会自动:
- ✅ 检查 Docker 环境
- ✅ 创建必要的目录
- ✅ 构建 Docker 镜像
- ✅ 启动服务

---

### 方式二: Docker Compose

适合需要自定义配置的用户。

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/TeleFlux.git
cd TeleFlux
```

#### 2. 配置环境变量

创建 `.env` 文件:

```bash
cp .env.example .env
nano .env
```

编辑内容:

```env
# 必需配置
API_ID=你的_api_id
API_HASH=你的_api_hash
BOT_TOKEN=你的_bot_token

# 可选配置
MUSIC_PATH=/data/Music
VIDEO_PATH=/data/Video
DOWNLOAD_PATH=/data/Download
CACHE_PATH=/app/cache
```

#### 3. 修改存储路径(可选)

编辑 `docker-compose.yml`:

```yaml
volumes:
  # 修改为你的实际路径
  - /your/path/Music:/data/Music
  - /your/path/Video:/data/Video
  - /your/path/Download:/data/Download
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

---

### 方式三: Docker Run

适合高级用户或不使用 Docker Compose 的场景。

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/TeleFlux.git
cd TeleFlux
```

#### 2. 构建镜像

```bash
docker build -t teleflux:latest .
```

#### 3. 创建必要的目录

```bash
mkdir -p /vol2/1000/Music
mkdir -p /vol2/1000/Video
mkdir -p /vol2/1000/Download
mkdir -p cache
```

#### 4. 运行容器

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=你的_api_id \
  -e API_HASH=你的_api_hash \
  -e BOT_TOKEN=你的_bot_token \
  -v /vol2/1000/Music:/data/Music \
  -v /vol2/1000/Video:/data/Video \
  -v /vol2/1000/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  teleflux:latest
```

#### 自定义路径示例

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=12345678 \
  -e API_HASH=abcdef1234567890 \
  -e BOT_TOKEN=123456789:ABCdefGHI \
  -e MUSIC_PATH=/custom/music \
  -e VIDEO_PATH=/custom/video \
  -e DOWNLOAD_PATH=/custom/files \
  -v /home/user/music:/custom/music \
  -v /home/user/videos:/custom/video \
  -v /home/user/files:/custom/files \
  -v $(pwd)/cache:/app/cache \
  teleflux:latest
```

#### 5. 查看日志

```bash
docker logs -f teleflux-bot
```

---

## 验证安装

### 1. 检查容器状态

```bash
# Docker Compose
docker-compose ps

# Docker
docker ps | grep teleflux
```

应该看到容器状态为 `Up`。

### 2. 查看日志

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f teleflux-bot
```

应该看到类似输出:

```
2024-12-25 10:00:00,000 - __main__ - INFO - TeleFlux Bot 启动中...
2024-12-25 10:00:00,100 - __main__ - INFO - 音乐路径: /data/Music
2024-12-25 10:00:00,101 - __main__ - INFO - 视频路径: /data/Video
2024-12-25 10:00:00,102 - __main__ - INFO - 下载路径: /data/Download
2024-12-25 10:00:00,103 - __main__ - INFO - 缓存路径: /app/cache
```

### 3. 测试机器人

1. 在 Telegram 中搜索你的机器人(使用创建时的用户名)
2. 发送 `/start` 命令
3. 应该收到欢迎消息
4. 发送任意文件测试下载功能

---

## 常见问题

### Q1: 提示 "请设置环境变量"

**原因**: 环境变量未正确设置

**解决**:
- 检查 `.env` 文件是否存在
- 确认 `API_ID`, `API_HASH`, `BOT_TOKEN` 已填写
- 确认没有引号或多余空格

### Q2: 容器启动后立即退出

**检查日志**:

```bash
docker logs teleflux-bot
```

**常见原因**:
- API 凭证错误
- Bot Token 无效
- 网络连接问题

### Q3: 文件下载失败 / 权限错误

**解决**:

```bash
# 检查目录权限
ls -la /vol2/1000/

# 修改权限
sudo chown -R $USER:$USER /vol2/1000/
sudo chmod -R 755 /vol2/1000/
```

### Q4: 断点续传不工作

**原因**: cache 目录未正确映射

**解决**: 确保 docker-compose.yml 中包含:

```yaml
volumes:
  - ./cache:/app/cache
```

### Q5: 如何更新到新版本

```bash
# 1. 停止服务
docker-compose down

# 2. 拉取最新代码
git pull

# 3. 重新构建
docker build -t teleflux:latest .

# 4. 启动服务
docker-compose up -d
```

### Q6: 如何完全卸载

```bash
# 1. 停止并删除容器
docker-compose down

# 2. 删除镜像
docker rmi teleflux:latest

# 3. 删除项目文件
cd ..
rm -rf TeleFlux
```

---

## 获取帮助

如果遇到问题:

1. 查看 [README.md](README.md) 中的故障排查部分
2. 查看项目 [Issues](https://github.com/yourusername/TeleFlux/issues)
3. 提交新的 Issue 描述问题

---

**祝你使用愉快! 🎉**
