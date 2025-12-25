# 故障排查指南 🔧

## ❌ 错误: "invalid literal for int() with base 10: 'your_api_id'"

### 问题原因
环境变量没有正确传递到容器中,容器使用了默认的示例值。

### 解决方法

#### 方法 1: 使用 .env 文件 (推荐)

1. **创建 .env 文件**
```bash
cd TeleFlux
cp .env.example .env
```

2. **编辑 .env 文件**
```bash
nano .env
# 或使用其他编辑器: vim .env 或 code .env
```

3. **填入实际配置** (重要:不要有引号)
```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

4. **确保 docker-compose.yml 包含 env_file**
```yaml
services:
  teleflux:
    env_file:
      - .env
```

5. **重新启动**
```bash
docker-compose down
docker-compose up -d
```

#### 方法 2: 直接在 docker-compose.yml 中设置

1. **编辑 docker-compose.yml**
```yaml
services:
  teleflux:
    environment:
      - API_ID=12345678
      - API_HASH=abcdef1234567890abcdef1234567890
      - BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
      - MUSIC_PATH=/data/Music
      - VIDEO_PATH=/data/Video
      - DOWNLOAD_PATH=/data/Download
```

2. **重新启动**
```bash
docker-compose down
docker-compose up -d
```

#### 方法 3: Docker Run 方式

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=12345678 \
  -e API_HASH=abcdef1234567890abcdef1234567890 \
  -e BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz \
  -v /vol2/1000/Music:/data/Music \
  -v /vol2/1000/Video:/data/Video \
  -v /vol2/1000/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  teleflux:latest
```

### 验证配置

**查看容器内的环境变量:**
```bash
docker exec teleflux-bot env | grep -E "API_|BOT_"
```

应该看到实际的值,而不是 `your_api_id` 等示例值。

---

## ❌ 错误: 容器不断重启

### 检查日志
```bash
docker-compose logs -f
# 或
docker logs teleflux-bot
```

### 常见原因

#### 1. 配置错误
- API_ID 不是纯数字
- API_HASH 或 BOT_TOKEN 格式错误
- 使用了示例值而非实际值

**解决**: 按照上面的方法正确配置

#### 2. 网络问题
- 无法连接到 Telegram 服务器

**解决**:
```bash
# 测试网络
docker exec teleflux-bot ping -c 3 telegram.org

# 如果无法连接,检查防火墙或代理设置
```

#### 3. 权限问题
```bash
# 检查目录权限
ls -la /vol2/1000/

# 修改权限
sudo chown -R $USER:$USER /vol2/1000/
sudo chmod -R 755 /vol2/1000/
```

---

## ❌ 错误: 文件下载失败

### 检查存储路径

1. **验证目录存在**
```bash
ls -la /vol2/1000/Music
ls -la /vol2/1000/Video
ls -la /vol2/1000/Download
```

2. **创建目录(如果不存在)**
```bash
mkdir -p /vol2/1000/Music
mkdir -p /vol2/1000/Video
mkdir -p /vol2/1000/Download
```

3. **检查权限**
```bash
# 查看权限
ls -la /vol2/1000/

# 修改权限(如果需要)
sudo chown -R $USER:$USER /vol2/1000/
sudo chmod -R 755 /vol2/1000/
```

4. **检查磁盘空间**
```bash
df -h /vol2/1000/
```

---

## ❌ 错误: 断点续传不工作

### 问题原因
cache 目录没有正确映射

### 解决方法

1. **检查 docker-compose.yml**
```yaml
volumes:
  - ./cache:/app/cache  # 必须包含这一行
```

2. **检查 cache 目录**
```bash
ls -la ./cache
```

3. **如果目录不存在,创建它**
```bash
mkdir -p ./cache
chmod 755 ./cache
```

4. **重新启动容器**
```bash
docker-compose restart
```

---

## 🔍 调试技巧

### 查看详细日志

```bash
# 实时日志
docker-compose logs -f

# 最后 100 行
docker-compose logs --tail=100

# 特定时间范围
docker-compose logs --since 10m

# 只看错误
docker-compose logs | grep ERROR
```

### 进入容器检查

```bash
# 进入容器
docker exec -it teleflux-bot bash

# 检查环境变量
env | grep -E "API_|PATH|BOT"

# 检查文件
ls -la /data/
ls -la /app/cache/

# 测试网络
ping telegram.org

# 退出容器
exit
```

### 重置并重新部署

```bash
# 1. 停止并删除容器
docker-compose down

# 2. 删除缓存(可选,会丢失会话)
rm -rf ./cache

# 3. 确认配置正确
cat .env

# 4. 重新构建镜像
docker build -t teleflux:latest .

# 5. 启动服务
docker-compose up -d

# 6. 查看日志
docker-compose logs -f
```

---

## 📋 配置检查清单

在启动前,确保:

- [ ] .env 文件存在并填写了实际值
- [ ] API_ID 是纯数字
- [ ] API_HASH 是 32 位字母数字
- [ ] BOT_TOKEN 格式正确(数字:字母数字)
- [ ] 存储目录已创建并有正确权限
- [ ] docker-compose.yml 配置正确
- [ ] Docker 服务正在运行

---

## 🆘 仍然无法解决?

### 1. 收集信息

```bash
# 系统信息
uname -a
docker --version
docker-compose --version

# 容器状态
docker ps -a | grep teleflux

# 完整日志
docker-compose logs > teleflux-logs.txt

# 配置(去掉敏感信息)
cat docker-compose.yml
cat .env | sed 's/=.*/=***/'
```

### 2. 提交 Issue

访问 [GitHub Issues](https://github.com/yourusername/TeleFlux/issues) 并包含:

- 错误信息
- 系统信息
- 日志文件
- 你已尝试的解决方法

---

## 📚 相关文档

- [README.md](README.md) - 项目介绍
- [INSTALL.md](INSTALL.md) - 详细安装指南
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考

---

**最后更新**: 2024-12-25
