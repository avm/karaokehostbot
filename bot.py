import os
import re
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot API token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# Queue data structure
queue = []

def start(update, context):
    update.message.reply_text("Welcome to the Karaoke Bot! Send a YouTube link to request a song.")

def request_song(update, context):
    user = update.message.from_user
    youtube_link = update.message.text

    if is_valid_youtube_link(youtube_link):
        queue.append((user.username, youtube_link))
        update.message.reply_text("Your song request has been added to the queue.")
    else:
        update.message.reply_text("Invalid YouTube link. Please try again.")

def is_valid_youtube_link(link):
    youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:\S+)'
    return re.match(youtube_regex, link) is not None

def next_singer(update, context):
    if len(queue) > 0:
        username, youtube_link = queue[0]
        update.message.reply_text(f"Next singer: {username}\nYouTube link: {youtube_link}")
    else:
        update.message.reply_text("The queue is currently empty.")

def done(update, context):
    if len(queue) > 0:
        username, _ = queue.pop(0)
        update.message.reply_text(f"Singer {username} marked as done.")
    else:
        update.message.reply_text("The queue is currently empty.")

def remove_singer(update, context):
    username = context.args[0] if context.args else None

    if username:
        found = False
        for singer in queue:
            if singer[0] == username:
                queue.remove(singer)
                found = True
                break

        if found:
            update.message.reply_text(f"Singer {username} has been removed from the queue.")
        else:
            update.message.reply_text(f"Singer {username} not found in the queue.")
    else:
        update.message.reply_text("Please provide the username of the singer to remove.")

def error(update, context):
    logger.warning(f"Update {update} caused error {context.error}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, request_song))
    dispatcher.add_handler(CommandHandler("nextsinger", next_singer))
    dispatcher.add_handler(CommandHandler("done", done))
    dispatcher.add_handler(CommandHandler("remove", remove_singer))

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

