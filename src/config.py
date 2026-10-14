import logging
import os
import re
import shutil
import tempfile
import uuid

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ClipShot")

try:
    from secure import BOT_USERNAME as SECURE_USERNAME, TOKEN as SECURE_TOKEN
except ImportError:
    SECURE_TOKEN = None
    SECURE_USERNAME = None

TOKEN = os.environ.get("TOKEN", SECURE_TOKEN)
BOT_USERNAME = os.environ.get("BOT_USERNAME", SECURE_USERNAME)

YT_COOKIES = os.environ.get("YT_COOKIES")
COOKIES_FILE = None
if YT_COOKIES:
    try:
        tmp_dir = tempfile.gettempdir()
        COOKIES_FILE = os.path.join(tmp_dir, f"cookies_{uuid.uuid4()}.txt")
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(YT_COOKIES)
        logger.info(f"YouTube cookies loaded into {COOKIES_FILE}")
    except Exception as e:
        logger.error(f"Failed to load YT_COOKIES: {e}")
        COOKIES_FILE = None

FFMPEG_BINARY = shutil.which("ffmpeg") or ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
FFMPEG_PATH = os.path.dirname(FFMPEG_BINARY) if os.path.isabs(FFMPEG_BINARY) else None

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:x\.com|twitter\.com|instagram\.com|youtube\.com|youtu\.be|tiktok\.com|vt\.tiktok\.com|vm\.tiktok\.com|facebook\.com|fb\.watch)/.+(?:\?.+)?"
)

CHOICES = {
    "video": "Video",
    "audio": "Audio",
}

PORT = os.environ.get("PORT")
WEBHOOK_URL = (
    os.environ.get("WEBHOOK_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or ("https://clipshot.onrender.com" if PORT else None)
)


def cleanup_cookies():
    global COOKIES_FILE
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        try:
            os.remove(COOKIES_FILE)
            logger.info("Cleanup: Removed temporary cookies file")
        except Exception as e:
            logger.error(f"Failed to remove cookies file: {e}")
