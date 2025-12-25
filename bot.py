#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeAudio, DocumentAttributeVideo
import logging

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量获取配置
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# 验证必需的环境变量
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("=" * 60)
    logger.error("❌ 缺少必需的环境变量!")
    logger.error("=" * 60)
    logger.error("")
    logger.error("请设置以下环境变量:")
    if not API_ID:
        logger.error("  ❌ API_ID 未设置")
    if not API_HASH:
        logger.error("  ❌ API_HASH 未设置")
    if not BOT_TOKEN:
        logger.error("  ❌ BOT_TOKEN 未设置")
    logger.error("")
    logger.error("🔧 解决方法:")
    logger.error("")
    logger.error("方法 1 - 使用 .env 文件:")
    logger.error("  1. 复制 .env.example 为 .env")
    logger.error("  2. 编辑 .env 文件填入你的配置")
    logger.error("  3. 在 docker-compose.yml 中添加 env_file:")
    logger.error("     env_file:")
    logger.error("       - .env")
    logger.error("")
    logger.error("方法 2 - 直接在 docker-compose.yml 中设置:")
    logger.error("  environment:")
    logger.error("    - API_ID=你的实际API_ID")
    logger.error("    - API_HASH=你的实际API_HASH")
    logger.error("    - BOT_TOKEN=你的实际BOT_TOKEN")
    logger.error("")
    logger.error("方法 3 - docker run 时使用 -e 参数:")
    logger.error("  docker run -e API_ID=xxx -e API_HASH=xxx -e BOT_TOKEN=xxx ...")
    logger.error("")
    logger.error("📖 获取配置信息:")
    logger.error("  API_ID 和 API_HASH: https://my.telegram.org/apps")
    logger.error("  BOT_TOKEN: 从 @BotFather 获取")
    logger.error("")
    logger.error("=" * 60)
    exit(1)

# 检查是否使用了示例值
if API_ID in ['your_api_id', 'your_API_ID', '你的_API_ID']:
    logger.error("❌ 请将 API_ID 替换为实际的数字 ID")
    logger.error("示例: API_ID=12345678")
    exit(1)

if API_HASH in ['your_api_hash', 'your_API_HASH', '你的_API_HASH']:
    logger.error("❌ 请将 API_HASH 替换为实际的 Hash 值")
    logger.error("示例: API_HASH=abcdef1234567890abcdef1234567890")
    exit(1)

if BOT_TOKEN in ['your_bot_token', 'your_BOT_TOKEN', '你的_BOT_TOKEN']:
    logger.error("❌ 请将 BOT_TOKEN 替换为实际的 Token")
    logger.error("示例: BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
    exit(1)

# 验证 API_ID 格式
try:
    API_ID = int(API_ID)
except ValueError:
    logger.error(f"❌ API_ID 格式错误: '{API_ID}'")
    logger.error("API_ID 应该是纯数字,例如: 12345678")
    exit(1)

# 下载路径配置 (支持自定义)
MUSIC_PATH = os.getenv('MUSIC_PATH', '/vol2/1000/Music')
VIDEO_PATH = os.getenv('VIDEO_PATH', '/vol2/1000/Video')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH', '/vol2/1000/Download')
CACHE_PATH = os.getenv('CACHE_PATH', './cache')

# 全局下载管理
active_downloads: Dict[int, dict] = {}

# 确保所有目录存在
for path in [MUSIC_PATH, VIDEO_PATH, DOWNLOAD_PATH, CACHE_PATH]:
    os.makedirs(path, exist_ok=True)

# 初始化客户端
client = TelegramClient(
    os.path.join(CACHE_PATH, 'bot_session'),
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)


def sanitize_filename(filename: str, is_video: bool = False) -> tuple:
    """清理文件名,移除特殊字符和广告,返回(清理后的文件名, 是否被截断, 原始关键信息)"""
    # 移除扩展名
    name, ext = os.path.splitext(filename)
    original_name = name  # 保存原始名称用于提示
    was_truncated = False
    
    # 常见广告关键词
    ad_patterns = [
        r'@\w+', r'www\.[\w\.]+', r'http[s]?://\S+',
        r'[\u4e00-\u9fa5]*广告[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*推广[\u4e00-\u9fa5]*',
        r'[\u4e00-\u9fa5]*官网[\u4e00-\u9fa5]*',
        r'\[.*?\]', r'\(.*?\)',
        r'VIP', r'高清', r'超清', r'蓝光', r'HD', r'4K', r'1080[pP]', r'720[pP]'
    ]
    
    for pattern in ad_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # 移除特殊字符,只保留字母数字中文和基本符号
    name = re.sub(r'[^\w\u4e00-\u9fa5\-_\s]', '', name)
    
    # 移除多余空格
    name = re.sub(r'\s+', ' ', name).strip()
    
    # 提取关键词信息
    key_info = ""
    
    # 超长文件名处理（超过50个字符认为是超长）
    if len(name) > 50:
        was_truncated = True
        # 提取关键词
        words = name.split()
        
        if is_video:
            # 视频文件：尝试提取年份、季数、集数等关键信息
            year_match = re.search(r'(19|20)\d{2}', name)
            season_match = re.search(r'[Ss](\d{1,2})', name)
            episode_match = re.search(r'[Ee](\d{1,3})', name)
            
            key_parts = []
            # 取前3-5个词作为标题
            if len(words) >= 3:
                key_parts.extend(words[:3])
            else:
                key_parts.extend(words)
            
            # 添加关键信息
            if year_match:
                key_parts.append(year_match.group())
            if season_match and episode_match:
                key_parts.append(f"S{season_match.group(1)}E{episode_match.group(1)}")
            elif season_match:
                key_parts.append(f"S{season_match.group(1)}")
            elif episode_match:
                key_parts.append(f"E{episode_match.group(1)}")
            
            name = ' '.join(key_parts)[:40]  # 视频文件名限制在40字符
            key_info = f"提取关键信息: {name}"
            
        else:
            # 其他文件：取前面重要词汇
            if len(words) >= 5:
                name = ' '.join(words[:5])[:40]
                key_info = f"提取前缀: {name}"
            else:
                name = name[:40]
                key_info = f"截取: {name}"
    
    # 如果清理后为空,返回时间戳
    if not name:
        name = f"file_{int(time.time())}"
        was_truncated = True
        key_info = "使用时间戳命名"
    
    return f"{name}{ext}", was_truncated, key_info or original_name[:50]


def format_filename_by_type(filename: str, file_type: str, attributes) -> tuple:
    """根据文件类型格式化文件名，返回(文件名, 是否被截断, 提示信息)"""
    if file_type == 'audio':
        # 尝试从属性中获取歌曲信息
        for attr in attributes:
            if isinstance(attr, DocumentAttributeAudio):
                title = attr.title or ''
                performer = attr.performer or ''
                if title and performer:
                    ext = os.path.splitext(filename)[1]
                    new_name, truncated, info = sanitize_filename(f"{title}-{performer}{ext}")
                    return new_name, truncated, info
        return sanitize_filename(filename)
    
    elif file_type == 'video':
        return sanitize_filename(filename, is_video=True)
    
    else:
        return sanitize_filename(filename)


def get_file_type(message) -> tuple:
    """判断文件类型"""
    if not message.media or not hasattr(message.media, 'document'):
        return 'other', DOWNLOAD_PATH
    
    document = message.media.document
    mime_type = document.mime_type or ''
    
    # 检查音频
    if mime_type.startswith('audio/') or any(
        isinstance(attr, DocumentAttributeAudio) and not attr.voice 
        for attr in document.attributes
    ):
        return 'audio', MUSIC_PATH
    
    # 检查视频
    if mime_type.startswith('video/') or any(
        isinstance(attr, DocumentAttributeVideo) 
        for attr in document.attributes
    ):
        return 'video', VIDEO_PATH
    
    return 'other', DOWNLOAD_PATH


def get_filename(message) -> str:
    """获取文件名"""
    if hasattr(message.media, 'document'):
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name
    return f"file_{int(time.time())}"


def check_duplicate_file(target_path: str, filename: str) -> Optional[str]:
    """检查是否存在重复文件"""
    filepath = os.path.join(target_path, filename)
    if os.path.exists(filepath):
        return filepath
    return None


def get_next_filename(target_path: str, filename: str) -> str:
    """获取带序列号的文件名"""
    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_filename = f"{name}_{counter}{ext}"
        if not os.path.exists(os.path.join(target_path, new_filename)):
            return new_filename
        counter += 1


async def download_with_progress(message, filepath: str, chat_id: int, progress_msg, display_filename: str = None):
    """带进度条的下载函数"""
    download_id = id(message)
    temp_filepath = filepath + '.downloading'
    
    # 检查是否有未完成的下载(断点续传)
    resume_from = 0
    if os.path.exists(temp_filepath):
        resume_from = os.path.getsize(temp_filepath)
        logger.info(f"恢复下载从 {resume_from} 字节")
    
    active_downloads[download_id] = {
        'paused': False,
        'cancelled': False,
        'filepath': temp_filepath,
        'message': message,
        'chat_id': chat_id
    }
    
    file_size = message.file.size
    last_update = 0
    downloaded = resume_from
    start_time = time.time()
    last_downloaded = resume_from
    last_time = start_time
    
    # 使用传入的显示文件名，如果没有则使用路径中的文件名
    show_filename = display_filename or os.path.basename(filepath)
    # 文件名过长时截断
    if len(show_filename) > 30:
        name, ext = os.path.splitext(show_filename)
        show_filename = name[:27] + "..." + ext
    
    async def progress_callback(current, total):
        nonlocal last_update, downloaded, last_downloaded, last_time
        downloaded = current + resume_from
        
        # 检查是否暂停
        while active_downloads.get(download_id, {}).get('paused', False):
            await asyncio.sleep(0.5)
            if active_downloads.get(download_id, {}).get('cancelled', False):
                raise asyncio.CancelledError("下载已取消")
        
        # 检查是否取消
        if active_downloads.get(download_id, {}).get('cancelled', False):
            raise asyncio.CancelledError("下载已取消")
        
        current_time = time.time()
        if current_time - last_update > 2:  # 每2秒更新一次
            percent = (downloaded / file_size) * 100 if file_size > 0 else 0
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = file_size / (1024 * 1024)
            
            # 计算下载速度
            time_diff = current_time - last_time
            bytes_diff = downloaded - last_downloaded
            speed_bytes = bytes_diff / time_diff if time_diff > 0 else 0
            speed_mb = speed_bytes / (1024 * 1024)
            
            # 计算剩余时间
            remaining_bytes = file_size - downloaded
            eta_seconds = remaining_bytes / speed_bytes if speed_bytes > 0 else 0
            
            # 格式化剩余时间
            if eta_seconds < 60:
                eta_str = f"{int(eta_seconds)}秒"
            elif eta_seconds < 3600:
                eta_str = f"{int(eta_seconds / 60)}分{int(eta_seconds % 60)}秒"
            else:
                hours = int(eta_seconds / 3600)
                minutes = int((eta_seconds % 3600) / 60)
                eta_str = f"{hours}时{minutes}分"
            
            # 格式化速度
            if speed_mb >= 1:
                speed_str = f"{speed_mb:.2f} MB/s"
            else:
                speed_kb = speed_bytes / 1024
                speed_str = f"{speed_kb:.1f} KB/s"
            
            # 进度条缩短到10个字符（原来是20个）
            progress_bar = '█' * int(percent / 10) + '░' * (10 - int(percent / 10))
            
            try:
                await progress_msg.edit(
                    f"📥 下载中\n\n"
                    f"📄 {show_filename}\n"
                    f"[{progress_bar}] {percent:.1f}%\n\n"
                    f"📦 {downloaded_mb:.2f}MB / {total_mb:.2f}MB\n"
                    f"⚡ 速度: {speed_str}\n"
                    f"⏱️ 剩余: {eta_str}",
                    buttons=[
                        [Button.inline("⏸ 暂停" if not active_downloads[download_id]['paused'] else "▶️ 继续", 
                                      f"pause_{download_id}")],
                        [Button.inline("❌ 取消", f"cancel_{download_id}")]
                    ]
                )
            except Exception as e:
                logger.warning(f"更新进度失败: {e}")
            
            last_update = current_time
            last_downloaded = downloaded
            last_time = current_time
    
    try:
        # 使用 MTProto 下载(支持大文件)
        mode = 'ab' if resume_from > 0 else 'wb'
        with open(temp_filepath, mode) as f:
            if resume_from > 0:
                # 断点续传
                async for chunk in client.iter_download(message.media, offset=resume_from):
                    if active_downloads.get(download_id, {}).get('cancelled', False):
                        raise asyncio.CancelledError("下载已取消")
                    f.write(chunk)
                    await progress_callback(f.tell() - resume_from, file_size - resume_from)
            else:
                # 正常下载
                await client.download_media(
                    message.media,
                    file=f,
                    progress_callback=progress_callback
                )
        
        # 下载完成,重命名文件
        os.rename(temp_filepath, filepath)
        
        return True
        
    except asyncio.CancelledError:
        logger.info(f"下载被取消: {filepath}")
        # 删除未完成的文件
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        return False
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return False
    finally:
        if download_id in active_downloads:
            del active_downloads[download_id]


@client.on(events.NewMessage)
async def handle_file(event):
    """处理接收到的文件"""
    message = event.message
    
    # 检查是否是文件
    if not message.media or not hasattr(message.media, 'document'):
        return
    
    # 获取文件类型和目标路径
    file_type, target_path = get_file_type(message)
    
    # 获取原始文件名
    original_filename = get_filename(message)
    
    # 格式化文件名
    formatted_filename, was_truncated, key_info = format_filename_by_type(
        original_filename, 
        file_type, 
        message.media.document.attributes
    )
    
    # 如果文件名被截断或处理过，显示提示
    truncate_notice = ""
    if was_truncated:
        truncate_notice = f"\n💡 原文件名过长，已优化为:\n📝 {key_info}\n"
    
    # 检查重复文件
    duplicate_path = check_duplicate_file(target_path, formatted_filename)
    
    if duplicate_path:
        # 有重复文件,显示选项
        file_size_mb = message.file.size / (1024 * 1024)
        await event.respond(
            f"⚠️ 检测到重复文件\n\n"
            f"📁 文件名: {formatted_filename}\n"
            f"📦 大小: {file_size_mb:.2f}MB\n"
            f"📂 类型: {'🎵 音乐' if file_type == 'audio' else '🎬 视频' if file_type == 'video' else '📄 其他'}\n"
            f"{truncate_notice}\n"
            f"请选择操作:",
            buttons=[
                [Button.inline("♻️ 覆盖", f"overwrite_{id(message)}")],
                [Button.inline("➕ 加序号", f"rename_{id(message)}")],
                [Button.inline("❌ 取消", f"cancel_dup_{id(message)}")]
            ]
        )
        
        # 临时保存消息信息
        active_downloads[id(message)] = {
            'message': message,
            'file_type': file_type,
            'target_path': target_path,
            'filename': formatted_filename,
            'chat_id': event.chat_id,
            'display_name': formatted_filename  # 用于显示
        }
        return
    
    # 没有重复,直接下载
    await start_download(message, event.chat_id, file_type, target_path, formatted_filename, truncate_notice)


async def start_download(message, chat_id, file_type, target_path, filename, truncate_notice=""):
    """开始下载文件"""
    file_size_mb = message.file.size / (1024 * 1024)
    
    type_emoji = '🎵' if file_type == 'audio' else '🎬' if file_type == 'video' else '📄'
    
    progress_msg = await client.send_message(
        chat_id,
        f"{type_emoji} 准备下载...\n\n"
        f"📁 文件名: {filename}\n"
        f"📦 大小: {file_size_mb:.2f}MB\n"
        f"📂 保存到: {target_path}"
        f"{truncate_notice}"
    )
    
    filepath = os.path.join(target_path, filename)
    
    success = await download_with_progress(message, filepath, chat_id, progress_msg, filename)
    
    if success:
        await progress_msg.edit(
            f"✅ 下载完成!\n\n"
            f"📁 {filename}\n"
            f"📦 {file_size_mb:.2f}MB\n"
            f"📂 {target_path}"
        )
    else:
        await progress_msg.edit(
            f"❌ 下载已取消\n\n"
            f"📁 {filename}\n"
            f"临时文件已清理"
        )


@client.on(events.CallbackQuery)
async def handle_callback(event):
    """处理按钮回调"""
    data = event.data.decode('utf-8')
    
    if data.startswith('overwrite_'):
        msg_id = int(data.split('_')[1])
        if msg_id in active_downloads:
            info = active_downloads[msg_id]
            await event.edit("♻️ 开始覆盖下载...")
            del active_downloads[msg_id]
            await start_download(
                info['message'],
                info['chat_id'],
                info['file_type'],
                info['target_path'],
                info['filename'],
                ""  # 覆盖时不显示截断提示
            )
    
    elif data.startswith('rename_'):
        msg_id = int(data.split('_')[1])
        if msg_id in active_downloads:
            info = active_downloads[msg_id]
            new_filename = get_next_filename(info['target_path'], info['filename'])
            await event.edit(f"➕ 使用新文件名: {new_filename}")
            del active_downloads[msg_id]
            await start_download(
                info['message'],
                info['chat_id'],
                info['file_type'],
                info['target_path'],
                new_filename,
                ""  # 重命名时不显示截断提示
            )
    
    elif data.startswith('cancel_dup_'):
        msg_id = int(data.split('_')[2])
        if msg_id in active_downloads:
            del active_downloads[msg_id]
        await event.edit("❌ 已取消下载")
    
    elif data.startswith('pause_'):
        download_id = int(data.split('_')[1])
        if download_id in active_downloads:
            active_downloads[download_id]['paused'] = not active_downloads[download_id]['paused']
            status = "⏸ 已暂停" if active_downloads[download_id]['paused'] else "▶️ 继续下载"
            await event.answer(status)
    
    elif data.startswith('cancel_'):
        download_id = int(data.split('_')[1])
        if download_id in active_downloads:
            active_downloads[download_id]['cancelled'] = True
            # 立即给出反馈
            await event.answer("❌ 取消请求已接收", alert=False)
            # 更新消息显示取消状态
            try:
                await event.edit(
                    f"❌ 正在取消下载...\n\n"
                    f"请稍候，正在清理临时文件..."
                )
            except Exception as e:
                logger.warning(f"更新取消状态失败: {e}")


@client.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    """启动命令"""
    await event.respond(
        "🤖 TeleFlux 文件下载机器人\n\n"
        "📥 发送任何文件,我会自动分类下载:\n\n"
        "🎵 音乐 → Music\n"
        "🎬 视频 → Video\n"
        "📄 其他 → Download\n\n"
        "✨ 功能特性:\n"
        "• 智能文件名清理\n"
        "• 重复文件检测\n"
        "• 实时进度显示\n"
        "• 暂停/继续下载\n"
        "• 大文件支持\n"
        "• 断点续传\n\n"
        "开始发送文件吧! 🚀"
    )


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 TeleFlux Bot v1.1.0 启动中...")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📂 配置路径:")
    logger.info(f"  🎵 音乐: {MUSIC_PATH}")
    logger.info(f"  🎬 视频: {VIDEO_PATH}")
    logger.info(f"  📄 其他: {DOWNLOAD_PATH}")
    logger.info(f"  💾 缓存: {CACHE_PATH}")
    logger.info("")
    logger.info("✅ 配置验证通过,开始连接 Telegram...")
    logger.info("=" * 60)
    
    client.run_until_disconnected()


if __name__ == '__main__':
    main()
