# 快速参考指南 ⚡

## 常用命令

### Docker Compose

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看日志(最后100行)
docker-compose logs -f --tail=100

# 查看容器状态
docker-compose ps

# 重新构建并启动
docker-compose up -d --build
```

### Docker

```bash
# 启动容器
docker start teleflux-bot

# 停止容器
docker stop teleflux-bot

# 重启容器
docker restart teleflux-bot

# 查看日志
docker logs -f teleflux-bot

# 查看容器状态
docker ps | grep teleflux

# 进入容器
docker exec -it teleflux-bot bash

# 删除容器
docker rm -f teleflux-bot

# 删除镜像
docker rmi teleflux:latest
```

### 构建镜像

```bash
# 构建镜像
docker build -t teleflux:latest .

# 构建镜像(不使用缓存)
docker build --no-cache -t teleflux:latest .

# 查看镜像
docker images | grep teleflux
```

## 环境变量

### 必需变量

```bash
API_ID=12345678                              # Telegram API ID
API_HASH=abcdef1234567890abcdef1234567890   # Telegram API Hash
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz  # Bot Token
```

### 可选变量

```bash
MUSIC_PATH=/data/Music          # 音乐文件路径
VIDEO_PATH=/data/Video          # 视频文件路径
DOWNLOAD_PATH=/data/Download    # 其他文件路径
CACHE_PATH=/app/cache           # 缓存文件路径
```

## 目录映射

### 默认映射

```yaml
volumes:
  - /vol2/1000/Music:/data/Music
  - /vol2/1000/Video:/data/Video
  - /vol2/1000/Download:/data/Download
  - ./cache:/app/cache
```

### 自定义映射

```yaml
volumes:
  - /your/path/music:/data/Music
  - /your/path/video:/data/Video
  - /your/path/files:/data/Download
  - ./cache:/app/cache
```

## 故障排查

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最后100行
docker-compose logs --tail=100

# 特定时间
docker-compose logs --since 10m
```

### 检查配置

```bash
# 查看环境变量
docker exec teleflux-bot env | grep -E "API_|PATH"

# 查看容器配置
docker inspect teleflux-bot
```

### 检查权限

```bash
# 查看目录权限
ls -la /vol2/1000/

# 修改权限
sudo chown -R $USER:$USER /vol2/1000/
sudo chmod -R 755 /vol2/1000/
```

### 重置服务

```bash
# 完全重置
docker-compose down
docker rmi teleflux:latest
docker build -t teleflux:latest .
docker-compose up -d
```

## Telegram 命令

### 机器人命令

```
/start - 启动机器人,显示欢迎信息
```

### 使用流程

1. 向机器人发送文件
2. 机器人自动识别类型
3. 检查是否重复
4. 选择处理方式(如有重复)
5. 开始下载并显示进度
6. 可随时暂停/取消

## 文件路径

### 容器内路径

```
/app/                    # 应用目录
/app/bot.py             # 主程序
/app/cache/             # 缓存目录
/data/Music/            # 音乐文件
/data/Video/            # 视频文件
/data/Download/         # 其他文件
```

### 宿主机路径(默认)

```
/vol2/1000/Music/       # 音乐文件
/vol2/1000/Video/       # 视频文件
/vol2/1000/Download/    # 其他文件
./cache/                # 缓存目录
```

## 文件类型识别

### 音乐文件

- MIME type: `audio/*`
- 或包含 `DocumentAttributeAudio` 属性
- 保存到: `MUSIC_PATH`

### 视频文件

- MIME type: `video/*`
- 或包含 `DocumentAttributeVideo` 属性
- 保存到: `VIDEO_PATH`

### 其他文件

- 不属于音乐或视频
- 保存到: `DOWNLOAD_PATH`

## 性能优化

### 日志轮转

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # 单个日志文件最大10MB
    max-file: "3"      # 保留最多3个日志文件
```

### 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # CPU限制
      memory: 512M     # 内存限制
```

## 备份与恢复

### 备份配置

```bash
# 备份配置文件
cp .env .env.backup
cp docker-compose.yml docker-compose.yml.backup

# 备份缓存(包含会话)
tar -czf cache-backup.tar.gz cache/
```

### 恢复配置

```bash
# 恢复配置
cp .env.backup .env
cp docker-compose.yml.backup docker-compose.yml

# 恢复缓存
tar -xzf cache-backup.tar.gz
```

## 更新流程

```bash
# 1. 备份配置
cp .env .env.backup

# 2. 停止服务
docker-compose down

# 3. 拉取更新
git pull origin main

# 4. 恢复配置
cp .env.backup .env

# 5. 重新构建
docker build -t teleflux:latest .

# 6. 启动服务
docker-compose up -d

# 7. 验证
docker-compose logs -f
```

## 监控命令

### 容器资源使用

```bash
# 实时资源监控
docker stats teleflux-bot

# 查看磁盘使用
docker system df
```

### 日志大小

```bash
# 查看日志大小
du -sh $(docker inspect --format='{{.LogPath}}' teleflux-bot)
```

## 安全建议

1. **保护凭证**
   - 不要提交 `.env` 文件到 Git
   - 使用强密码
   - 定期更新 Bot Token

2. **限制权限**
   - 使用最小权限原则
   - 不要以 root 运行(如可能)

3. **网络安全**
   - 考虑使用防火墙
   - 限制容器网络访问

4. **更新维护**
   - 定期更新依赖
   - 关注安全公告

## 获取帮助

- 📖 查看 [README.md](README.md)
- 🔧 查看 [INSTALL.md](INSTALL.md)
- 📝 查看 [CHANGELOG.md](CHANGELOG.md)
- 💬 提交 [Issue](https://github.com/yourusername/TeleFlux/issues)

---

**最后更新**: 2024-12-25
