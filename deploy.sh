#!/bin/bash

# TeleFlux 快速部署脚本
# 使用方法: ./deploy.sh

set -e

echo "================================================"
echo "  TeleFlux - Telegram 文件下载机器人"
echo "  版本: 1.0.0"
echo "================================================"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装,请先安装 Docker"
    echo "访问: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装,请先安装 Docker Compose"
    echo "访问: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件,正在创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件,填入你的配置信息:"
    echo ""
    echo "   nano .env"
    echo ""
    echo "需要填写:"
    echo "  - API_ID: 从 https://my.telegram.org/apps 获取"
    echo "  - API_HASH: 从 https://my.telegram.org/apps 获取"
    echo "  - BOT_TOKEN: 从 @BotFather 获取"
    echo ""
    echo "填写完成后,重新运行此脚本: ./deploy.sh"
    exit 0
fi

# 检查配置是否填写
if grep -q "your_api_id" .env || grep -q "your_api_hash" .env || grep -q "your_bot_token" .env; then
    echo "❌ 请先在 .env 文件中填写正确的配置信息"
    echo ""
    echo "编辑配置: nano .env"
    exit 1
fi

echo "✅ 配置文件检查通过"
echo ""

# 创建必要的目录
echo "📁 创建存储目录..."
mkdir -p cache
mkdir -p /vol2/1000/Music
mkdir -p /vol2/1000/Video
mkdir -p /vol2/1000/Download
echo "✅ 目录创建完成"
echo ""

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker build -t teleflux:latest .
echo "✅ 镜像构建完成"
echo ""

# 停止旧容器(如果存在)
if docker ps -a | grep -q teleflux-bot; then
    echo "🔄 停止旧容器..."
    docker-compose down
fi

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "================================================"
echo "  ✅ TeleFlux 部署成功!"
echo "================================================"
echo ""
echo "📊 查看日志:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "   docker-compose down"
echo ""
echo "🔄 重启服务:"
echo "   docker-compose restart"
echo ""
echo "📝 现在可以在 Telegram 中向你的机器人发送文件了!"
echo ""
