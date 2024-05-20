import os
import logging
import shelve
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

from dj import DJ

load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARN)
logger = logging.getLogger(__name__)

# Telegram Bot API token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Admin user configuration
ADMIN_USERNAMES = os.environ.get("ADMIN_USERNAMES", "").split(",")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "\n".join(
            (
                "Welcome to the Karaoke Bot! Send a YouTube link to request a song.",
                "Commands:",
                "/list — show your queue",
                "/listall — show all queues",
                "/clear — clear your queue",
                "Admin only:",
                "/next — show next song to be performed",
            )
        )
    )


def is_url(text: str) -> bool:
    return text.startswith("https://")


def format_name(user):
    if user.username:
        return "@" + user.username
    return f"{user.first_name} {user.last_name}"


class KaraokeBot:
    def __init__(self, db: shelve.Shelf, admins: list[str]):
        self.dj = DJ(db)
        self.admins = set(admins)

    async def request_song(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user = update.message.from_user
        song = update.message.text

        if is_url(song):
            self.dj.enqueue(update.message.chat_id, format_name(user), song)
            await update.message.reply_text(
                "Your song request has been added to your list."
            )
        else:
            await update.message.reply_text("Invalid YouTube link. Please try again.")

    async def next(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return

        await update.message.reply_text(self.dj.next())

    async def remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return

        msg = self.dj.remove()
        await update.message.reply_text(msg)

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = self.dj.clear(update.message.chat_id)
        await update.message.reply_text(msg)

    async def list_songs(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user = update.message.chat_id
        msg = self.dj.show_queue(user)
        await update.message.reply_text(msg)

    async def list_all_queues(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        msg = self.dj.show_all_queues()
        await update.message.reply_text(msg)

    def is_admin(self, username: str) -> bool:
        return username in self.admins


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    bot = KaraokeBot(shelve.open("bot"), ADMIN_USERNAMES)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.request_song)
    )
    application.add_handler(CommandHandler("next", bot.next))
    application.add_handler(CommandHandler("remove", bot.remove))
    application.add_handler(CommandHandler("clear", bot.clear))
    application.add_handler(CommandHandler("list", bot.list_songs))
    application.add_handler(CommandHandler("listall", bot.list_all_queues))

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
