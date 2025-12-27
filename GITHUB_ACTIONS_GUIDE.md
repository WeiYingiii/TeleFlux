# GitHub Actions 使用指南 🚀

本项目已配置完整的 GitHub Actions CI/CD 流程，可自动构建 Docker 镜像并发布到 GitHub Container Registry。

---

## 📋 目录

- [工作流概览](#工作流概览)
- [首次设置](#首次设置)
- [使用镜像](#使用镜像)
- [发布新版本](#发布新版本)
- [工作流详情](#工作流详情)
- [故障排查](#故障排查)

---

## 工作流概览

### 1. Docker Image CI/CD (`.github/workflows/docker-image.yml`)

**触发条件:**
- 推送到 `main` 或 `master` 分支
- 推送标签 `v*` (如 `v1.1.1`)
- Pull Request 到 `main` 或 `master`
- 手动触发

**功能:**
- 自动构建 Docker 镜像
- 推送到 GitHub Container Registry
- 支持多架构 (linux/amd64, linux/arm64)
- 生成镜像标签:
  - `latest` (主分支最新)
  - `vX.X.X` (版本号)
  - `main` (主分支)
  - `pr-XXX` (Pull Request)

### 2. Release (`.github/workflows/release.yml`)

**触发条件:**
- 推送标签 `v*` (如 `v1.1.1`)

**功能:**
- 自动创建 GitHub Release
- 打包源码为 zip 文件
- 生成详细的 Release Notes
- 包含 Docker 镜像使用说明

---

## 首次设置

### 1. 启用 GitHub Container Registry

GHCR 默认已启用，无需额外配置。

### 2. 设置仓库权限

确保 GitHub Actions 有权限写入 packages:

1. 进入仓库 Settings
2. 左侧菜单选择 Actions → General
3. 滚动到 "Workflow permissions"
4. 选择 "Read and write permissions"
5. 勾选 "Allow GitHub Actions to create and approve pull requests"
6. 保存更改

### 3. 首次推送

```bash
# 添加并提交所有文件
git add .
git commit -m "feat: initial release with GitHub Actions"

# 推送到 main 分支
git push origin main

# 创建并推送第一个版本标签
git tag v1.1.1
git push origin v1.1.1
```

### 4. 查看构建状态

1. 进入仓库的 Actions 标签页
2. 查看工作流运行状态
3. 等待构建完成（通常需要 5-10 分钟）

---

## 使用镜像

### 查看可用镜像

访问仓库的 Packages 页面：
```
https://github.com/WeiYingiii/TeleFlux/pkgs/container/teleflux
```

### 拉取镜像

```bash
# 拉取最新版本
docker pull ghcr.io/weiyingiii/teleflux:latest

# 拉取指定版本
docker pull ghcr.io/weiyingiii/teleflux:v1.1.1

# 拉取主分支最新构建
docker pull ghcr.io/weiyingiii/teleflux:main
```

### 私有仓库认证

如果你的仓库是私有的，需要先登录：

```bash
# 创建 Personal Access Token (PAT)
# 1. 访问 https://github.com/settings/tokens
# 2. 生成新 token，勾选 read:packages 权限
# 3. 复制 token

# 使用 token 登录
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u WeiYingiii --password-stdin

# 然后就可以拉取镜像了
docker pull ghcr.io/weiyingiii/teleflux:latest
```

### 运行容器

```bash
docker run -d \
  --name teleflux-bot \
  --restart unless-stopped \
  -e API_ID=YOUR_API_ID \
  -e API_HASH=YOUR_API_HASH \
  -e BOT_TOKEN=YOUR_BOT_TOKEN \
  -v /path/to/Music:/data/Music \
  -v /path/to/Video:/data/Video \
  -v /path/to/Download:/data/Download \
  -v $(pwd)/cache:/app/cache \
  ghcr.io/weiyingiii/teleflux:latest
```

---

## 发布新版本

### 版本号规范

采用语义化版本 (Semantic Versioning):
- `v1.0.0` - 主版本.次版本.修订号
- 主版本号：不兼容的 API 修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

### 发布流程

#### 1. 更新版本号

更新以下文件中的版本号：

**VERSION 文件:**
```bash
echo "1.2.0" > VERSION
```

**bot.py:**
```python
logger.info("🚀 TeleFlux Bot v1.2.0 启动中...")
```

**Dockerfile:**
```dockerfile
LABEL version="1.2.0"
```

**README.md:**
```markdown
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
```

#### 2. 更新 CHANGELOG.md

```markdown
## [1.2.0] - 2024-XX-XX

### ✨ 新增功能
- 功能描述

### 🔄 变更
- 变更描述

### 🐛 修复
- 修复描述
```

#### 3. 提交并打标签

```bash
# 提交更改
git add .
git commit -m "chore: bump version to v1.2.0"

# 创建标签
git tag -a v1.2.0 -m "Release v1.2.0"

# 推送到远程
git push origin main
git push origin v1.2.0
```

#### 4. 等待自动发布

1. GitHub Actions 会自动：
   - 构建 Docker 镜像
   - 推送到 GHCR
   - 创建 GitHub Release
   - 打包源码 zip

2. 查看进度：
   - 进入仓库的 Actions 标签页
   - 查看工作流运行状态

3. 发布完成后：
   - 镜像可在 Packages 查看
   - Release 可在 Releases 页面查看

---

## 工作流详情

### Docker Image CI/CD 工作流

**步骤说明:**

1. **Checkout repository**
   - 检出代码

2. **Set up Docker Buildx**
   - 设置 Docker 构建器
   - 支持多平台构建

3. **Log in to GHCR**
   - 使用 GITHUB_TOKEN 自动登录
   - 无需手动配置密钥

4. **Extract metadata**
   - 自动生成镜像标签
   - 设置镜像标签和标签

5. **Build and push**
   - 构建 Docker 镜像
   - 推送到 GHCR
   - 启用构建缓存加速

6. **Generate attestation**
   - 生成构建证明
   - 提高镜像安全性

**支持的平台:**
- linux/amd64 (x86_64)
- linux/arm64 (ARM64/Apple Silicon)

**镜像标签示例:**
- `ghcr.io/username/teleflux:latest` - 最新稳定版
- `ghcr.io/username/teleflux:v1.1.1` - 版本号
- `ghcr.io/username/teleflux:main` - 主分支最新
- `ghcr.io/username/teleflux:main-abc1234` - 带 commit SHA

### Release 工作流

**步骤说明:**

1. **Checkout code**
   - 检出代码

2. **Get version**
   - 从 tag 提取版本号

3. **Create Release Zip**
   - 打包必要文件
   - 排除 .git, cache 等
   - 创建 VERSION 文件

4. **Generate Release Notes**
   - 自动生成 Release 说明
   - 包含安装指南
   - 包含更新日志链接

5. **Create Release**
   - 创建 GitHub Release
   - 上传源码 zip
   - 发布 Release Notes

---

## 故障排查

### 问题 1: 工作流失败 - 权限错误

**错误信息:**
```
Error: failed to push: denied: permission_denied
```

**解决方法:**
1. 检查仓库设置 → Actions → General
2. 确保 "Workflow permissions" 设置为 "Read and write permissions"
3. 重新运行工作流

### 问题 2: 多平台构建失败

**错误信息:**
```
Error: failed to solve: failed to build for platform
```

**解决方法:**
1. 这通常是架构兼容性问题
2. 检查 Dockerfile 中的基础镜像是否支持 ARM64
3. 如不需要 ARM64，可以移除该平台

### 问题 3: Release 创建失败

**错误信息:**
```
Error: Resource not accessible by integration
```

**解决方法:**
1. 确保 GITHUB_TOKEN 有正确权限
2. 检查仓库设置中的 Actions 权限
3. 确保推送了正确格式的 tag (v*)

### 问题 4: 无法拉取镜像

**错误信息:**
```
Error: unauthorized: unauthenticated
```

**解决方法:**

如果是私有仓库：
```bash
# 创建 Personal Access Token
# 访问: https://github.com/settings/tokens
# 权限: read:packages

# 登录 GHCR
echo YOUR_TOKEN | docker login ghcr.io -u WeiYingiii --password-stdin

# 然后拉取镜像
docker pull ghcr.io/weiyingiii/teleflux:latest
```

如果是公开仓库但仍失败：
```bash
# 确认镜像可见性
# 进入 Package settings
# 确保 "Package visibility" 设置为 Public
```

### 问题 5: 构建时间太长

**优化建议:**

1. **启用构建缓存** (已默认启用)
   ```yaml
   cache-from: type=gha
   cache-to: type=gha,mode=max
   ```

2. **减少构建平台**
   - 如只需要 amd64，移除 arm64
   ```yaml
   platforms: linux/amd64
   ```

3. **优化 Dockerfile**
   - 使用多阶段构建
   - 合并 RUN 命令
   - 利用层缓存

---

## 高级配置

### 自定义工作流触发

编辑 `.github/workflows/docker-image.yml`:

```yaml
on:
  push:
    branches: [ "main", "develop" ]  # 添加其他分支
    paths:
      - 'bot.py'              # 仅当特定文件改变时触发
      - 'requirements.txt'
      - 'Dockerfile'
  schedule:
    - cron: '0 0 * * 0'       # 每周日午夜自动构建
```

### 添加构建变量

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    build-args: |
      VERSION=${{ steps.get_version.outputs.VERSION }}
      BUILD_DATE=${{ steps.date.outputs.date }}
```

### 自定义镜像标签

编辑 `.github/workflows/docker-image.yml`:

```yaml
tags: |
  type=semver,pattern={{version}}
  type=semver,pattern={{major}}.{{minor}}
  type=raw,value=stable
  type=raw,value=beta,enable={{is_default_branch}}
```

---

## 最佳实践

### 1. 版本管理
- 使用语义化版本
- 每个版本打 tag
- 及时更新 CHANGELOG

### 2. 安全性
- 定期更新依赖
- 使用固定版本的 Actions
- 启用 Dependabot

### 3. 性能优化
- 启用构建缓存
- 优化 Dockerfile 层
- 使用 .dockerignore

### 4. 文档维护
- 保持 README 更新
- 记录每个版本的变更
- 提供清晰的使用示例

---

## 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [GitHub Container Registry 文档](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Buildx 文档](https://docs.docker.com/buildx/working-with-buildx/)
- [语义化版本](https://semver.org/lang/zh-CN/)

---

**祝你使用愉快！如有问题，欢迎提 Issue。** 🎉
