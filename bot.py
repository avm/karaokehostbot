import os
import re
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


dj = DJ(shelve.open("bot"))


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


async def request_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    youtube_link = update.message.text

    if is_valid_youtube_link(youtube_link):
        dj.enqueue(update.message.chat_id, format_name(user), youtube_link)
        await update.message.reply_text(
            "Your song request has been added to your list."
        )
    else:
        await update.message.reply_text("Invalid YouTube link. Please try again.")


def is_valid_youtube_link(link: str) -> bool:
    youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:\S+)"
    return re.match(youtube_regex, link) is not None


async def next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    await update.message.reply_text(dj.next())


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    msg = dj.remove()
    await update.message.reply_text(msg)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = dj.clear(update.message.chat_id)
    await update.message.reply_text(msg)


def format_name(user):
    if user.username:
        return "@" + user.username
    return f"{user.first_name} {user.last_name}"


async def list_songs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.chat_id
    msg = dj.show_queue(user)
    await update.message.reply_text(msg)


async def list_all_queues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = dj.show_all_queues()
    await update.message.reply_text(msg)


def is_admin(username: str) -> bool:
    return username in ADMIN_USERNAMES


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, request_song)
    )
    application.add_handler(CommandHandler("next", next))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("listall", list_all_queues))

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
