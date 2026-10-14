import asyncio
import os
import subprocess
import tempfile
import uuid
import httpx
from yt_dlp import YoutubeDL
from config import COOKIES_FILE, FFMPEG_BINARY, FFMPEG_PATH, logger

DEFAULT_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


async def expand_url(short_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(short_url)
            return str(response.url)
    except Exception as e:
        logger.error(f"Error expanding URL '{short_url}': {e}")
        return short_url


async def download_video(url: str) -> dict:
    tmp_basename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
    ydl_opts = {
        "format": "best",
        "ffmpeg_location": FFMPEG_PATH if (FFMPEG_PATH and os.path.exists(FFMPEG_PATH)) else None,
        "outtmpl": tmp_basename,
        "cookiefile": COOKIES_FILE,
        "quiet": True,
        "http_headers": DEFAULT_HTTP_HEADERS,
    }

    def _sync_download():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    info = await asyncio.to_thread(_sync_download)

    if "requested_downloads" in info and info["requested_downloads"]:
        downloaded_file = info["requested_downloads"][0]["filepath"]
    elif "_filename" in info:
        downloaded_file = info["_filename"]
    else:
        downloaded_file = tmp_basename

    logger.info(f"Downloaded file '{downloaded_file}', size: {os.path.getsize(downloaded_file)} bytes")

    return {
        "filepath": downloaded_file,
        "title": info.get("title", "video"),
        "cleanup_files": [downloaded_file],
    }


async def compress_video(input_path: str) -> str:
    compressed_filename = input_path + "_compressed.mp4"
    ffmpeg_cmd = [
        FFMPEG_BINARY,
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        "-y",
        compressed_filename,
    ]
    logger.info(f"Running FFmpeg compression: {' '.join(ffmpeg_cmd)}")
    await asyncio.to_thread(subprocess.run, ffmpeg_cmd, check=True)

    if not os.path.exists(compressed_filename) or os.path.getsize(compressed_filename) == 0:
        raise RuntimeError("Compressed video file is empty or was not created.")

    return compressed_filename


async def download_audio(url: str) -> dict:
    tmp_basename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
    tmp_filename = tmp_basename + ".mp3"
    ydl_opts = {
        "format": "bestaudio/best",
        "ffmpeg_location": FFMPEG_PATH if (FFMPEG_PATH and os.path.exists(FFMPEG_PATH)) else None,
        "cookiefile": COOKIES_FILE,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": tmp_basename,
        "quiet": True,
        "http_headers": DEFAULT_HTTP_HEADERS,
    }

    def _sync_audio_download():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    info = await asyncio.to_thread(_sync_audio_download)

    return {
        "filepath": tmp_filename,
        "title": info.get("title", "audio"),
        "cleanup_files": [tmp_filename],
    }


def cleanup_files(files: list[str]):
    for f in files:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                logger.error(f"Failed to delete temp file '{f}': {e}")
