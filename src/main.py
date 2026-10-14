from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from config import PORT, TOKEN, URL_PATTERN, WEBHOOK_URL, cleanup_cookies, logger
from handlers import (
    button_handler,
    custom_command,
    error_handler,
    handle_message,
    handle_url,
    help_command,
    introduction_command,
    start_command,
)

try:
    from telegram.ext._utils.webhookhandler import TelegramHandler

    async def _health_check_get(self):
        self.set_header("Content-Type", "text/html")
        self.write(
            "<html><body><h1>ClipShot is running!</h1><p>Bot is active and listening for webhooks.</p></body></html>"
        )

    TelegramHandler.SUPPORTED_METHODS = ("POST", "GET")
    TelegramHandler.get = _health_check_get
except Exception as e:
    logger.warning(f"Could not monkeypatch TelegramHandler for health checks: {e}")


def build_application() -> Application:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("custom", custom_command))
    app.add_handler(CommandHandler("introduction", introduction_command))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(URL_PATTERN), handle_url)
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(URL_PATTERN) & ~filters.StatusUpdate.ALL,
            handle_message,
        )
    )
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    return app


if __name__ == "__main__":
    logger.info("Initializing ClipShot...")
    app = build_application()

    try:
        if PORT and WEBHOOK_URL:
            logger.info(f"Starting bot in Webhook mode on port {PORT} (webhook_url={WEBHOOK_URL})...")
            app.run_webhook(
                listen="0.0.0.0",
                port=int(PORT),
                url_path="",
                webhook_url=WEBHOOK_URL,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
        else:
            logger.info("Starting bot in Polling mode...")
            app.run_polling(
                poll_interval=1,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
    finally:
        cleanup_cookies()
