#!./venv/bin/python3
import os
import logging
import shelve
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from telegram.constants import ParseMode
from telegram_markdown_text import Italic
from dotenv import load_dotenv

from dj import DJ
from youtube import VideoFormatter

load_dotenv()

# pyre-ignore-all-errors[16]

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


async def start(update: Update, context: CallbackContext) -> None:
    assert update.message is not None
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
                "/remove — remove current singer because they have left",
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
        self.last_msg_with_buttons: Message | None = None

    def _register(self, user: User) -> None:
        self.dj.register(user.id, format_name(user))

    async def request_song(self, update: Update, context: CallbackContext) -> None:
        message = update.message
        assert message and message.from_user
        user = message.from_user
        self._register(user)
        song = message.text or ""

        if not is_url(song):
            await message.reply_text("Invalid link. Please try again.")
            return

        self.dj.enqueue(user.id, song)
        await message.reply_text("Your song request has been added to your list.")
        if self.formatter:
            await self.formatter.register_url(song)

    async def next(self, update: Update, context: CallbackContext) -> None:
        message = update.message
        if not (message and message.from_user and message.from_user.username):
            return
        if not self.is_admin(message.from_user.username):
            await message.reply_text("Only the admin can use this command.")
            return
        await self.next_impl(message)

    async def next_impl(self, message: Message) -> None:
        text, url = self.dj.next()
        if not url:
            await message.chat.send_message(text)
            return

        peek = self.dj.peek_next()
        if peek:
            notification = Italic("Next in queue:") + " " + self.dj._format_singer(peek)
            text = text + "\n\n" + notification.escaped_text()

        song_button = InlineKeyboardButton(text="▶️ Play song", url=url)
        not_ready_button = InlineKeyboardButton(
            text="⏳ Singer not ready", callback_data="not_ready"
        )
        next_button = InlineKeyboardButton(text="⬇️ Next singer", callback_data="next")
        inline_keyboard = InlineKeyboardMarkup(
            [[song_button], [not_ready_button], [next_button]]
        )

        sent = await message.chat.send_message(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=inline_keyboard,
            disable_web_page_preview=True,
        )

        if self.last_msg_with_buttons:
            await self.last_msg_with_buttons.edit_reply_markup(reply_markup=None)
        self.last_msg_with_buttons = sent

    async def button_callback(self, update: Update, context: CallbackContext) -> None:
        await update.callback_query.answer()
        match update.callback_query.data:
            case "not_ready":
                if self.is_admin(update.callback_query.from_user.username):
                    await self.notready_impl(update)
            case "next":
                if self.is_admin(update.callback_query.from_user.username):
                    assert update.effective_message is not None
                    await self.next_impl(update.effective_message)

    async def notready(self, update: Update, context: CallbackContext) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return
        await self.notready_impl(update)

    async def notready_impl(self, update: Update) -> None:
        msgs = self.dj.notready()
        for chat_id, text in msgs:
            if chat_id is None:
                chat_id = update.effective_message.chat_id
            await update.get_bot().send_message(chat_id=chat_id, text=text)

    async def remove(self, update: Update, context: CallbackContext) -> None:
        if not self.is_admin(update.message.from_user.username):
            await update.message.reply_text("Only the admin can use this command.")
            return

        msg = self.dj.remove()
        await update.message.reply_text(msg)

    async def clear(self, update: Update, context: CallbackContext) -> None:
        self._register(update.message.from_user)
        msg = self.dj.clear(update.message.chat_id)
        await update.message.reply_text(msg)

    async def list_songs(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)
        msg = self.dj.show_queue(user.id, (user.id == update.message.chat.id))
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

    async def pause(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)
        await update.message.reply_text(self.dj.pause(user.id))

    async def unpause(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)
        await update.message.reply_text(self.dj.unpause(user.id))

    async def list_all_queues(self, update: Update, context: CallbackContext) -> None:
        is_admin = self.is_admin(update.message.from_user.username)
        msg = self.dj.show_all_queues(
            requester=update.message.chat.id, is_admin=is_admin
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )

    def is_admin(self, username: str) -> bool:
        return username in self.admins


async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"Exception while handling an update ({update}): {context.error}")


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

    application.add_handler(CallbackQueryHandler(bot.button_callback))

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
