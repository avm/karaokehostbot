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

# Admin user configuration
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')

# User song lists and queue
user_song_lists = {}
queue = []
not_ready_singers = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to the Karaoke Bot! Send a YouTube link to request a song.")

async def request_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    youtube_link = update.message.text

    if is_valid_youtube_link(youtube_link):
        if user.username not in user_song_lists:
            user_song_lists[user.username] = []
        user_song_lists[user.username].append(youtube_link)

        if user.username not in queue:
            queue.append(user.username)

        await update.message.reply_text("Your song request has been added to your list.")
    else:
        await update.message.reply_text("Invalid YouTube link. Please try again.")

def is_valid_youtube_link(link: str) -> bool:
    youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:\S+)'
    return re.match(youtube_regex, link) is not None

async def next_singer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    # Check if there are any singers in the not_ready_singers list
    for username in not_ready_singers:
        if user_song_lists[username]:
            queue.append(username)
            not_ready_singers.remove(username)

    if queue:
        username = queue[0]
        if user_song_lists[username]:
            youtube_link = user_song_lists[username][0]
            await update.message.reply_text(f"Next singer: @{username} - {youtube_link}\n\n"
                                            f"Available commands:\n"
                                            f"/nextsinger - Get the next singer in the queue\n"
                                            f"/done - Mark the current singer as done\n"
                                            f"/remove <username> - Remove a singer from the queue\n"
                                            f"/move <username> - Move a singer to the not_ready_singers list")
        else:
            queue.pop(0)
            await next_singer(update, context)
    else:
        await update.message.reply_text("The queue is currently empty.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    if queue:
        username = queue.pop(0)
        if user_song_lists[username]:
            user_song_lists[username].pop(0)
        await update.message.reply_text(f"Singer @{username} marked as done.")
    else:
        await update.message.reply_text("The queue is currently empty.")

async def remove_singer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    username = context.args[0] if context.args else None


    if username:
        if username in queue:
            queue.remove(username)
            await update.message.reply_text(f"Singer @{username} has been removed from the queue.")
        else:
            await update.message.reply_text(f"Singer @{username} not found in the queue.")
    else:
        await update.message.reply_text("Please provide the username of the singer to remove.")

async def move_singer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.message.from_user.username):
        await update.message.reply_text("Only the admin can use this command.")
        return

    username = context.args[0] if context.args else None

    if username:
        if username in queue:
            queue.remove(username)
            not_ready_singers.append(username)
            await update.message.reply_text(f"Singer @{username} has been removed from the queue and will be added back when they are ready.")
        else:
            await update.message.reply_text(f"Singer @{username} not found in the queue.")
    else:
        await update.message.reply_text("Please provide the username of the singer to move.")

async def clear_song_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.username in user_song_lists:
        user_song_lists[user.username].clear()
        await update.message.reply_text("Your song list has been cleared.")
    else:
        await update.message.reply_text("You have no songs in your list.")

async def view_song_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.username in user_song_lists:
        song_list = user_song_lists[user.username]
        if song_list:
            song_list_text = "\n".join(song_list)
            await update.message.reply_text(f"Your song list:\n{song_list_text}")
        else:
            await update.message.reply_text("Your song list is empty.")
    else:
        await update.message.reply_text("You have no songs in your list.")

def is_admin(username: str) -> bool:
    return username == ADMIN_USERNAME

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, request_song))
    application.add_handler(CommandHandler("nextsinger", next_singer))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("remove", remove_singer))
    application.add_handler(CommandHandler("move", move_singer))
    application.add_handler(CommandHandler("clearlist", clear_song_list))
    application.add_handler(CommandHandler("viewlist", view_song_list))

    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()

