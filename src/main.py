import re
import io
import requests
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_dlp import YoutubeDL
import logging
import tempfile
import uuid
import subprocess
import time
import asyncio

TOKEN = os.environ.get('TOKEN')
BOT_USERNAME = os.environ.get('BOT_USERNAME')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"

URL_PATTERN = re.compile(
    r'https?://(?:www\.)?(?:x\.com|twitter\.com|instagram\.com|youtube\.com|youtu\.be)/.+(?:\?.+)?'
)

CHOICES = {
    'video': 'Video',
    'audio': 'Audio'
}
pending_choices = {}

def expand_url(short_url):
    response = requests.head(short_url, allow_redirects=True)
    return response.url

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey there! 🎥🔊 Welcome to ClipShot, your go-to genie for snatching videos and jamming to audio from Twitter and Instagram! Ready to dive into the media madness? Send me a URL, and let's get this party started!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Need a hand? 🛠️ Here’s the scoop on ClipShot commands:\n- `/start` - Kick off the fun!\n- `/help` - You’re here, genius!\n- `/custom` - For those special requests.\n- `/introduction` - Meet the star of the show!\nJust drop a Twitter , Youtube or Instagram video/reel URL, and choose Video or Audio. Let’s make some magic happen!")

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Feeling fancy? 🕺 `/custom` is your backstage pass to special requests. Currently, it’s chilling, but stay tuned for more tricks up ClipShot’s sleeve! (This was a test command sorry 😁)")

async def introduction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Greetings, 🌟 I’m ClipShot, your trusty sidekick for capturing videos and audio from Twitter and Instagram. Think of me as your personal DJ and filmmaker rolled into one! 🎶🎥\nWant to see the magic behind the curtain? Check out my repo and give it a star if you dig it! ⭐\nRepo Link: [github.com/Yonathan-T/ClipShot](https://github.com/Yonathan-T/ClipShot)\nNow, let’s get clipping and shooting!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    logger.info(f"Received message text: {message_text}")
    if message_text.startswith("https://x.com/i/status/"):
        message_text = expand_url(message_text)
        logger.info(f"Expanded URL: {message_text}")
    if URL_PATTERN.match(message_text):
        logger.info(f"URL pattern matched: {message_text}")
        user_id = update.message.from_user.id
        pending_choices[user_id] = message_text
        keyboard = [
            [InlineKeyboardButton(CHOICES['video'], callback_data='video')],
            [InlineKeyboardButton(CHOICES['audio'], callback_data='audio')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose an option:", reply_markup=reply_markup)
    else:
        logger.info(f"URL pattern did not match: {message_text}")
        await update.message.reply_text("Please send a valid Twitter , Youtube or Instagram video/reel URL or use a command.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in pending_choices:
        await query.edit_message_text("No pending URL. Please send a URL first.")
        return
    url = pending_choices[user_id]
    choice = query.data
    if choice not in CHOICES:
        await query.edit_message_text("Invalid choice.")
        return
    await query.edit_message_text(f"Processing {CHOICES[choice]} from {url}... Please wait.")
    try:
        if choice == 'video':
            await process_video(update, context, url)
        else: 
            await process_audio(update, context, url)
        del pending_choices[user_id]
    except Exception as e:
        logger.error(f"Error processing {choice}: {e}")
        await query.edit_message_text(f"Error processing {choice}: {str(e)}. Please try again.")

async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    tmp_basename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
    compressed_filename = tmp_basename + "_compressed.mp4"
    ydl_opts = {
        'format': 'best',
        'ffmpeg_location': FFMPEG_PATH,
        'outtmpl': tmp_basename,
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    downloaded_file = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        if 'requested_downloads' in info and info['requested_downloads']:
            downloaded_file = info['requested_downloads'][0]['filepath']
        elif '_filename' in info:
            downloaded_file = info['_filename']
        else:
            downloaded_file = tmp_basename
        logger.info(f"Downloaded file size: {os.path.getsize(downloaded_file)} bytes")
        if os.path.getsize(downloaded_file) <= 50 * 1024 * 1024:
            with open(downloaded_file, 'rb') as f:
                buffer = io.BytesIO(f.read())
                buffer.seek(0)
                await update.effective_message.reply_video(
                    video=buffer,
                    caption="Here’s your video!",
                    supports_streaming=True,
                    filename=f"{info.get('title', 'video')}.mp4"
                )
            return
        for _ in range(10):
            if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                break
            time.sleep(0.2)
        else:
            await update.effective_message.reply_text("Error: Downloaded video is empty or not found.")
            return
        logger.info(f"Running ffmpeg: {FFMPEG_PATH} -i {downloaded_file} ...")
        try:
            ffmpeg_cmd = [
                FFMPEG_PATH,
                '-i', downloaded_file,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ac', '2',
                '-y',
                compressed_filename
            ]
            logger.info(f"ffmpeg command: {' '.join(ffmpeg_cmd)}")
            subprocess.run(ffmpeg_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e}")
            await update.effective_message.reply_text("Error: ffmpeg failed to compress the video. Please try a different video or check ffmpeg permissions.")
            return
        except PermissionError as e:
            logger.error(f"Permission error: {e}")
            await update.effective_message.reply_text("Permission error: ffmpeg could not access the file. Try running as administrator or check your antivirus settings.")
            return
        if not os.path.exists(compressed_filename) or os.path.getsize(compressed_filename) == 0:
            await update.effective_message.reply_text("Error: Compressed video is empty or not found.")
            return
        if os.path.getsize(compressed_filename) > 50 * 1024 * 1024:
            await update.effective_message.reply_text("Sorry, the video is too large to send via Telegram (limit is 50 MB). Try a shorter or lower-quality video.")
            return
        with open(compressed_filename, 'rb') as f:
            buffer = io.BytesIO(f.read())
            buffer.seek(0)
            await update.effective_message.reply_video(
                video=buffer,
                caption="Here’s your video!",
                supports_streaming=True,
                filename=f"{info.get('title', 'video')}.mp4"
            )
    finally:
        for f in [downloaded_file, compressed_filename]:
            if f is not None:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as e:
                    logger.error(f"Failed to remove temp file {f}: {e}")

async def process_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    tmp_basename = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}")
    tmp_filename = tmp_basename + ".mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': FFMPEG_PATH,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': tmp_basename,
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        with open(tmp_filename, 'rb') as f:
            buffer = io.BytesIO(f.read())
            buffer.seek(0)
            await update.effective_message.reply_audio(
                audio=buffer,
                caption="Here’s your audio!",
                filename=f"{info.get('title', 'audio')}.mp3"
            )
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

def handle_response(update: Update, text: str) -> str:
    processed = text.lower()
    user_name = update.message.chat.first_name
    if "hello" in processed:
        return f"Hey there {user_name} 👋"
    if "how are you" in processed:
        return "I am good!"
    if "who created you" in processed:
        return "My developer is Yonathan"
    if "who made you" in processed:
        return "My developer is Yonathan"
    return "Sorry, I can’t understand what you wrote (Still in development 🛠️)"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type = update.message.chat.type
    text = update.message.text
    logger.info(f'User ({update.message.chat.id}) in {message_type}: "{text}"')
    if message_type == 'group':
        if BOT_USERNAME in text:
            new_text = text.replace(BOT_USERNAME, '').strip()
            response = handle_response(update, new_text)
        else:
            return
    else:
        response = handle_response(update, text)
    logger.info(f"Bot: {response}")
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    logger.info('Starting bot...')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('custom', custom_command))
    app.add_handler(CommandHandler('introduction', introduction_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.StatusUpdate.ALL, handle_message))
    app.add_error_handler(error)
    asyncio.run(app.run_polling(poll_interval=3))