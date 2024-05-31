import os
import logging
import shelve
from telegram import Update, User
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

from dj import DJ
from youtube import VideoFormatter

load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARN)
logger = logging.getLogger(__name__)

# Telegram Bot API token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

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
                "/pause — take a break from singing",
                "/unpause — continue singing",
                "Admin only:",
                "/next — show next song to be performed",
                "/remove — remove current singer because they have left"
                "/notready — pause current singer and move on",
            )
        )
    )


def is_url(text: str) -> bool:
    return text.startswith("https://")


def format_name(user: User) -> str:
    if user.username:
        return "@" + user.username
    return f"{user.first_name} {user.last_name}"


class KaraokeBot:
    def __init__(self, db: shelve.Shelf, admins: list[str]):
        self.formatter = (
            VideoFormatter(YOUTUBE_API_KEY, db) if YOUTUBE_API_KEY else None
        )
        self.dj = DJ(db, self.formatter)
        self.admins = set(admins)

    def _register(self, user: User) -> None:
        self.dj.register(user.id, format_name(user))

    async def request_song(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user = update.message.from_user
        self._register(user)
        song = update.message.text

        if is_url(song):
            self.dj.enqueue(user.id, song)
            await update.message.reply_text(
                "Your song request has been added to your list."
            )
            if self.formatter:
                await self.formatter.register_url(song)
        else:
            await update.message.reply_text("Invalid link. Please try again.")

    async def next(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return

        await update.message.reply_text(self.dj.next())

    async def notready(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return
        msgs = self.dj.notready()
        for chat_id, text in msgs:
            if chat_id is None:
                chat_id = update.effective_message.chat_id
            await update.get_bot().send_message(chat_id, text)

    async def remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return

        msg = self.dj.remove()
        await update.message.reply_text(msg)

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._register(update.message.from_user)
        msg = self.dj.clear(update.message.chat_id)
        await update.message.reply_text(msg)

    async def list_songs(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user = update.message.from_user
        self._register(user)
        msg = self.dj.show_queue(user.id, update.message.chat.id)
        await update.message.reply_text(msg)

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.message.from_user
        self._register(user)
        await update.message.reply_text(self.dj.pause(user.id))

    async def unpause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.message.from_user
        self._register(user)
        await update.message.reply_text(self.dj.unpause(user.id))

    async def list_all_queues(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        msg = self.dj.show_all_queues(requester=update.message.chat.id)
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
    application.add_handler(CommandHandler("notready", bot.notready))
    application.add_handler(CommandHandler("clear", bot.clear))
    application.add_handler(CommandHandler("list", bot.list_songs))
    application.add_handler(CommandHandler("listall", bot.list_all_queues))
    application.add_handler(CommandHandler("pause", bot.pause))
    application.add_handler(CommandHandler("unpause", bot.unpause))

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
