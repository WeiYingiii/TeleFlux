# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import re
import asyncio
import time
from urllib.parse import urlparse, unquote
from pathlib import Path
from typing import Optional, Dict, Any, List
from telethon import TelegramClient, events, Button
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeAudio,
    DocumentAttributeVideo,
)
from telethon.errors.rpcerrorlist import MessageNotModifiedError
from telethon.errors import FloodWaitError, RPCError
import logging
from logging.handlers import RotatingFileHandler
from collections import deque

from task_manager import TaskManager
from runtime_settings import (
    RuntimeSettings,
    default_settings_path,
    load_settings,
    save_settings,
)

try:
    import socks  # type: ignore
except Exception:  # pragma: no cover
    socks = None

LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, "teleflux.log")


class _ChineseLevelFormatter(logging.Formatter):
    _LEVEL_MAP = {
        "DEBUG": "调试",
        "INFO": "信息",
        "WARNING": "警告",
        "ERROR": "错误",
        "CRITICAL": "致命",
    }

    def format(self, record: logging.LogRecord) -> str:
        setattr(record, "levelname_cn", self._LEVEL_MAP.get(record.levelname, record.levelname))
        return super().format(record)


def _setup_logging() -> logging.Logger:
    """Configure logging for container runtime.

    Requirements from deployment:
      - Container logs should be Chinese as much as possible.
      - Provide an internal log file for Telegram /log streaming.
    """

    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = _ChineseLevelFormatter(
        fmt="%(asctime)s | %(name)s | %(levelname_cn)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stdout)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Rotating file handler (for /log)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Suppress noisy English logs from Telethon at INFO level.
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("telethon.client.downloads").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = _setup_logging()

# 项目版本
VERSION = "1.0.15"

# 从环境变量获取配置
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    logger.error("方法 1 - 直接在 docker-compose.yml 中设置:")
    logger.error("  environment:")
    logger.error("    - API_ID=你的实际API_ID")
    logger.error("    - API_HASH=你的实际API_HASH")
    logger.error("    - BOT_TOKEN=你的实际BOT_TOKEN")
    logger.error("")
    logger.error("方法 2 - docker run 时使用 -e 参数:")
    logger.error("  docker run -e API_ID=xxx -e API_HASH=xxx -e BOT_TOKEN=xxx ...")
    logger.error("")
    logger.error("📖 获取配置信息:")
    logger.error("  API_ID 和 API_HASH: https://my.telegram.org/apps")
    logger.error("  BOT_TOKEN: 从 @BotFather 获取")
    logger.error("")
    logger.error("=" * 60)
    exit(1)

# 检查是否使用了示例值
if API_ID in ["your_api_id", "your_API_ID", "你的_API_ID"]:
    logger.error("❌ 请将 API_ID 替换为实际的数字 ID")
    logger.error("示例: API_ID=12345678")
    exit(1)

if API_HASH in ["your_api_hash", "your_API_HASH", "你的_API_HASH"]:
    logger.error("❌ 请将 API_HASH 替换为实际的 Hash 值")
    logger.error("示例: API_HASH=abcdef1234567890abcdef1234567890")
    exit(1)

if BOT_TOKEN in ["your_bot_token", "your_BOT_TOKEN", "你的_BOT_TOKEN"]:
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
MUSIC_PATH = os.getenv("MUSIC_PATH", "/vol2/1000/Music")
VIDEO_PATH = os.getenv("VIDEO_PATH", "/vol2/1000/Video")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "/vol2/1000/Download")
CACHE_PATH = os.getenv("CACHE_PATH", "./cache")

# 管理类命令权限（可选）
# - 未设置时：只允许在私聊中执行 /proxy、/concurrency
# - 设置后：允许指定用户 ID 在任意聊天执行
def _parse_int_set(value: str) -> set[int]:
    out: set[int] = set()
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            continue
    return out


ADMIN_USER_IDS = _parse_int_set(os.getenv("ADMIN_USER_IDS", ""))


def _parse_int_list(value: str) -> list[int]:
    out: list[int] = []
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            continue
    return out


STARTUP_NOTIFY_CHAT_IDS = _parse_int_list(os.getenv("STARTUP_NOTIFY_CHAT_ID", "") or os.getenv("STARTUP_NOTIFY_CHAT_IDS", ""))

# 运行时可持久化设置（通过 Telegram /命令修改，保存到 cache 目录）
SETTINGS_PATH = default_settings_path(CACHE_PATH)
runtime_settings = load_settings(SETTINGS_PATH)


class ConcurrencyLimiter:
    """A dynamic concurrency limiter that can be adjusted at runtime.

    asyncio.Semaphore cannot be resized safely. This limiter keeps a running
    counter and a condition to support changing the limit while the bot runs.
    """

    def __init__(self, limit: int):
        self._limit = max(1, int(limit))
        self._running = 0
        self._cond = asyncio.Condition()

    async def acquire(self) -> None:
        async with self._cond:
            while self._running >= self._limit:
                await self._cond.wait()
            self._running += 1

    async def release(self) -> None:
        async with self._cond:
            self._running -= 1
            if self._running < 0:
                self._running = 0
            self._cond.notify_all()

    async def set_limit(self, new_limit: int) -> None:
        async with self._cond:
            self._limit = max(1, int(new_limit))
            self._cond.notify_all()

    def get_limit(self) -> int:
        return self._limit

    def get_running(self) -> int:
        return self._running

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()


def _parse_int_list_env(name: str) -> List[int]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return []
    out: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            continue
    return out


def _apply_env_proxy(proxy_url: Optional[str]) -> None:
    keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    if proxy_url:
        for k in keys:
            os.environ[k] = proxy_url
    else:
        for k in keys:
            os.environ.pop(k, None)


def _telethon_proxy_from_url(proxy_url: str):
    """Convert a proxy URL to Telethon's proxy tuple.

    Supported schemes: socks5, socks5h, socks4, socks4a, http, https.
    """
    if not proxy_url:
        return None

    if socks is None:
        raise RuntimeError("pysocks is not installed; cannot use proxy")

    p = urlparse(proxy_url)
    scheme = (p.scheme or "").lower()
    host = p.hostname
    port = p.port
    if not host or not port:
        raise ValueError("proxy url must include host and port")

    username = unquote(p.username) if p.username else None
    password = unquote(p.password) if p.password else None

    rdns = True
    if scheme in ("socks5", "socks5h"):
        proxy_type = socks.SOCKS5
        rdns = True
    elif scheme in ("socks4", "socks4a"):
        proxy_type = socks.SOCKS4
        rdns = True
    elif scheme in ("http", "https"):
        proxy_type = socks.HTTP
        rdns = False
    else:
        raise ValueError(f"unsupported proxy scheme: {scheme}")

    if username is not None or password is not None:
        return (proxy_type, host, int(port), rdns, username or "", password or "")
    return (proxy_type, host, int(port), rdns)

# -----------------------------
# 全局状态
# -----------------------------

# 正在进行的下载任务 (download_id -> info)
active_downloads: Dict[int, Dict[str, Any]] = {}

# 重复文件处理的临时状态 (msg_id -> info)
pending_duplicates: Dict[int, Dict[str, Any]] = {}

# 每个聊天会话的“任务面板”消息 (chat_id -> info)
chat_dashboards: Dict[int, Dict[str, Any]] = {}

# 避免同一 chat 在并发情况下重复创建面板消息
dashboard_create_locks: Dict[int, asyncio.Lock] = {}

# 已结束任务的简短历史 (chat_id -> list[dict])
download_history: Dict[int, List[Dict[str, Any]]] = {}

# 并发安全的任务计数与“延迟清理”管理器
# - 当某个 chat 的任务数降为 0 时，5 秒后执行一次清理回调（若期间无新任务）
task_manager = TaskManager(cleanup_delay_s=5.0)

# 代理（通过 /proxy 命令写入 settings 后，重启容器生效）
proxy_url_effective = (
    os.getenv("TELEFLUX_PROXY")
    or os.getenv("PROXY_URL")
    or runtime_settings.proxy_url
)
_apply_env_proxy(proxy_url_effective)

telethon_proxy = None
if proxy_url_effective:
    try:
        telethon_proxy = _telethon_proxy_from_url(proxy_url_effective)
        logger.info("已启用代理（来自设置/环境变量）。")
    except Exception as e:
        logger.error("代理配置无效，已忽略：%s（%s）", proxy_url_effective, e)
        telethon_proxy = None

# 下载并发控制（避免 Telethon 同时打开过多连接导致卡住/超时）
MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
if runtime_settings.max_concurrent_downloads is not None:
    MAX_CONCURRENT_DOWNLOADS = int(runtime_settings.max_concurrent_downloads)
concurrency_limiter = ConcurrencyLimiter(MAX_CONCURRENT_DOWNLOADS)

# 下载“卡住”判定：超过该秒数无任何进度更新则中止该任务并标记失败
DOWNLOAD_STALL_TIMEOUT_S = int(os.getenv("DOWNLOAD_STALL_TIMEOUT_S", "180"))

# 确保所有目录存在
for path in [MUSIC_PATH, VIDEO_PATH, DOWNLOAD_PATH, CACHE_PATH]:
    os.makedirs(path, exist_ok=True)

# 初始化客户端
client = TelegramClient(
    os.path.join(CACHE_PATH, "bot_session"), API_ID, API_HASH, proxy=telethon_proxy
).start(bot_token=BOT_TOKEN)


def sanitize_filename(filename: str, is_video: bool = False) -> tuple:
    """清理文件名,移除特殊字符和广告,返回(清理后的文件名, 是否被截断, 原始关键信息)"""
    # 移除扩展名
    name, ext = os.path.splitext(filename)
    original_name = name  # 保存原始名称用于提示
    was_truncated = False

    # 常见广告关键词
    ad_patterns = [
        r"@\w+",
        r"www\.[\w\.]+",
        r"http[s]?://\S+",
        r"[\u4e00-\u9fa5]*广告[\u4e00-\u9fa5]*",
        r"[\u4e00-\u9fa5]*推广[\u4e00-\u9fa5]*",
        r"[\u4e00-\u9fa5]*官网[\u4e00-\u9fa5]*",
        r"\[.*?\]",
        r"\(.*?\)",
        r"VIP",
        r"高清",
        r"超清",
        r"蓝光",
        r"HD",
        r"4K",
        r"1080[pP]",
        r"720[pP]",
    ]

    for pattern in ad_patterns:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)

    # 移除类似 “_1756486628200” 这种尾随时间戳/数字后缀（常见于转存/重命名）
    # 仅移除尾部连续 8 位以上的数字，避免误伤正常标题里的数字
    name = re.sub(r"([_-])\d{8,}$", "", name)

    # 移除特殊字符,只保留字母数字中文、基本符号和点号
    # 修改：允许点号 (.) 存在，以便保留 G.E.M. 等名称中的点
    name = re.sub(r"[^\w\u4e00-\u9fa5\-_\s\.]", "", name)

    # 移除多余空格
    name = re.sub(r"\s+", " ", name).strip()

    # 提取关键词信息
    key_info = ""

    # 超长文件名处理（超过50个字符认为是超长）
    if len(name) > 50:
        was_truncated = True
        # 提取关键词
        words = name.split()

        if is_video:
            # 视频文件：尝试提取年份、季数、集数等关键信息
            year_match = re.search(r"(19|20)\d{2}", name)
            season_match = re.search(r"[Ss](\d{1,2})", name)
            episode_match = re.search(r"[Ee](\d{1,3})", name)

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

            name = " ".join(key_parts)[:40]  # 视频文件名限制在40字符
            key_info = f"提取关键信息: {name}"

        else:
            # 其他文件：取前面重要词汇
            if len(words) >= 5:
                name = " ".join(words[:5])[:40]
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


def format_filename_by_type(
    filename: str,
    file_type: str,
    attributes,
    *,
    message=None,
    caption_text: str = "",
) -> tuple:
    """根据文件类型格式化文件名，返回(文件名, 是否被截断, 提示信息)。

    说明：
    - 许多音乐机器人会把真实歌名写在 caption 文案里，而文件属性只给 music.mp3。
    - 因此音频命名策略：metadata(title/performer) > caption("歌曲：...") > 稳定兜底(audio_{id}).
    """

    def _stable_suffix(msg) -> str:
        try:
            doc = getattr(getattr(msg, "media", None), "document", None)
            doc_id = getattr(doc, "id", None)
            if doc_id is not None:
                return f"{int(doc_id) & 0xffffffff:08x}"
        except Exception:
            pass
        try:
            mid = getattr(msg, "id", None)
            if mid is not None:
                return f"m{int(mid)}"
        except Exception:
            pass
        return str(int(time.time()))

    def _extract_audio_title(text: str) -> str:
        if not text:
            return ""
        import re

        lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]
        patterns = [
            re.compile(r"^(歌曲|歌名|曲名|曲目)\s*[:：]\s*(.+)$"),
            re.compile(r"^(Song|Title)\s*[:：]\s*(.+)$", re.IGNORECASE),
        ]
        for ln in lines:
            for p in patterns:
                m = p.match(ln)
                if m:
                    return (m.group(2) or "").strip()

        # 兜底：第一行像“xxx - yyy”，且不包含明显非标题字段
        if lines:
            first = lines[0]
            bad = [
                "专辑",
                "大小",
                "音乐ID",
                "via",
                "kbps",
                "MB",
                "#网易云音乐",
                "网易云音乐",
            ]
            if " - " in first and not any(b in first for b in bad):
                return first.strip()
        return ""

    def _extract_audio_ext(text: str) -> str:
        if not text:
            return ""
        import re

        m = re.search(r"#\s*(flac|mp3|m4a|wav|ogg|aac|alac|ape)\b", text, re.IGNORECASE)
        if m:
            return "." + m.group(1).lower()
        return ""

    def _guess_ext_from_mime(msg) -> str:
        mt = ""
        try:
            mt = (
                getattr(
                    getattr(getattr(msg, "media", None), "document", None),
                    "mime_type",
                    "",
                )
                or ""
            ).lower()
        except Exception:
            mt = ""
        mapping = {
            "audio/flac": ".flac",
            "audio/x-flac": ".flac",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/aac": ".aac",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/x-ape": ".ape",
            "audio/ape": ".ape",
            "audio/alac": ".m4a",
        }
        return mapping.get(mt, "")

    def _is_generic_audio_name(fn: str) -> bool:
        base = os.path.basename(fn or "").strip().lower()
        return base in {
            "music.mp3",
            "music.flac",
            "music.m4a",
            "audio.mp3",
            "audio.flac",
            "audio.m4a",
            "file.mp3",
            "file.flac",
            "file.m4a",
            "unknown.mp3",
            "unknown.flac",
            "unknown.m4a",
        }

    if file_type != "audio":
        if file_type == "video":
            return sanitize_filename(filename, is_video=True)
        return sanitize_filename(filename)

    # 1) 从 DocumentAttributeAudio 读取 metadata
    meta_title = meta_perf = ""
    for attr in attributes:
        if isinstance(attr, DocumentAttributeAudio) and not getattr(
            attr, "voice", False
        ):
            meta_title = (attr.title or "").strip()
            meta_perf = (attr.performer or "").strip()
            if meta_title or meta_perf:
                break

    # 2) caption 文案（优先用调用方传入；否则从 message.message 取）
    cap = (caption_text or "").strip()
    if not cap and message is not None:
        try:
            cap = (getattr(message, "message", "") or "").strip()
        except Exception:
            cap = ""

    cap_title = _extract_audio_title(cap)

    # 3) 扩展名：caption tag > 原名 ext > mime > 默认.mp3
    ext = _extract_audio_ext(cap)
    if not ext:
        ext = os.path.splitext(filename)[1]
    if not ext and message is not None:
        ext = _guess_ext_from_mime(message)
    if not ext:
        ext = ".mp3"

    # 4) 组装 base name：metadata > caption_title > 兜底
    if meta_title or meta_perf:
        base = (
            f"{meta_title}-{meta_perf}"
            if (meta_title and meta_perf)
            else (meta_title or meta_perf)
        )
        return sanitize_filename(f"{base}{ext}")

    if cap_title:
        # 若原文件名是占位名（music.mp3），以 caption 标题为准
        return sanitize_filename(f"{cap_title}{ext}")

    # 兜底：若是泛化名，改为 audio_{suffix}
    if _is_generic_audio_name(filename) or not filename:
        suf = _stable_suffix(message) if message is not None else str(int(time.time()))
        return sanitize_filename(f"audio_{suf}{ext}")

    # 最后：保留原文件名（并清理）
    return sanitize_filename(filename)


def get_file_type(message, filename: str = "", caption_text: str = "") -> tuple:
    """判断文件类型。

    音频类型判定策略：
    - mime_type 是 audio/*
    - 或存在 DocumentAttributeAudio(非 voice)
    - 或文件扩展名为常见音频格式
    - 或 caption 中包含 #flac/#mp3/... 这类格式标签
    """
    if not message.media or not hasattr(message.media, "document"):
        return "other", DOWNLOAD_PATH

    document = message.media.document
    mime_type = document.mime_type or ""

    # 检查音频
    audio_exts = {".flac", ".mp3", ".m4a", ".wav", ".ogg", ".aac", ".alac", ".ape"}
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    cap = (caption_text or "").lower()
    cap_has_audio_tag = any(
        tag in cap
        for tag in ["#flac", "#mp3", "#m4a", "#wav", "#ogg", "#aac", "#alac", "#ape"]
    )

    if (
        mime_type.startswith("audio/")
        or any(
            isinstance(attr, DocumentAttributeAudio)
            and not getattr(attr, "voice", False)
            for attr in document.attributes
        )
        or (ext in audio_exts)
        or cap_has_audio_tag
    ):
        return "audio", MUSIC_PATH

    # 检查视频
    if mime_type.startswith("video/") or any(
        isinstance(attr, DocumentAttributeVideo) for attr in document.attributes
    ):
        return "video", VIDEO_PATH

    return "other", DOWNLOAD_PATH


def get_filename(message) -> str:
    """获取文件名"""
    if hasattr(message.media, "document"):
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
    if info and info.get("message"):
        return info["message"]

    create_lock = dashboard_create_locks.setdefault(chat_id, asyncio.Lock())
    async with create_lock:
        info = chat_dashboards.get(chat_id)
        if info and info.get("message"):
            return info["message"]

        msg = await client.send_message(
            chat_id,
            "📥 下载任务面板\n\n暂无任务",
            buttons=[[Button.inline("🔄 刷新", "dash_refresh")]],
        )
        chat_dashboards[chat_id] = {
            "message": msg,
            "lock": asyncio.Lock(),
            "last_edit_ts": 0.0,
            "last_text": "",
            "last_buttons_sig": "",
        }
        return msg


def _render_dashboard(chat_id: int) -> str:
    items = [v for v in active_downloads.values() if v.get("chat_id") == chat_id]
    items.sort(key=lambda x: x.get("created_ts", 0))

    lines: List[str] = []
    lines.append("📥 下载任务面板")
    lines.append("")

    if not items:
        lines.append("暂无正在下载的任务。")
    else:
        for idx, it in enumerate(items, start=1):
            state = it.get("state", "downloading")
            name = _short_name(
                it.get("display_name") or os.path.basename(it.get("final_path", "file"))
            )
            total = it.get("file_size", 0) or 0
            done = it.get("downloaded", 0) or 0
            percent = (done / total * 100) if total > 0 else 0.0
            speed = it.get("speed_str", "-")
            eta = it.get("eta_str", "-")

            if state == "paused":
                state_str = "⏸ 已暂停"
            elif state == "cancelling":
                state_str = "🧹 正在取消"
            elif state == "cancelled":
                state_str = "❌ 已取消"
            elif state == "failed":
                state_str = "⚠️ 失败"
            elif state == "completed":
                state_str = "✅ 完成"
            elif state == "queued":
                state_str = "⏳ 排队中"
            else:
                state_str = "📥 下载中"

            bar = "█" * int(percent / 10) + "░" * (10 - int(percent / 10))
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
                parts.append(
                    f"{b.text}:{b.data.decode('utf-8') if hasattr(b, 'data') else ''}"
                )
            except Exception:
                parts.append(str(b))
    return "|".join(parts)


def _build_dashboard_buttons(chat_id: int):
    items = [v for v in active_downloads.values() if v.get("chat_id") == chat_id]
    items.sort(key=lambda x: x.get("created_ts", 0))

    buttons = []
    # 每个任务一行：暂停/继续 + 取消
    for idx, it in enumerate(items, start=1):
        download_id = it["id"]
        paused = it.get("paused", False)
        state = it.get("state")

        # 已取消/已完成/失败的不再显示控制按钮
        if state in {"completed", "cancelled", "failed"}:
            continue

        pause_text = f"⏸ {idx}" if not paused else f"▶️ {idx}"
        cancel_text = f"❌ {idx}"
        buttons.append(
            [
                Button.inline(pause_text, f"pause_{download_id}"),
                Button.inline(cancel_text, f"cancel_{download_id}"),
            ]
        )

    # 面板操作
    buttons.append([Button.inline("🔄 刷新", "dash_refresh")])
    return buttons


async def update_dashboard(chat_id: int, force: bool = False):
    info = chat_dashboards.get(chat_id)
    if not info:
        await ensure_dashboard(chat_id)
        info = chat_dashboards.get(chat_id)

    async with info["lock"]:
        now = time.time()
        # 限流：默认 1.5 秒最多编辑一次（force 仅跳过限流，不跳过内容一致检查）
        if (not force) and now - info.get("last_edit_ts", 0) < 1.5:
            return

        text = _render_dashboard(chat_id)
        buttons = _build_dashboard_buttons(chat_id)
        btn_sig = _buttons_signature(buttons)

        # 避免重复内容编辑（无论是否 force，只要内容没变就不发 edit）
        if text == info.get("last_text") and btn_sig == info.get("last_buttons_sig"):
            # 记一次“最近渲染”时间，避免调用方频繁触发
            info["last_edit_ts"] = now
            return

        def _schedule_retry(delay_s: float):
            # 避免重复排队（失败后做一次延迟重试即可；用户也可手动点“刷新”）
            t = info.get("retry_task")
            if t and not t.done():
                return

            async def _retry():
                try:
                    await asyncio.sleep(delay_s)
                    await update_dashboard(chat_id, force=True)
                except Exception:
                    # 兜底：重试失败不再递归排队，避免无限循环
                    return

            info["retry_task"] = asyncio.create_task(_retry())

        try:
            await info["message"].edit(text, buttons=buttons)
            info["last_edit_ts"] = now
            info["last_text"] = text
            info["last_buttons_sig"] = btn_sig
        except MessageNotModifiedError:
            # 理论上不应再触发（上面已做内容一致检查），但为保险起见做降噪处理
            info["last_edit_ts"] = now
            info["last_text"] = text
            info["last_buttons_sig"] = btn_sig
        except FloodWaitError as e:
            # Telegram 限流：等待指定秒数后自动重试一次
            delay = int(getattr(e, "seconds", 1) or 1) + 1
            logger.warning(f"更新任务面板受限(FloodWait {delay}s)，将自动重试")
            _schedule_retry(delay)
        except RPCError as e:
            # RPC 类错误：短延迟重试一次，避免“完成后卡住”
            logger.warning(f"更新任务面板 RPC 失败: {e}，将自动重试")
            _schedule_retry(2.0)
        except Exception as e:
            logger.warning(f"更新任务面板失败: {e}，将自动重试")
            _schedule_retry(2.0)


async def _dashboard_cleanup_refresh(chat_id: int, is_cleanup: bool) -> None:
    """任务面板的延迟清理回调（由 task_manager 触发）。

    仅在 is_cleanup=True 时执行：
    - 清空“最近状态”历史；
    - 移除该 chat 中仍残留的终态任务（完成/取消/失败）；
    - 强制刷新面板，使其回到“空闲/暂无任务”状态。
    """

    if not is_cleanup:
        return

    # 清空历史
    download_history.pop(chat_id, None)

    # 移除残留的终态任务（理论上这时已无活动任务，但为保险起见按 state 过滤）
    to_del = [
        did
        for did, it in active_downloads.items()
        if it.get("chat_id") == chat_id
        and it.get("state") in {"completed", "cancelled", "failed"}
    ]
    for did in to_del:
        active_downloads.pop(did, None)

    # 刷新面板
    await update_dashboard(chat_id, force=True)


# 绑定 UI 刷新回调：实现“空闲 5 秒后自动清理面板”的逻辑
task_manager.refresh_ui = _dashboard_cleanup_refresh


def _push_history(chat_id: int, name: str, status: str, note: str = ""):
    lst = download_history.setdefault(chat_id, [])
    lst.append({"name": name, "status": status, "note": note, "ts": time.time()})
    # 控制大小
    if len(lst) > 30:
        del lst[:-30]


async def _remove_download_after(download_id: int, delay: float = 3.0):
    # 兼容旧调用（未传 chat_id 时无法刷新面板）
    await asyncio.sleep(delay)
    active_downloads.pop(download_id, None)


async def _remove_download_after_and_refresh(download_id: int, chat_id: int, delay: float = 3.0):
    """延迟移除终态任务，并刷新面板。

    目的：
    - 让“✅ 完成/❌ 取消/⚠️ 失败”的行在面板中保留短暂时间（默认 5 秒）。
    - 移除后主动刷新一次，避免面板长期停留在“完成项仍显示”的状态。
    """
    await asyncio.sleep(delay)
    active_downloads.pop(download_id, None)
    try:
        await update_dashboard(chat_id, force=True)
    except Exception:
        return


async def _final_dashboard_refresh(chat_id: int, delay: float = 2.0):
    """任务进入终态后再兜底刷新一次。

    目的：最后一次 EditMessage 可能因网络/RPC/FloodWait 等原因失败。
    下载任务结束后不会再有 progress callback 触发刷新，因此这里补一刀。
    """
    try:
        await asyncio.sleep(delay)
        await update_dashboard(chat_id, force=True)
    except Exception:
        return


async def download_with_progress(download_id: int):
    """下载任务执行体：更新 active_downloads 状态，并驱动统一任务面板刷新。"""
    info = active_downloads.get(download_id)
    if not info:
        return

    message = info["message"]
    chat_id = info["chat_id"]
    final_path = info["final_path"]
    temp_path = info["temp_path"]

    file_size = int(info.get("file_size", 0) or 0)
    resume_from = int(info.get("resume_from", 0) or 0)

    # 用于速度/ETA 计算
    last_update_ts = 0.0
    last_bytes = resume_from
    last_ts = time.time()

    # 用于“卡住”检测（跨 DC / 网络不可达等场景常见）
    last_progress_mono = time.monotonic()
    last_progress_bytes = resume_from

    async def progress_callback(current, total):
        nonlocal last_update_ts, last_bytes, last_ts, last_progress_mono, last_progress_bytes

        # current 为本次 session 的已下载量；加上 resume_from 才是总计
        downloaded = int(current) + resume_from
        info["downloaded"] = downloaded

        # 记录最近进度（用于 watchdog 判定是否“卡住”）
        last_progress_mono = time.monotonic()
        last_progress_bytes = downloaded

        # 暂停控制：在 callback 内阻塞最安全（Telethon 会持续调用）
        while info.get("paused", False):
            info["state"] = "paused"
            await update_dashboard(chat_id)
            await asyncio.sleep(0.5)

        info["state"] = "downloading"

        # 速度/ETA
        now = time.time()
        dt = max(now - last_ts, 1e-6)
        db = downloaded - last_bytes
        speed_bps = db / dt
        last_bytes = downloaded
        last_ts = now

        if speed_bps <= 0:
            info["speed_str"] = "-"
            info["eta_str"] = "-"
        else:
            speed_mb = speed_bps / (1024 * 1024)
            info["speed_str"] = (
                f"{speed_mb:.2f} MB/s"
                if speed_mb >= 1
                else f"{(speed_bps/1024):.1f} KB/s"
            )
            remaining = max(file_size - downloaded, 0)
            eta = remaining / speed_bps
            if eta < 60:
                info["eta_str"] = f"{int(eta)}秒"
            elif eta < 3600:
                info["eta_str"] = f"{int(eta/60)}分{int(eta%60)}秒"
            else:
                h = int(eta / 3600)
                m = int((eta % 3600) / 60)
                info["eta_str"] = f"{h}时{m}分"

        # 限流刷新
        if now - last_update_ts > 1.5:
            last_update_ts = now
            await update_dashboard(chat_id)

    async def _stall_watchdog(download_task: asyncio.Task):
        """如果长时间无任何进度更新，则中止该任务。

        典型触发原因：文件位于其他 DC，目标 DC 网络不可达/被墙/路由异常；
        或并发过高导致 Telethon 连接建立/握手卡住。
        """
        try:
            while not download_task.done():
                await asyncio.sleep(5)
                # 暂停时不判定卡住
                if info.get("state") != "downloading":
                    continue

                idle_s = time.monotonic() - last_progress_mono
                if idle_s >= DOWNLOAD_STALL_TIMEOUT_S and info.get("downloaded", 0) == last_progress_bytes:
                    info["cancel_reason"] = "stalled"
                    logger.error(
                        "下载卡住超时，已中止任务。download_id=%s chat_id=%s idle_s=%s downloaded=%s/%s",
                        download_id,
                        chat_id,
                        int(idle_s),
                        info.get("downloaded", 0),
                        file_size,
                    )
                    download_task.cancel()
                    return
        except asyncio.CancelledError:
            return

    async def _download_body():
        """实际下载过程（可能被 watchdog 取消）。"""
        info["state"] = "downloading"
        await update_dashboard(chat_id, force=True)

        # 记录文件所在 DC（便于排障：跨 DC 时更容易暴露网络问题）
        try:
            doc = getattr(getattr(message, "media", None), "document", None)
            dc_id = getattr(doc, "dc_id", None)
            if dc_id is not None:
                info["dc_id"] = dc_id
                logger.info("下载目标 DC：chat_id=%s download_id=%s dc_id=%s", chat_id, download_id, dc_id)
        except Exception:
            pass

        mode = "ab" if resume_from > 0 else "wb"
        with open(temp_path, mode) as f:
            if resume_from > 0:
                async for chunk in client.iter_download(message.media, offset=resume_from):
                    f.write(chunk)
                    await progress_callback(f.tell() - resume_from, file_size - resume_from)
            else:
                await client.download_media(message.media, file=f, progress_callback=progress_callback)

        os.rename(temp_path, final_path)

    finished_chat_id: Optional[int] = chat_id
    did_finish = False

    download_task: Optional[asyncio.Task] = None
    watchdog_task: Optional[asyncio.Task] = None

    try:
        # 控制并发：大量并发时“跨 DC 下载”更容易出现连接卡住
        async with concurrency_limiter:
            download_task = asyncio.create_task(_download_body())
            watchdog_task = asyncio.create_task(_stall_watchdog(download_task))
            await download_task
        info["state"] = "completed"
        info["downloaded"] = file_size
        _push_history(chat_id, info["display_name"], "✅ 完成")
        # 完成后做两次刷新：一次立即，一次稍后兜底，避免最后一次 edit 失败导致“卡住”
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_final_dashboard_refresh(chat_id, delay=2.0))
        asyncio.create_task(_remove_download_after_and_refresh(download_id, chat_id, delay=5.0))
        did_finish = True

    except asyncio.CancelledError:
        # task.cancel()：可能来自用户取消，也可能来自 watchdog 的“卡住超时”中止
        if info.get("cancel_reason") == "stalled":
            info["state"] = "failed"
            _push_history(
                chat_id,
                info["display_name"],
                "⚠️ 失败",
                note="(Stalled/跨DC连接超时)",
            )
        else:
            info["state"] = "cancelled"
            _push_history(chat_id, info["display_name"], "❌ 已取消")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_final_dashboard_refresh(chat_id, delay=2.0))
        asyncio.create_task(_remove_download_after_and_refresh(download_id, chat_id, delay=5.0))
        did_finish = True

    except Exception as e:
        logger.error(f"下载失败: {e}")
        info["state"] = "failed"
        _push_history(
            chat_id, info["display_name"], "⚠️ 失败", note=f"({type(e).__name__})"
        )
        await update_dashboard(chat_id, force=True)
        asyncio.create_task(_final_dashboard_refresh(chat_id, delay=2.0))
        asyncio.create_task(_remove_download_after_and_refresh(download_id, chat_id, delay=8.0))
        did_finish = True

    finally:
        # 结束 watchdog
        if watchdog_task and not watchdog_task.done():
            try:
                watchdog_task.cancel()
            except Exception:
                pass

        # 统一做任务计数 decrement：确保即使刷新异常也不会导致“永远不清理”。
        if did_finish and finished_chat_id is not None:
            try:
                await task_manager.task_finished(finished_chat_id)
            except Exception:
                pass


def _caption_looks_like_music(text: str) -> bool:
    """判断一段文本是否像音乐机器人生成的“歌曲信息”文案。"""
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    # 典型关键字段：歌曲/专辑/音乐ID/码率/平台标签
    markers = [
        "歌曲",
        "歌名",
        "曲名",
        "专辑",
        "音乐id",
        "网易云音乐",
        "kbps",
        "via @music_v1bot",
        "#flac",
        "#mp3",
        "#m4a",
        "#wav",
        "#ogg",
        "#aac",
        "#alac",
        "#ape",
    ]
    tl = t.lower()
    hit = 0
    for m in markers:
        if m.lower() in tl:
            hit += 1
    # 命中 2 个以上字段通常就非常可靠
    return hit >= 2


async def get_effective_caption_text(
    message, chat_id: int, *, max_lookback: int = 6, max_seconds: int = 15
) -> str:
    """为“命名/类型识别”获取最可信的 caption 文案。

    处理场景：
    - 文件消息自身带 caption（最常见）
    - 文件消息没有 caption，但上一条消息/被回复消息是音乐文案
    """
    # 1) 自身 caption
    try:
        cap = (getattr(message, "message", "") or "").strip()
        if cap:
            return cap
    except Exception:
        pass

    # 2) reply_to 指向的消息
    try:
        rmid = getattr(message, "reply_to_msg_id", None)
        if rmid:
            ref = await client.get_messages(chat_id, ids=rmid)
            txt = (getattr(ref, "message", "") or "").strip() if ref else ""
            if _caption_looks_like_music(txt):
                return txt
    except Exception:
        pass

    # 3) 回看同一发送者的上一条（或几条）纯文本消息
    try:
        offset_id = getattr(message, "id", None)
        sender_id = getattr(message, "sender_id", None)
        cur_date = getattr(message, "date", None)
        if offset_id is None:
            return ""

        prev_msgs = await client.get_messages(
            chat_id, limit=max_lookback, offset_id=offset_id
        )
        if not prev_msgs:
            return ""

        for m in prev_msgs:
            try:
                if sender_id is not None and getattr(m, "sender_id", None) != sender_id:
                    continue
                # 只用纯文本消息
                if getattr(m, "media", None) is not None:
                    continue
                txt = (getattr(m, "message", "") or "").strip()
                if not txt:
                    continue
                if cur_date and getattr(m, "date", None):
                    dt = (cur_date - m.date).total_seconds()
                    if dt < 0 or dt > max_seconds:
                        continue
                if _caption_looks_like_music(txt):
                    return txt
            except Exception:
                continue
    except Exception:
        pass

    return ""


@client.on(events.NewMessage)
async def handle_file(event):
    """处理接收到的文件"""
    message = event.message

    # 检查是否是文件
    if not message.media or not hasattr(message.media, "document"):
        return

    # 获取原始文件名
    original_filename = get_filename(message)

    # 获取用于命名/类型判断的 caption（必要时从上一条/被回复消息回溯）
    caption_text = await get_effective_caption_text(message, event.chat_id)

    # 获取文件类型和目标路径（音频类型判定也会参考扩展名与 caption 标签）
    file_type, target_path = get_file_type(message, original_filename, caption_text)

    # 格式化文件名（音频：metadata > caption("歌曲：...") > 稳定兜底）
    formatted_filename, was_truncated, key_info = format_filename_by_type(
        original_filename,
        file_type,
        message.media.document.attributes,
        message=message,
        caption_text=caption_text,
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
                [Button.inline("❌ 取消", f"cancel_dup_{id(message)}")],
            ],
        )

        # 临时保存重复处理所需信息
        pending_duplicates[id(message)] = {
            "message": message,
            "file_type": file_type,
            "target_path": target_path,
            "filename": formatted_filename,
            "chat_id": event.chat_id,
        }
        return

    # 没有重复,直接下载
    await start_download(
        message,
        event.chat_id,
        file_type,
        target_path,
        formatted_filename,
        truncate_notice,
    )


async def start_download(
    message, chat_id, file_type, target_path, filename, truncate_notice: str = ""
):
    """开始下载：创建任务并把多个任务统一展示到同一个面板消息。"""

    # =========== 修改开始: 删除旧面板 ===========
    # 目的：每次有新任务加入时，尝试删除旧的面板消息，以便发送一个新的在最底部
    old_info = chat_dashboards.get(chat_id)
    if old_info and old_info.get("message"):
        try:
            # 删除旧消息
            await old_info["message"].delete()
        except Exception:
            # 即使删除失败（例如已被用户手动删除）也不影响后续流程
            pass
        # 清除内存中的记录，强制 ensure_dashboard 重新发送新消息
        chat_dashboards.pop(chat_id, None)
    # =========== 修改结束 ===========

    # 任务计数 + 取消可能存在的“空闲延迟清理”
    # 注意：只调用一次，避免计数翻倍导致“永不清理”等异常。
    await task_manager.task_started(chat_id)

    await ensure_dashboard(chat_id)

    filepath = os.path.join(target_path, filename)
    temp_filepath = filepath + ".downloading"

    # 断点续传
    resume_from = 0
    if os.path.exists(temp_filepath):
        resume_from = os.path.getsize(temp_filepath)
        logger.info(f"恢复下载从 {resume_from} 字节: {filename}")

    download_id = id(message)
    file_size = int(message.file.size or 0)

    type_emoji = (
        "🎵" if file_type == "audio" else "🎬" if file_type == "video" else "📄"
    )

    active_downloads[download_id] = {
        "id": download_id,
        "message": message,
        "chat_id": chat_id,
        "file_type": file_type,
        "type_emoji": type_emoji,
        "display_name": filename,
        "target_path": target_path,
        "final_path": filepath,
        "temp_path": temp_filepath,
        "file_size": file_size,
        "resume_from": resume_from,
        "downloaded": resume_from,
        "speed_str": "-",
        "eta_str": "-",
        "paused": False,
        "state": "queued",
        "created_ts": time.time(),
        "truncate_notice": truncate_notice,
        "cancel_requested_ts": None,
        "task": None,
    }

    # 推送一条“准备”历史（保持轻量，不刷屏）
    _push_history(chat_id, filename, f"{type_emoji} 已加入队列")

    # 创建下载任务（关键：支持并发、多任务统一面板）
    task = asyncio.create_task(download_with_progress(download_id))
    active_downloads[download_id]["task"] = task

    await update_dashboard(chat_id, force=True)


@client.on(events.CallbackQuery)
async def handle_callback(event):
    """处理按钮回调"""
    data = event.data.decode("utf-8")

    # 面板刷新
    if data == "dash_refresh":
        await event.answer("已刷新", alert=False)
        await update_dashboard(event.chat_id, force=True)
        return

    if data.startswith("overwrite_"):
        msg_id = int(data.split("_")[1])
        if msg_id in pending_duplicates:
            info = pending_duplicates.pop(msg_id)
            await event.edit("♻️ 开始覆盖下载...")
            await start_download(
                info["message"],
                info["chat_id"],
                info["file_type"],
                info["target_path"],
                info["filename"],
                "",  # 覆盖时不显示截断提示
            )
        else:
            await event.answer("该任务已处理或已过期", alert=False)

    elif data.startswith("rename_"):
        msg_id = int(data.split("_")[1])
        if msg_id in pending_duplicates:
            info = pending_duplicates.pop(msg_id)
            new_filename = get_next_filename(info["target_path"], info["filename"])
            await event.edit(f"➕ 使用新文件名: {new_filename}")
            await start_download(
                info["message"],
                info["chat_id"],
                info["file_type"],
                info["target_path"],
                new_filename,
                "",  # 重命名时不显示截断提示
            )
        else:
            await event.answer("该任务已处理或已过期", alert=False)

    elif data.startswith("cancel_dup_"):
        msg_id = int(data.split("_")[2])
        pending_duplicates.pop(msg_id, None)
        await event.edit("❌ 已取消下载")

    elif data.startswith("pause_"):
        download_id = int(data.split("_")[1])
        if download_id in active_downloads:
            it = active_downloads[download_id]
            it["paused"] = not it.get("paused", False)
            it["state"] = "paused" if it["paused"] else "downloading"
            status = "⏸ 已暂停" if it["paused"] else "▶️ 继续下载"
            _push_history(it["chat_id"], it["display_name"], status)
            await event.answer(status, alert=False)
            await update_dashboard(it["chat_id"], force=True)
        else:
            await event.answer("任务不存在或已结束", alert=False)

    elif data.startswith("cancel_"):
        download_id = int(data.split("_")[1])
        if download_id in active_downloads:
            it = active_downloads[download_id]
            it["state"] = "cancelling"
            it["cancel_requested_ts"] = time.time()

            # 关键：直接取消 asyncio Task，避免“正在取消”卡住
            task = it.get("task")
            if task and not task.done():
                task.cancel()

            _push_history(it["chat_id"], it["display_name"], "🧹 取消中")
            await event.answer("已请求取消", alert=False)
            await update_dashboard(it["chat_id"], force=True)
        else:
            await event.answer("任务不存在或已结束", alert=False)


@client.on(events.NewMessage(pattern="/start"))
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


def _is_admin_event(event) -> bool:
    """Admin gate for management commands.

    - If ADMIN_USER_IDS is configured: only allow those users.
    - Otherwise: only allow in private chats (avoid anyone in groups changing settings).
    """
    try:
        if ADMIN_USER_IDS:
            return int(getattr(event, "sender_id", 0) or 0) in ADMIN_USER_IDS
        return bool(getattr(event, "is_private", False))
    except Exception:
        return False


# ===== 管理命令：日志与状态 =====
_log_follow_sessions: Dict[tuple[int, int], asyncio.Task] = {}
_status_watch_sessions: Dict[tuple[int, int], asyncio.Task] = {}


def _parse_duration_seconds(token: str) -> Optional[int]:
    """Parse duration token into seconds.

    Supported forms:
      - 120        (seconds)
      - 30s
      - 10m
      - 2h
      - 1d

    Returns:
      - int seconds on success
      - None on parse failure
    """
    t = (token or "").strip().lower()
    if not t:
        return None

    if t.isdigit():
        try:
            return max(1, int(t))
        except Exception:
            return None

    unit = t[-1]
    num = t[:-1]
    if not num or not num.isdigit():
        return None

    try:
        n = int(num)
        if n <= 0:
            return None
    except Exception:
        return None

    mul = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }.get(unit)
    if mul is None:
        return None

    return n * mul


def _tail_lines(path: str, n: int) -> str:
    """Return the last N lines of a UTF-8 text file."""
    try:
        n = max(1, min(int(n), 300))
    except Exception:
        n = 80

    try:
        dq: deque[str] = deque(maxlen=n)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                dq.append(line.rstrip("\n"))
        return "\n".join(dq)
    except FileNotFoundError:
        return "(日志文件不存在)"
    except Exception as e:
        return f"(读取日志失败：{type(e).__name__}: {e})"


def _clip_telegram(text: str, limit: int = 3800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return "…\n" + text[-limit:]


def _code_block(text: str) -> str:
    return "```\n" + (text or "") + "\n```"


async def _stop_session(sessions: Dict[tuple[int, int], asyncio.Task], key: tuple[int, int]) -> bool:
    t = sessions.pop(key, None)
    if t and not t.done():
        t.cancel()
        return True
    return False


@client.on(events.NewMessage(pattern=r"^/(log|logs)(?:\s+.*)?$"))
async def log_command(event):
    """查看容器内日志（中文输出）并支持短时跟随。

    用法：
      /log               查看最后 80 行
      /log 200           查看最后 200 行（上限 300）
      /log follow        跟随日志（每 2 秒刷新，默认持续直到手动 stop）
      /log follow 10m    跟随日志 10 分钟
      /log follow forever 跟随日志直到手动 stop
      /log stop          停止跟随
    """
    if not _is_admin_event(event):
        await event.respond("❌ 无权限：请在私聊中使用该命令，或设置 ADMIN_USER_IDS")
        return

    chat_id = int(getattr(event, "chat_id", 0) or 0)
    user_id = int(getattr(event, "sender_id", 0) or 0)
    key = (chat_id, user_id)

    text = (event.raw_text or "").strip()
    tokens = text.split()
    args = [a.strip() for a in tokens[1:]]
    sub = (args[0].lower() if args else "")

    if sub in {"stop", "end", "off"}:
        stopped = await _stop_session(_log_follow_sessions, key)
        await event.respond("✅ 已停止日志跟随" if stopped else "当前没有运行中的日志跟随")
        return

    if sub in {"follow", "f"}:
        # Ensure only one session per user per chat.
        await _stop_session(_log_follow_sessions, key)

        duration_s: Optional[int] = None  # None => forever
        if len(args) >= 2:
            dur_token = (args[1] or "").strip().lower()
            if dur_token in {"forever", "infinite", "inf", "always"}:
                duration_s = None
            else:
                duration_s = _parse_duration_seconds(dur_token)
                if duration_s is None:
                    await event.respond(
                        "❌ 无法识别的时长参数。示例：/log follow 10m 或 /log follow 120s 或 /log follow forever"
                    )
                    return

        if duration_s is None:
            duration_desc = "直到手动 stop"
        else:
            if duration_s % 3600 == 0:
                duration_desc = f"{duration_s // 3600} 小时"
            elif duration_s % 60 == 0:
                duration_desc = f"{duration_s // 60} 分钟"
            else:
                duration_desc = f"{duration_s} 秒"

        head = (
            f"📄 TeleFlux 实时日志（{Path(LOG_FILE).name}）\n"
            f"刷新：每 2 秒，持续：{duration_desc}\n\n"
        )
        init = _tail_lines(LOG_FILE, 80)
        msg = await event.respond(head + _code_block(_clip_telegram(init)))

        end_at: Optional[float] = None
        if duration_s is not None:
            end_at = asyncio.get_running_loop().time() + float(duration_s)

        async def _runner():
            try:
                while True:
                    await asyncio.sleep(2)
                    if end_at is not None and asyncio.get_running_loop().time() >= end_at:
                        break
                    content = _tail_lines(LOG_FILE, 80)
                    body = head + _code_block(_clip_telegram(content))
                    try:
                        await msg.edit(body)
                    except MessageNotModifiedError:
                        pass
                    except Exception:
                        # Ignore edit failures; continue.
                        pass
            except asyncio.CancelledError:
                return
            finally:
                # Best-effort cleanup of session registry.
                cur = asyncio.current_task()
                if cur is not None:
                    existing = _log_follow_sessions.get(key)
                    if existing is cur:
                        _log_follow_sessions.pop(key, None)

                # If finite duration, optionally tell the user it ended.
                if end_at is not None:
                    try:
                        await event.respond("⏹ 日志跟随已结束（已到时限）。可用 /log follow 继续，或 /log 查看尾部。")
                    except Exception:
                        pass

        _log_follow_sessions[key] = asyncio.create_task(_runner())
        return

    # Tail mode
    n = 80
    if sub.isdigit():
        n = int(sub)

    content = _tail_lines(LOG_FILE, n)
    await event.respond(
        f"📄 TeleFlux 日志（最后 {min(max(1, n), 300)} 行）\n\n" + _code_block(_clip_telegram(content))
    )


def _summarize_task_states() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for it in active_downloads.values():
        st = str(it.get("state") or "unknown")
        counts[st] = counts.get(st, 0) + 1
    return counts


async def _build_status_text(chat_id: int) -> str:
    snap = await task_manager.snapshot()
    active_map = snap.get("active", {}) or {}
    total_active = 0
    for v in active_map.values():
        try:
            total_active += int(v)
        except Exception:
            continue

    chat_active = int(active_map.get(chat_id, 0) or 0)
    pending_cleanup = snap.get("pending_cleanup", []) or []

    state_counts = _summarize_task_states()

    # Show up to 5 active rows for this chat
    rows: List[str] = []
    for did, it in list(active_downloads.items()):
        if int(it.get("chat_id") or 0) != int(chat_id):
            continue
        name = str(it.get("display_name") or it.get("filename") or f"#{did}")
        st = str(it.get("state") or "unknown")
        dl = int(it.get("downloaded") or 0)
        total = int(it.get("total") or 0)
        pct = (dl / total * 100.0) if total > 0 else 0.0
        rows.append(f"• {name} | {st} | {pct:.1f}%")
        if len(rows) >= 5:
            break
    if not rows:
        rows = ["• (当前聊天暂无活跃任务)"]

    # Human-friendly state summary
    def _cn_state(k: str) -> str:
        mapping = {
            "downloading": "下载中",
            "paused": "已暂停",
            "cancelling": "取消中",
            "cancelled": "已取消",
            "completed": "已完成",
            "failed": "失败",
        }
        return mapping.get(k, k)

    state_lines = []
    for k in sorted(state_counts.keys()):
        state_lines.append(f"- {_cn_state(k)}: {state_counts[k]}")
    if not state_lines:
        state_lines = ["- (无任务)"]

    txt = (
        "📊 TeleFlux 任务状态\n"
        f"版本：v{VERSION}\n"
        f"并发：{concurrency_limiter.get_running()}/{concurrency_limiter.get_limit()}\n"
        f"任务计数：当前聊天 {chat_active} | 全部聊天 {total_active}\n"
        f"待清理聊天：{len(pending_cleanup)}\n\n"
        "状态统计：\n"
        + "\n".join(state_lines)
        + "\n\n"
        "当前聊天任务预览：\n"
        + "\n".join(rows)
    )
    return txt


@client.on(events.NewMessage(pattern=r"^/status(?:\s+.*)?$"))
async def status_command(event):
    """查看任务状态，支持短时监控。\n\n用法：\n  /status\n  /status watch\n  /status stop"""
    if not _is_admin_event(event):
        await event.respond("❌ 无权限：请在私聊中使用该命令，或设置 ADMIN_USER_IDS")
        return

    chat_id = int(getattr(event, "chat_id", 0) or 0)
    user_id = int(getattr(event, "sender_id", 0) or 0)
    key = (chat_id, user_id)

    text = (event.raw_text or "").strip()
    parts = text.split(maxsplit=1)
    arg = parts[1].strip().lower() if len(parts) > 1 else ""

    if arg in {"stop", "end", "off"}:
        stopped = await _stop_session(_status_watch_sessions, key)
        await event.respond("✅ 已停止状态监控" if stopped else "当前没有运行中的状态监控")
        return

    if arg in {"watch", "follow", "w"}:
        await _stop_session(_status_watch_sessions, key)
        msg = await event.respond("⏳ 正在启动状态监控…")

        async def _runner():
            try:
                for _ in range(48):  # 240s, every 5s
                    await asyncio.sleep(5)
                    body = await _build_status_text(chat_id)
                    try:
                        await msg.edit(body)
                    except MessageNotModifiedError:
                        pass
                    except Exception:
                        pass
            except asyncio.CancelledError:
                return

        _status_watch_sessions[key] = asyncio.create_task(_runner())
        # Immediately render once
        try:
            await msg.edit(await _build_status_text(chat_id))
        except Exception:
            pass
        return

    await event.respond(await _build_status_text(chat_id))


@client.on(events.NewMessage(pattern=r"^/concurrency(?:\s+.*)?$"))
async def concurrency_command(event):
    """Set or show runtime concurrency limit.

    Usage:
      /concurrency            -> show current
      /concurrency 3          -> set to 3
    """
    if not _is_admin_event(event):
        await event.respond("❌ 无权限：请在私聊中使用该命令，或设置 ADMIN_USER_IDS")
        return

    text = (event.raw_text or "").strip()
    parts = text.split(maxsplit=1)

    if len(parts) == 1:
        await event.respond(
            f"当前并发上限: {concurrency_limiter.get_limit()}\n"
            f"正在运行: {concurrency_limiter.get_running()}\n\n"
            "设置示例: /concurrency 3"
        )
        return

    arg = parts[1].strip()
    if not arg.isdigit():
        await event.respond("参数错误：请输入纯数字，例如 /concurrency 3")
        return

    new_limit = int(arg)
    if new_limit < 1 or new_limit > 50:
        await event.respond("并发范围建议 1~50，请重新输入。")
        return

    await concurrency_limiter.set_limit(new_limit)
    global MAX_CONCURRENT_DOWNLOADS
    MAX_CONCURRENT_DOWNLOADS = new_limit

    runtime_settings.max_concurrent_downloads = new_limit
    save_settings(SETTINGS_PATH, runtime_settings)

    await event.respond(
        f"✅ 并发已更新为 {new_limit}\n"
        "说明：对新任务立即生效；已在运行的任务不会被强制中断。"
    )


@client.on(events.NewMessage(pattern=r"^/proxy(?:\s+.*)?$"))
async def proxy_command(event):
    """Set or show container/network proxy.

    This proxy is applied at process/container level (env) and also used for
    Telethon connection **on next startup**.

    Usage:
      /proxy                  -> show saved proxy
      /proxy off              -> disable
      /proxy socks5://host:1080
      /proxy socks5://user:pass@host:1080
      /proxy http://host:3128
    """
    if not _is_admin_event(event):
        await event.respond("❌ 无权限：请在私聊中使用该命令，或设置 ADMIN_USER_IDS")
        return

    text = (event.raw_text or "").strip()
    parts = text.split(maxsplit=1)

    if len(parts) == 1:
        saved = runtime_settings.proxy_url or "(未设置)"
        await event.respond(
            "当前代理设置（持久化）:\n"
            f"  {saved}\n\n"
            "设置示例: /proxy socks5://user:pass@127.0.0.1:1080\n"
            "关闭代理: /proxy off\n\n"
            "注意：代理对 Telegram 连接参数需要在启动时生效，设置后请重启容器。"
        )
        return

    arg = parts[1].strip()
    low = arg.lower()
    if low in {"off", "disable", "none", "0"}:
        runtime_settings.proxy_url = None
        save_settings(SETTINGS_PATH, runtime_settings)
        _apply_env_proxy(None)
        await event.respond(
            "✅ 已关闭代理（设置已保存）。\n"
            "为确保 Telegram 连接不再使用旧代理，请重启容器：docker restart teleflux-bot"
        )
        return

    # Validate format early
    try:
        _ = _telethon_proxy_from_url(arg)  # just validation
    except Exception as e:
        await event.respond(
            "❌ 代理格式不正确或不支持。\n"
            "支持：socks5/socks5h/socks4/socks4a/http/https\n"
            f"错误信息: {type(e).__name__}: {e}\n\n"
            "示例: /proxy socks5://127.0.0.1:1080"
        )
        return

    runtime_settings.proxy_url = arg
    save_settings(SETTINGS_PATH, runtime_settings)
    _apply_env_proxy(arg)

    await event.respond(
        "✅ 代理已保存。\n"
        f"当前设置: {arg}\n\n"
        "重要：Telegram 连接代理需要在启动时设置，请重启容器后生效：\n"
        "  docker restart teleflux-bot"
    )


async def _send_startup_notification() -> None:
    """Send a one-time startup notification after the container is running."""
    if not STARTUP_NOTIFY_CHAT_IDS:
        return

    # Give Telethon a moment to finish the initial handshake.
    await asyncio.sleep(1)

    proxy_show = runtime_settings.proxy_url or "(未设置)"
    msg = (
        f"✅ TeleFlux Bot 已启动\n"
        f"版本: v{VERSION}\n"
        f"并发上限: {concurrency_limiter.get_limit()}\n"
        f"代理: {proxy_show}"
    )

    for cid in STARTUP_NOTIFY_CHAT_IDS:
        try:
            await client.send_message(cid, msg)
        except Exception as e:
            logger.warning("启动通知发送失败：chat_id=%s，原因=%s", cid, e)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info(f"🚀 TeleFlux Bot v{VERSION} 启动中...")
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

    # 容器成功运行后通知（可选：设置 STARTUP_NOTIFY_CHAT_ID）
    try:
        client.loop.create_task(_send_startup_notification())
    except Exception:
        pass

    client.run_until_disconnected()


if __name__ == "__main__":
    main()
