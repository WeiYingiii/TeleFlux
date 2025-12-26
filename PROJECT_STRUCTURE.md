# 项目结构说明 📁

```
TeleFlux/
├── bot.py                  # 主程序文件
├── requirements.txt        # Python 依赖列表
├── Dockerfile             # Docker 镜像构建文件
├── docker-compose.yml     # Docker Compose 配置文件
├── deploy.sh              # 快速部署脚本
├── .env.example           # 环境变量示例文件
├── .dockerignore          # Docker 构建忽略文件
├── .gitignore             # Git 忽略文件
├── README.md              # 项目说明文档
├── INSTALL.md             # 详细安装指南
├── CHANGELOG.md           # 版本更新日志
├── LICENSE                # MIT 开源许可证
└── PROJECT_STRUCTURE.md   # 本文件
```

## 文件说明

### 核心文件

#### `bot.py`
主程序文件,包含所有核心功能:
- Telegram 客户端初始化
- 文件类型识别
- 文件名清理和格式化
- 下载管理(进度、暂停、取消)
- 重复文件处理
- 断点续传功能

#### `requirements.txt`
Python 依赖包列表:
- `telethon`: Telegram 客户端库
- `cryptg`: 加密库,提升性能

### Docker 相关

#### `Dockerfile`
Docker 镜像构建配置:
- 基于 Python 3.11 slim 镜像
- 安装必要的系统依赖
- 配置工作目录和环境变量
- 复制应用文件

#### `docker-compose.yml`
Docker Compose 编排配置:
- 服务定义
- 环境变量配置
- 卷映射配置
- 重启策略
- 日志配置

#### `.dockerignore`
Docker 构建时忽略的文件:
- Python 缓存文件
- Git 文件
- IDE 配置
- 临时文件

### 配置文件

#### `.env.example`
环境变量示例文件,包含:
- API_ID
- API_HASH
- BOT_TOKEN
- 路径配置

使用时复制为 `.env` 并填写实际值。

#### `.gitignore`
Git 版本控制忽略文件:
- Python 缓存
- 环境变量文件
- 会话文件
- 缓存目录
- IDE 配置

### 部署脚本

#### `deploy.sh`
自动化部署脚本:
- 检查 Docker 环境
- 验证配置文件
- 创建必要目录
- 构建镜像
- 启动服务

### 文档文件

#### `README.md`
项目主文档,包含:
- 项目介绍
- 功能特性
- 快速开始
- 安装部署
- 使用说明
- 故障排查

#### `INSTALL.md`
详细安装指南,包含:
- 前置要求
- Docker 安装
- Telegram 配置获取
- 三种部署方式
- 验证步骤
- 常见问题

#### `CHANGELOG.md`
版本更新日志:
- 版本历史
- 新功能
- Bug 修复
- 已知问题

#### `LICENSE`
MIT 开源许可证

## 运行时目录结构

部署后的完整目录结构:

```
TeleFlux/
├── [项目文件]
├── cache/                  # 缓存目录(自动创建)
│   ├── bot_session         # Telegram 会话文件
│   └── ...                 # 其他缓存
└── [宿主机映射目录]
    ├── /vol2/1000/Music/   # 音乐文件
    ├── /vol2/1000/Video/   # 视频文件
    └── /vol2/1000/Download/ # 其他文件
```

## 容器内目录结构

```
/app/                       # 应用根目录
├── bot.py                  # 主程序
├── requirements.txt        # 依赖列表
└── cache/                  # 缓存目录

/data/                      # 数据根目录
├── Music/                  # 音乐文件
├── Video/                  # 视频文件
└── Download/               # 其他文件
```

## 开发建议

### 添加新功能

1. 在 `bot.py` 中添加新的事件处理器
2. 更新 `CHANGELOG.md` 记录变更
3. 更新 `README.md` 添加功能说明
4. 测试功能
5. 提交代码

### 修改配置

1. 编辑 `.env` 文件修改运行时配置
2. 编辑 `docker-compose.yml` 修改容器配置
3. 编辑 `Dockerfile` 修改镜像配置

### 更新文档

1. 功能变更 → 更新 `README.md`
2. 安装步骤变更 → 更新 `INSTALL.md`
3. 版本发布 → 更新 `CHANGELOG.md`

---

**最后更新**: 2024-12-25
