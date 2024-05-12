import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot API token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Queue data structure
queue = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to the Karaoke Bot! Send a YouTube link to request a song.")

async def request_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    youtube_link = update.message.text

    if is_valid_youtube_link(youtube_link):
        queue.append((user.username, youtube_link))
        await update.message.reply_text("Your song request has been added to the queue.")
    else:
        await update.message.reply_text("Invalid YouTube link. Please try again.")

def is_valid_youtube_link(link: str) -> bool:
    youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:\S+)'
    return re.match(youtube_regex, link) is not None

async def next_singer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if queue:
        username, youtube_link = queue[0]
        await update.message.reply_text(f"Next singer: {username}\nYouTube link: {youtube_link}")
    else:
        await update.message.reply_text("The queue is currently empty.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if queue:
        username, _ = queue.pop(0)
        await update.message.reply_text(f"Singer {username} marked as done.")
    else:
        await update.message.reply_text("The queue is currently empty.")

async def remove_singer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = context.args[0] if context.args else None

    if username:
        found = False
        for singer in queue:
            if singer[0] == username:
                queue.remove(singer)
                found = True
                break

        if found:
            await update.message.reply_text(f"Singer {username} has been removed from the queue.")
        else:
            await update.message.reply_text(f"Singer {username} not found in the queue.")
    else:
        await update.message.reply_text("Please provide the username of the singer to remove.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, request_song))
    application.add_handler(CommandHandler("nextsinger", next_singer))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("remove", remove_singer))

    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()

