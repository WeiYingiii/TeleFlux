#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
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

# -----------------------------
# 全局状态
# -----------------------------

# 正在进行的下载任务 (download_id -> info)
active_downloads: Dict[int, Dict[str, Any]] = {}

# 重复文件处理的临时状态 (msg_id -> info)
pending_duplicates: Dict[int, Dict[str, Any]] = {}

# 每个聊天会话的“任务面板”消息 (chat_id -> info)
chat_dashboards: Dict[int, Dict[str, Any]] = {}

# 已结束任务的简短历史 (chat_id -> list[dict])
download_history: Dict[int, List[Dict[str, Any]]] = {}

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

    # 移除类似 “_1756486628200” 这种尾随时间戳/数字后缀（常见于转存/重命名）
    # 仅移除尾部连续 8 位以上的数字，避免误伤正常标题里的数字
    name = re.sub(r'([_-])\d{8,}$', '', name)
    
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


def _human_size(num_bytes: float) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 1024:
        gb = mb / 1024
        return f"{gb:.2f}GB"
    return f"{mb:.2f}MB"


def _short_name(name: str, max_len: int = 26) -> str:
    if len(name) <= max_len:
        return name
    base, ext = os.path.splitext(name)
    keep = max_len - len(ext) - 3
    if keep <= 0:
        return name[:max_len]
    return f"{base[:keep]}...{ext}"


async def ensure_dashboard(chat_id: int):
    """确保该 chat_id 有一个统一的下载任务面板消息。"""
    info = chat_dashboards.get(chat_id)
    if info and info.get('message'):
        return info['message']

    msg = await client.send_message(
        chat_id,
        "📥 下载任务面板\n\n暂无任务",
        buttons=[[Button.inline("🔄 刷新", "dash_refresh")]]
    )
    chat_dashboards[chat_id] = {
        'message': msg,
        'lock': asyncio.Lock(),
        'last_edit_ts': 0.0,
        'last_text': "",
        'last_buttons_sig': ""
    }
    return msg


def _render_dashboard(chat_id: int) -> str:
    items = [v for v in active_downloads.values() if v.get('chat_id') == chat_id]
    items.sort(key=lambda x: x.get('created_ts', 0))

    lines: List[str] = []
    lines.append("📥 下载任务面板")
    lines.append("")

    if not items:
        lines.append("暂无正在下载的任务。")
    else:
        for idx, it in enumerate(items, start=1):
            state = it.get('state', 'downloading')
            name = _short_name(it.get('display_name') or os.path.basename(it.get('final_path', 'file')))
            total = it.get('file_size', 0) or 0
            done = it.get('downloaded', 0) or 0
            percent = (done / total * 100) if total > 0 else 0.0
            speed = it.get('speed_str', '-')
            eta = it.get('eta_str', '-')

            if state == 'paused':
                state_str = "⏸ 已暂停"
            elif state == 'cancelling':
                state_str = "🧹 正在取消"
            elif state == 'cancelled':
                state_str = "❌ 已取消"
            elif state == 'failed':
                state_str = "⚠️ 失败"
            elif state == 'completed':
                state_str = "✅ 完成"
            elif state == 'queued':
                state_str = "⏳ 排队中"
            else:
                state_str = "📥 下载中"

            bar = '█' * int(percent / 10) + '░' * (10 - int(percent / 10))
            lines.append(
                f"{idx}. {state_str} | {name}\n"
                f"[{bar}] {percent:.1f}%  ({_human_size(done)} / {_human_size(total)})\n"
                f"⚡ {speed}   ⏱️ {eta}"
            )
            lines.append("")

    # 附加历史（最近 5 条）
    hist = download_history.get(chat_id, [])[-5:]
    if hist:
        lines.append("—")
        lines.append("最近状态：")
        for h in reversed(hist):
            lines.append(f"• {h['status']} - {h['name']} {h.get('note','')}")

    return "\n".join(lines).strip()


def _buttons_signature(buttons) -> str:
    # 用于避免频繁重复编辑（Telegram 编辑频率有限）
    parts = []
    for row in buttons:
        for b in row:
            try:
                parts.append(f"{b.text}:{b.data.decode('utf-8') if hasattr(b, 'data') else ''}")
            except Exception:
                parts.append(str(b))
    return "|".join(parts)


def _build_dashboard_buttons(chat_id: int):
    items = [v for v in active_downloads.values() if v.get('chat_id') == chat_id]
    items.sort(key=lambda x: x.get('created_ts', 0))

    buttons = []
    # 每个任务一行：暂停/继续 + 取消
    for idx, it in enumerate(items, start=1):
        download_id = it['id']
        paused = it.get('paused', False)
        state = it.get('state')

        # 已取消/已完成/失败的不再显示控制按钮
        if state in {'completed', 'cancelled', 'failed'}:
            continue

        pause_text = f"⏸ {idx}" if not paused else f"▶️ {idx}"
        cancel_text = f"❌ {idx}"
        buttons.append([
            Button.inline(pause_text, f"pause_{download_id}"),
            Button.inline(cancel_text, f"cancel_{download_id}")
        ])

    # 面板操作
    buttons.append([Button.inline("🔄 刷新", "dash_refresh")])
    return buttons


async def update_dashboard(chat_id: int, force: bool = False):
    info = chat_dashboards.get(chat_id)
    if not info:
        await ensure_dashboard(chat_id)
        info = chat_dashboards.get(chat_id)

    async with info['lock']:
        now = time.time()
        # 限流：默认 1.5 秒最多编辑一次
        if not force and now - info.get('last_edit_ts', 0) < 1.5:
            return

        text = _render_dashboard(chat_id)
        buttons = _build_dashboard_buttons(chat_id)
        btn_sig = _buttons_signature(buttons)

        # 避免重复内容编辑
        if not force and text == info.get('last_text') and btn_sig == info.get('last_buttons_sig'):
            return

        try:
            await info['message'].edit(text, buttons=buttons)
            info['last_edit_ts'] = now
            info['last_text'] = text
            info['last_buttons_sig'] = btn_sig
        except Exception as e:
            logger.warning(f"更新任务面板失败: {e}")


def _push_history(chat_id: int, name: str, status: str, note: str = ""):
    lst = download_history.setdefault(chat_id, [])
    lst.append({'name': name, 'status': status, 'note': note, 'ts': time.time()})
    # 控制大小
    if len(lst) > 30:
        del lst[:-30]


async def _remove_download_after(download_id: int, delay: float = 3.0):
    await asyncio.sleep(delay)
    active_downloads.pop(download_id, None)


async def download_with_progress(download_id: int):
    """下载任务执行体：更新 active_downloads 状态，并驱动统一任务面板刷新。"""
    info = active_downloads.get(download_id)
    if not info:
        return

    message = info['message']
    chat_id = info['chat_id']
    final_path = info['final_path']
    temp_path = info['temp_path']

    file_size = int(info.get('file_size', 0) or 0)
    resume_from = int(info.get('resume_from', 0) or 0)

    last_update_ts = 0.0
    last_bytes = resume_from
    last_ts = time.time()

    async def progress_callback(current, total):
        nonlocal last_update_ts, last_bytes, last_ts

        # current 为本次 session 的已下载量；加上 resume_from 才是总计
        downloaded = int(current) + resume_from
        info['downloaded'] = downloaded

        # 暂停控制：在 callback 内阻塞最安全（Telethon 会持续调用）
        while info.get('paused', False):
            info['state'] = 'paused'
            await update_dashboard(chat_id)
            await asyncio.sleep(0.5)

        info['state'] = 'downloading'

        # 速度/ETA
        now = time.time()
        dt = max(now - last_ts, 1e-6)
        db = downloaded - last_bytes
        speed_bps = db / dt
        last_bytes = downloaded
        last_ts = now

        if speed_bps <= 0:
            info['speed_str'] = '-'
            info['eta_str'] = '-'
        else:
            speed_mb = speed_bps / (1024 * 1024)
            info['speed_str'] = f"{speed_mb:.2f} MB/s" if speed_mb >= 1 else f"{(speed_bps/1024):.1f} KB/s"
            remaining = max(file_size - downloaded, 0)
            eta = remaining / speed_bps
            if eta < 60:
                info['eta_str'] = f"{int(eta)}秒"
            elif eta < 3600:
                info['eta_str'] = f"{int(eta/60)}分{int(eta%60)}秒"
            else:
                h = int(eta/3600)
                m = int((eta%3600)/60)
                info['eta_str'] = f"{h}时{m}分"

        # 限流刷新
        if now - last_update_ts > 1.5:
            last_update_ts = now
            await update_dashboard(chat_id)

    try:
        info['state'] = 'downloading'
        await update_dashboard(chat_id, force=True)

        mode = 'ab' if resume_from > 0 else 'wb'
        with open(temp_path, mode) as f:
            if resume_from > 0:
                async for chunk in client.iter_download(message.media, offset=resume_from):
                    f.write(chunk)
                    await progress_callback(f.tell() - resume_from, file_size - resume_from)
            else:
                await client.download_media(
                    message.media,
                    file=f,
                    progress_callback=progress_callback
                )

        os.rename(temp_path, final_path)
        info['state'] = 'completed'
        info['downloaded'] = file_size
        _push_history(chat_id, info['display_name'], "✅ 完成")
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_remove_download_after(download_id, delay=5.0))

    except asyncio.CancelledError:
        # task.cancel() 或其他 CancelledError
        info['state'] = 'cancelled'
        _push_history(chat_id, info['display_name'], "❌ 已取消")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_remove_download_after(download_id, delay=5.0))

    except Exception as e:
        logger.error(f"下载失败: {e}")
        info['state'] = 'failed'
        _push_history(chat_id, info['display_name'], "⚠️ 失败", note=f"({type(e).__name__})")
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_remove_download_after(download_id, delay=8.0))


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
        
        # 临时保存重复处理所需信息
        pending_duplicates[id(message)] = {
            'message': message,
            'file_type': file_type,
            'target_path': target_path,
            'filename': formatted_filename,
            'chat_id': event.chat_id,
        }
        return
    
    # 没有重复,直接下载
    await start_download(message, event.chat_id, file_type, target_path, formatted_filename, truncate_notice)


async def start_download(message, chat_id, file_type, target_path, filename, truncate_notice: str = ""):
    """开始下载：创建任务并把多个任务统一展示到同一个面板消息。"""
    await ensure_dashboard(chat_id)

    filepath = os.path.join(target_path, filename)
    temp_filepath = filepath + '.downloading'

    # 断点续传
    resume_from = 0
    if os.path.exists(temp_filepath):
        resume_from = os.path.getsize(temp_filepath)
        logger.info(f"恢复下载从 {resume_from} 字节: {filename}")

    download_id = id(message)
    file_size = int(message.file.size or 0)

    type_emoji = '🎵' if file_type == 'audio' else '🎬' if file_type == 'video' else '📄'

    active_downloads[download_id] = {
        'id': download_id,
        'message': message,
        'chat_id': chat_id,
        'file_type': file_type,
        'type_emoji': type_emoji,
        'display_name': filename,
        'target_path': target_path,
        'final_path': filepath,
        'temp_path': temp_filepath,
        'file_size': file_size,
        'resume_from': resume_from,
        'downloaded': resume_from,
        'speed_str': '-',
        'eta_str': '-',
        'paused': False,
        'state': 'queued',
        'created_ts': time.time(),
        'truncate_notice': truncate_notice,
        'cancel_requested_ts': None,
        'task': None,
    }

    # 推送一条“准备”历史（保持轻量，不刷屏）
    _push_history(chat_id, filename, f"{type_emoji} 已加入队列")

    # 创建下载任务（关键：支持并发、多任务统一面板）
    task = asyncio.create_task(download_with_progress(download_id))
    active_downloads[download_id]['task'] = task

    await update_dashboard(chat_id, force=True)


@client.on(events.CallbackQuery)
async def handle_callback(event):
    """处理按钮回调"""
    data = event.data.decode('utf-8')

    # 面板刷新
    if data == 'dash_refresh':
        await event.answer("已刷新", alert=False)
        await update_dashboard(event.chat_id, force=True)
        return
    
    if data.startswith('overwrite_'):
        msg_id = int(data.split('_')[1])
        if msg_id in pending_duplicates:
            info = pending_duplicates.pop(msg_id)
            await event.edit("♻️ 开始覆盖下载...")
            await start_download(
                info['message'],
                info['chat_id'],
                info['file_type'],
                info['target_path'],
                info['filename'],
                ""  # 覆盖时不显示截断提示
            )
        else:
            await event.answer("该任务已处理或已过期", alert=False)
    
    elif data.startswith('rename_'):
        msg_id = int(data.split('_')[1])
        if msg_id in pending_duplicates:
            info = pending_duplicates.pop(msg_id)
            new_filename = get_next_filename(info['target_path'], info['filename'])
            await event.edit(f"➕ 使用新文件名: {new_filename}")
            await start_download(
                info['message'],
                info['chat_id'],
                info['file_type'],
                info['target_path'],
                new_filename,
                ""  # 重命名时不显示截断提示
            )
        else:
            await event.answer("该任务已处理或已过期", alert=False)
    
    elif data.startswith('cancel_dup_'):
        msg_id = int(data.split('_')[2])
        pending_duplicates.pop(msg_id, None)
        await event.edit("❌ 已取消下载")
    
    elif data.startswith('pause_'):
        download_id = int(data.split('_')[1])
        if download_id in active_downloads:
            it = active_downloads[download_id]
            it['paused'] = not it.get('paused', False)
            it['state'] = 'paused' if it['paused'] else 'downloading'
            status = "⏸ 已暂停" if it['paused'] else "▶️ 继续下载"
            _push_history(it['chat_id'], it['display_name'], status)
            await event.answer(status, alert=False)
            await update_dashboard(it['chat_id'], force=True)
        else:
            await event.answer("任务不存在或已结束", alert=False)
    
    elif data.startswith('cancel_'):
        download_id = int(data.split('_')[1])
        if download_id in active_downloads:
            it = active_downloads[download_id]
            it['state'] = 'cancelling'
            it['cancel_requested_ts'] = time.time()

            # 关键：直接取消 asyncio Task，避免“正在取消”卡住
            task = it.get('task')
            if task and not task.done():
                task.cancel()

            _push_history(it['chat_id'], it['display_name'], "🧹 取消中")
            await event.answer("已请求取消", alert=False)
            await update_dashboard(it['chat_id'], force=True)
        else:
            await event.answer("任务不存在或已结束", alert=False)


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
    logger.info("🚀 TeleFlux Bot v1.1.1 启动中...")
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
