FROM python:3.11-slim

LABEL maintainer="TeleFlux"
LABEL version="1.1.1"
LABEL description="Telegram File Download Bot with Auto Classification and Smart Optimization"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY bot.py .

# 创建数据目录
RUN mkdir -p /data/Music /data/Video /data/Download /app/cache

# 设置环境变量默认值
ENV MUSIC_PATH=/data/Music
ENV VIDEO_PATH=/data/Video
ENV DOWNLOAD_PATH=/data/Download
ENV CACHE_PATH=/app/cache

# 运行机器人
CMD ["python", "-u", "bot.py"]
