import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config import BOT_USERNAME, CHOICES, URL_PATTERN, logger
from downloader import (
    cleanup_files,
    compress_video,
    download_audio,
    download_video,
    expand_url,
)

pending_choices = {}


def handle_response(update: Update, text: str) -> str:
    processed = text.lower()
    user_name = update.message.chat.first_name
    if "hello" in processed:
        return f"Hey there {user_name} 👋"
    if "how are you" in processed:
        return "I am good!"
    if "who created you" in processed or "who made you" in processed:
        return "My developer is Yonathan"
    return "Sorry, I can’t understand what you wrote (Still in development 🛠️)"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey there! 🎥🔊 Welcome to ClipShot, your go-to genie for snatching videos and jamming to audio from Twitter, TikTok, and Instagram! Send me a URL, and let's get started!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Need a hand? 🛠️ Here’s the scoop on ClipShot commands:\n"
        "- `/start` - Kick off the fun!\n"
        "- `/help` - You’re here, genius!\n"
        "- `/custom` - For special requests.\n"
        "- `/introduction` - Meet the star of the show!\n\n"
        "Just drop a Twitter, YouTube, TikTok, or Instagram video/reel URL, and choose Video or Audio."
    )


async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Feeling fancy? 🕺 `/custom` is your backstage pass to special requests. Currently chilling, but stay tuned for more tricks up ClipShot’s sleeve!"
    )


async def introduction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Greetings, 🌟 I’m ClipShot, your trusty sidekick for capturing videos and audio from Twitter, TikTok, YouTube, and Instagram. Think of me as your personal DJ and filmmaker rolled into one! 🎶🎥\n\n"
        "Want to see the magic behind the curtain? Check out my repo and give it a star if you dig it! ⭐\n"
        "Repo: [github.com/Yonathan-T/ClipShot](https://github.com/Yonathan-T/ClipShot)"
    )


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    logger.info(f"Received message text: {message_text}")

    if any(short in message_text for short in ["x.com/i/status/", "vt.tiktok.com", "vm.tiktok.com", "fb.watch"]):
        message_text = await expand_url(message_text)
        logger.info(f"Expanded URL: {message_text}")

    if URL_PATTERN.match(message_text):
        logger.info(f"URL pattern matched: {message_text}")
        user_id = update.message.from_user.id
        pending_choices[user_id] = message_text
        context.user_data["pending_url"] = message_text

        keyboard = [
            [InlineKeyboardButton(CHOICES["video"], callback_data="video")],
            [InlineKeyboardButton(CHOICES["audio"], callback_data="audio")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose an option:", reply_markup=reply_markup)
    else:
        logger.info(f"URL pattern did not match: {message_text}")
        await update.message.reply_text("Please send a valid Twitter, YouTube, TikTok, Facebook, or Instagram URL.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data
    logger.info(f"Button callback received: choice='{choice}', user_id={user_id}")

    url = pending_choices.pop(user_id, None) or context.user_data.get("pending_url")
    if not url:
        logger.warning(f"No pending URL found for user {user_id}")
        await query.edit_message_text("No pending URL found. Please send a URL first.")
        return

    if choice not in CHOICES:
        await query.edit_message_text("Invalid choice.")
        return

    await query.edit_message_text(f"⏳ Processing {choice}... Please wait.")

    if choice == "video":
        await process_video_request(update, url, query)
    else:
        await process_audio_request(update, url, query)


async def process_video_request(update: Update, url: str, query):
    to_cleanup = []
    try:
        result = await download_video(url)
        downloaded_file = result["filepath"]
        title = result["title"]
        to_cleanup.extend(result["cleanup_files"])

        file_to_send = downloaded_file
        if os.path.getsize(downloaded_file) > 50 * 1024 * 1024:
            compressed_file = await compress_video(downloaded_file)
            to_cleanup.append(compressed_file)
            file_to_send = compressed_file

            if os.path.getsize(compressed_file) > 50 * 1024 * 1024:
                await update.effective_message.reply_text(
                    "Sorry, the video is too large to send via Telegram (limit is 50 MB). Try a shorter video."
                )
                return

        with open(file_to_send, "rb") as video_file:
            try:
                await query.delete_message()
            except Exception:
                pass

            await update.effective_message.reply_video(
                video=video_file,
                caption="Here's your video! 🎥",
                supports_streaming=True,
                filename=f"{title}.mp4",
                read_timeout=120,
                write_timeout=120,
                connect_timeout=60,
            )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing video: {error_msg}")
        try:
            await query.delete_message()
        except Exception:
            pass

        if "tiktok" in url.lower() and "photo" in url.lower():
            await update.effective_message.reply_text("❗ Sorry, I can't download TikTok photo slideshows.")
        else:
            await update.effective_message.reply_text(
                f"❗ An error occurred while downloading: {error_msg}\n"
                "Please make sure the post is public and try again."
            )
    finally:
        cleanup_files(to_cleanup)


async def process_audio_request(update: Update, url: str, query):
    to_cleanup = []
    try:
        result = await download_audio(url)
        audio_file = result["filepath"]
        title = result["title"]
        to_cleanup.extend(result["cleanup_files"])

        with open(audio_file, "rb") as f:
            try:
                await query.delete_message()
            except Exception:
                pass

            await update.effective_message.reply_audio(
                audio=f,
                caption="Here's your audio! 🎶",
                filename=f"{title}.mp3",
                read_timeout=120,
                write_timeout=120,
                connect_timeout=60,
            )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing audio: {error_msg}")
        try:
            await query.delete_message()
        except Exception:
            pass

        if "tiktok" in url.lower() and "photo" in url.lower():
            await update.effective_message.reply_text("❗ Sorry, I can't extract audio from TikTok photos.")
        else:
            await update.effective_message.reply_text(
                f"❗ An error occurred while extracting audio: {error_msg}\n"
                "Please make sure the post is public and try again."
            )
    finally:
        cleanup_files(to_cleanup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type = update.message.chat.type
    text = update.message.text
    logger.info(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type in ["group", "supergroup"]:
        if BOT_USERNAME and BOT_USERNAME in text:
            new_text = text.replace(BOT_USERNAME, "").strip()
            response = handle_response(update, new_text)
        else:
            return
    else:
        response = handle_response(update, text)

    logger.info(f"Bot: {response}")
    await update.message.reply_text(response)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
