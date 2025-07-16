# ClipShot

ClipShot is a simple Telegram bot for downloading videos and audio from Twitter, Instagram, and YouTube. Whether you're looking to save a memorable video or extract the audio from a reel, ClipShot makes it easy! 🎥🔊

## Features
- Download videos from Twitter, Instagram, and YouTube
- Extract audio as MP3 from supported videos
- Simple Telegram interface with buttons for video/audio choice
- Handles large files by compressing videos if needed

## Requirements
- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [ffmpeg](https://ffmpeg.org/) (must be in your PATH)
- requests

## Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Yonathan-T/ClipShot.git
   cd ClipShot
   ```
2. **Install dependencies:**
   ```bash
   pip install yt-dlp python-telegram-bot requests
   ```
   Make sure `ffmpeg` is installed and available in your system PATH. On Windows, you can use Chocolatey:
   ```bash
   choco install ffmpeg
   ```
3. **Add your Telegram bot credentials:**
   Create a file at `src/secure.py` with the following content:
   ```python
   TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
   BOT_USERNAME = "YOUR_BOT_USERNAME"
   ```
4. **Run the bot:**
   ```bash
   python src/main.py
   ```

## Usage
- Start a chat with the bot on Telegram: [@Clip_Shot_Urls_Bot](https://t.me/Clip_Shot_Urls_Bot)
- **No need to join any random channels to use the bot btw 👀!** Just start chatting and enjoy.
- Send a Twitter, Instagram, or YouTube video URL.
- Choose whether you want the video or just the audio.
- The bot will reply with your requested media (if possible).

## Screenshots

![ClipShot Example](assets/screenshot1.png)

## Contributing
Pull requests are welcome! Please open an issue first if you want to discuss a major change.
And of course, star the repo ⭐

---

**GitHub Repository:** [https://github.com/Yonathan-T/ClipShot](https://github.com/Yonathan-T/ClipShot)