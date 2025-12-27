# 快速修复指南 ⚡

## 🚨 错误: "invalid literal for int() with base 10"

这是最常见的配置问题,表示环境变量没有正确设置。

### 🎯 3 步快速修复

#### 步骤 1: 创建配置文件

```bash
cd TeleFlux
cp .env.example .env
```

#### 步骤 2: 编辑配置(重要!)

```bash
nano .env
```

填入你的**实际配置**:

```env
# ⚠️ 重要:这些是示例,必须替换为你的实际值!

# API_ID 是纯数字,从 https://my.telegram.org/apps 获取
API_ID=12345678

# API_HASH 是 32 位字母数字
API_HASH=abcdef1234567890abcdef1234567890

# BOT_TOKEN 从 @BotFather 获取
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# 以下是可选配置,可以不改
MUSIC_PATH=/data/Music
VIDEO_PATH=/data/Video
DOWNLOAD_PATH=/data/Download
CACHE_PATH=/app/cache
```

**保存**: 按 `Ctrl + X`, 然后按 `Y`, 最后按 `Enter`

#### 步骤 3: 重启服务

```bash
docker-compose down
docker-compose up -d
```

### ✅ 验证修复

查看日志,应该看到成功启动:

```bash
docker-compose logs -f
```

应该看到类似输出:
```
✅ 配置验证通过,开始连接 Telegram...
```

---

## 🔍 如何获取配置信息

### 获取 API_ID 和 API_HASH

1. 访问: https://my.telegram.org/apps
2. 使用手机号登录
3. 点击 "API development tools"
4. 填写应用信息(随意填)
5. 获得:
   - `api_id`: 纯数字,如 `12345678`
   - `api_hash`: 32 位字符,如 `abcdef1234567890abcdef1234567890`

### 获取 BOT_TOKEN

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot` 创建机器人
3. 按提示设置名称
4. 获得 Token,格式: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

---

## 🛠️ 其他常见问题

### ❌ 容器一直重启

**查看日志找原因:**
```bash
docker logs teleflux-bot
```

**可能原因:**
1. 配置错误 → 按上面步骤重新配置
2. 网络问题 → 检查防火墙
3. 权限问题 → 执行下面的命令

**修复权限:**
```bash
sudo mkdir -p /vol2/1000/Music /vol2/1000/Video /vol2/1000/Download
sudo chown -R $USER:$USER /vol2/1000/
sudo chmod -R 755 /vol2/1000/
```

### ❌ 找不到 .env 文件

```bash
# 检查当前位置
pwd

# 应该在 TeleFlux 目录下
cd TeleFlux

# 创建 .env
cp .env.example .env
```

### ❌ docker-compose 命令不存在

**安装 Docker Compose:**

Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

或使用新版本命令:
```bash
docker compose up -d  # 注意是空格不是横杠
```

---

## 📋 完整流程示例

从零开始的完整步骤:

```bash
# 1. 解压项目
tar -xzf TeleFlux-v1.0.0.tar.gz
cd TeleFlux

# 2. 创建配置文件
cp .env.example .env

# 3. 编辑配置
nano .env
# 填入实际的 API_ID, API_HASH, BOT_TOKEN
# 保存: Ctrl+X, Y, Enter

# 4. 创建存储目录
mkdir -p /vol2/1000/Music /vol2/1000/Video /vol2/1000/Download

# 5. 构建镜像
docker build -t teleflux:latest .

# 6. 启动服务
docker-compose up -d

# 7. 查看日志
docker-compose logs -f

# 8. 测试机器人
# 在 Telegram 中向机器人发送文件
```

---

## 🆘 还是不行?

### 检查清单

- [ ] `.env` 文件已创建
- [ ] API_ID 是纯数字(没有引号)
- [ ] API_HASH 填写正确(没有引号)
- [ ] BOT_TOKEN 填写正确(没有引号)
- [ ] 没有使用示例值(your_api_id 等)
- [ ] Docker 服务正在运行
- [ ] 有网络连接

### 收集信息提交 Issue

```bash
# 收集诊断信息
echo "=== 系统信息 ===" > debug.txt
docker --version >> debug.txt
docker-compose --version >> debug.txt
echo "" >> debug.txt

echo "=== 容器状态 ===" >> debug.txt
docker ps -a | grep teleflux >> debug.txt
echo "" >> debug.txt

echo "=== 日志 ===" >> debug.txt
docker logs teleflux-bot 2>&1 | tail -50 >> debug.txt

# 查看收集的信息
cat debug.txt
```

将 `debug.txt` 内容提交到 GitHub Issues。

---

## 📞 获取帮助

- 📖 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 详细故障排查
- 📚 查看 [README.md](README.md) 完整文档
- 💬 提交 [GitHub Issue](https://github.com/yourusername/TeleFlux/issues)

---

**记住:最常见的问题就是忘记修改 .env 文件! 🎯**
