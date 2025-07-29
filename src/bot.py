#!./venv/bin/python3
import os
import asyncio
import logging
import shelve
import json
from functools import wraps
from telegram import (
    Update,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MaybeInaccessibleMessage,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from telegram.constants import ParseMode
from aiohttp import web
from dotenv import load_dotenv

from dj import DJ
from party import Party
from youtube import VideoFormatter, SongInfo

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

ADMIN_USERNAMES = os.environ.get("ADMIN_USERNAMES", "")


def is_url(text: str) -> bool:
    return text.startswith("https://")


def format_name(user: User) -> str:
    if user.username:
        return "@" + user.username
    name = user.first_name
    if user.last_name:
        name += " " + user.last_name
    return name


async def maybe(coro):
    try:
        await coro
    except Exception as e:
        logger.error(f"Error: {e}")


def admin_only(func):
    @wraps(func)
    async def wrapper(self, update: Update, context: CallbackContext, *args, **kwargs):
        message = update.message
        if not (message and message.from_user and message.from_user.username):
            return
        if not self.is_admin(message.from_user.username):
            await message.reply_text("Only the admin can use this command.")
            return
        return await func(self, update, context, *args, **kwargs)

    return wrapper


def btn(text: str, action: str, **params) -> InlineKeyboardButton:
    cb_data = json.dumps({"a": action} | params, separators=(",", ":"))
    return InlineKeyboardButton(text, callback_data=cb_data)


class KaraokeBot:
    def __init__(self, db: shelve.Shelf):
        self.formatter = (
            VideoFormatter(YOUTUBE_API_KEY, db) if YOUTUBE_API_KEY else None
        )
        self.dj = DJ(Party(db, 0, set(ADMIN_USERNAMES.split(","))), self.formatter)
        self.last_msg_with_buttons: Message | None = None
        self.websockets = []

    def _register(self, user: User) -> None:
        self.dj.register(user.id, format_name(user))

    async def start(self, update: Update, context: CallbackContext) -> None:
        assert update.message is not None
        await update.message.reply_html(
            "\n".join(
                (
                    "Welcome to the Karaoke Bot!",
                    "",
                    "Send a YouTube link to request a song. Send a search term like "
                    "<code>beatles yesterday</code> to find a karaoke track.",
                    "",
                    "Commands:",
                    "/list — view and edit your song list",
                    "/clear — clear your song list",
                    "/queue — view singer queue",
                    "/pause — take a break from singing",
                    "/unpause — continue singing",
                )
                + (
                    (
                        "",
                        "Admin only:",
                        "/next — show next song to be performed",
                        "/remove — remove current singer because they have left",
                        "/notready — pause current singer and move on",
                        "/reset — clear all queues",
                        "/admins [+newadmin] [-oldadmin] — show or update the list of admins",
                    )
                    if self.is_admin(update.message.from_user.username)
                    else ()
                )
            )
        )

    async def send_search_result_with_thumbnail(self, bot, chat_id, result) -> None:
        await bot.sendPhoto(chat_id, result["thumbnail"])

        button = [[btn("Add to my list", "add", u=result["url"])]]
        reply_markup = InlineKeyboardMarkup(button)

        text = f"{result['title']}\n<i>{result['channel']}</i>"
        await bot.sendMessage(
            chat_id, text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )

    async def request_song(self, update: Update, context: CallbackContext) -> None:
        message = update.message
        if message.chat.type != "private":
            return
        assert message and message.from_user
        user = message.from_user
        self._register(user)
        song = message.text or ""

        if not is_url(song):
            if self.formatter:
                await context.bot.send_chat_action(
                    chat_id=message.chat_id, action="typing"
                )
                results = await self.formatter.search_youtube(song)
                for r in results:
                    await self.send_search_result_with_thumbnail(
                        context.bot, message.chat_id, r
                    )
                return
            await self.reply_text(message, "Invalid link. Please try again.")
            return

        enqueued = self.dj.enqueue(user.id, song)
        if not enqueued:
            await self.reply_text(message, "This song is already on your /list")
            return
        await self.reply_text(message, "Your song request has been added to your /list")
        await self.update_websockets()
        if self.formatter:
            await self.formatter.register_url(song)

    @staticmethod
    async def reply_text(
        message: MaybeInaccessibleMessage | None,
        text: str,
        show_error: bool = False,
        **kwargs,
    ) -> None:
        if not isinstance(message, Message):
            logger.error("Message inaccessible or None, cannot reply.")
            return
        try:
            await message.reply_text(text, **kwargs)
        except Exception as e:
            logger.error(f"Error sending message to {message.chat_id}: {e}")
            if show_error:
                await message.reply_text(f"Internal error: {e}")

    async def enqueue_from_callback(self, update: Update, song: str) -> None:
        assert update.callback_query
        user = update.callback_query.from_user
        self._register(user)
        if not self.dj.enqueue(user.id, song):
            return
        await self.reply_text(
            update.callback_query.message,
            "Your song request has been added to your /list",
        )
        if self.formatter:
            await self.formatter.register_url(song)

    @admin_only
    async def next(self, update: Update, context: CallbackContext) -> None:
        assert update.message is not None
        await self.next_impl(update.message)

    async def update_websockets(self, sockets=None) -> None:
        queue_json = self.dj.get_queue_json()
        for ws in sockets or self.websockets:
            try:
                await ws.send_str(queue_json)
            except Exception as e:
                logger.error(f"Error sending message to websocket: {e}")

    async def next_impl(self, message: Message) -> None:
        text, url = self.dj.next()
        if not url:
            await message.chat.send_message(text)
            return

        self.dj.peek_next()
        await self.update_websockets()

        song_button = InlineKeyboardButton(text="▶️ Play song", url=url)
        not_ready_button = btn("⏳ Singer not ready", "not_ready")
        next_button = btn("⬇️ Next singer", "next")
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

        await self.notify_next_singers(message.get_bot())

    async def notify_next_singers(self, bot) -> None:
        upcoming = self.dj.get_upcoming_singers()
        if not upcoming:
            return
        next_singer, ready = upcoming[0]
        if ready:
            await maybe(
                bot.send_message(
                    chat_id=next_singer,
                    text="You are next in the queue. Get ready to sing!",
                )
            )
        else:
            await maybe(
                bot.send_message(
                    chat_id=next_singer,
                    text="You are next in the queue. Add a song to your list to sing next!",
                )
            )

        for i, (singer, ready) in enumerate(upcoming[1:], start=1):
            if i == 1:
                condition = "the singer ahead of you is not ready"
            else:
                condition = f"the {i} singers ahead of you are not ready"
            await maybe(
                bot.send_message(
                    singer,
                    text=f"You may be called to sing next if {condition}",
                )
            )

    async def button_callback(self, update: Update, context: CallbackContext) -> None:
        await update.callback_query.answer()
        data = json.loads(update.callback_query.data)

        match action := data.get("a"):
            case "not_ready":
                if self.is_admin(update.callback_query.from_user.username):
                    await self.notready_impl(update)
            case "next":
                if self.is_admin(update.callback_query.from_user.username):
                    assert update.effective_message is not None
                    await self.next_impl(update.effective_message)
            case "noop":
                return
            case "add":
                await self.enqueue_from_callback(update, data.get("u", ""))
            case "move_up" | "move_down" | "delete":
                index = data.get("i", 0)
                uid = data.get("u", 0)
                await self.update_list(update, uid, action, int(index))

    async def update_list(
        self, update: Update, uid: int, action: str, index: int
    ) -> None:
        user = update.callback_query.from_user
        if uid != user.id and not self.is_admin(user.username):
            logger.warning(f"non-admin user {user} attempts to modify others' lists")
            return

        if action == "delete":
            action_taken = self.dj.remove_song(uid, index)
        else:
            action_taken = self.dj.move_song(uid, action, index)
        if not action_taken:
            return
        songs = self.dj.get_queue(uid)
        text = "Song list:" if songs else "Song list is empty"
        await update.callback_query.edit_message_text(
            text, reply_markup=self.generate_list_markup(songs, uid)
        )

    @admin_only
    async def admins(self, update: Update, context: CallbackContext) -> None:
        themselves = update.message.from_user.username
        await self.admins_impl(update, themselves)

    async def admins_impl(self, update: Update, themselves: str) -> None:
        words = update.message.text.removeprefix("/admins").strip().split()
        if themselves in (w[1:] for w in words):
            await self.reply_text(
                update.message, "You cannot promote or demote yourself"
            )
            return
        text = self.dj.admins_cmd(words)
        await self.reply_text(update.message, text)

    @admin_only
    async def notready(self, update: Update, context: CallbackContext) -> None:
        await self.notready_impl(update)

    async def notready_impl(self, update: Update) -> None:
        msgs = self.dj.notready()
        for chat_id, text in msgs:
            if chat_id is None:
                chat_id = update.effective_message.chat_id
            await update.get_bot().send_message(chat_id=chat_id, text=text)

    @admin_only
    async def remove(self, update: Update, context: CallbackContext) -> None:
        msg = self.dj.remove()
        await self.reply_text(update.message, msg)

    @admin_only
    async def remove_with_id(self, update: Update, context: CallbackContext) -> None:
        index = int(update.message.text.removeprefix("/remove"))
        msg = self.dj.remove_with_id(index)
        await self.reply_text(update.message, msg)

    async def clear(self, update: Update, context: CallbackContext) -> None:
        self._register(update.message.from_user)
        msg = self.dj.clear(update.message.chat_id)
        await self.reply_text(update.message, msg)

    @admin_only
    async def undo(self, update: Update, context: CallbackContext) -> None:
        for to, text in self.dj.undo():
            if to is None:
                await self.reply_text(update.message, text)
            else:
                await update.get_bot().send_message(chat_id=to, text=text)

    @admin_only
    async def reset(self, update: Update, context: CallbackContext) -> None:
        messages = self.dj.reset()
        for chat_id, text in messages:
            try:
                if chat_id is None:
                    await self.reply_text(update.message, text)
                else:
                    await update.get_bot().send_message(chat_id=chat_id, text=text)
            except Exception as e:
                logger.error(f"Error sending message to {chat_id}: {e}")

    @admin_only
    async def tell(self, update: Update, context: CallbackContext) -> None:
        words = update.message.text.split(None, 2)
        if len(words) != 3 or not words[1].isdigit():
            await self.reply_text(update.message, "Usage: /tell UID some text")
            return
        uid = int(words[1])
        await update.get_bot().send_message(chat_id=uid, text=words[2])

    @admin_only
    async def bcast(self, update: Update, context: CallbackContext) -> None:
        text = update.message.text.removeprefix("/bcast ")
        for uid in self.dj.names:
            await asyncio.sleep(0.1)
            try:
                await update.get_bot().send_message(chat_id=uid, text=text)
            except Exception:
                pass

    async def list_songs(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)

        command_id = update.message.text.removeprefix("/list")
        uid = int(command_id) if command_id else user.id

        songs = self.dj.get_queue(uid)
        text = "Song list:" if songs else "Song list is empty"
        await update.get_bot().send_message(
            chat_id=user.id,
            text=text,
            reply_markup=self.generate_list_markup(songs, uid),
        )

    @staticmethod
    def generate_list_markup(songs: list[SongInfo], uid: int) -> InlineKeyboardMarkup:
        # Build the list display with buttons
        keyboard = []
        empty_button_text = "⠀"  # Invisible separator character (U+2800)

        for index, item in enumerate(songs):
            move_up_text = "⬆️" if index > 0 else empty_button_text
            move_down_text = "⬇️" if index < len(songs) - 1 else empty_button_text
            buttons = [
                btn(move_up_text, "move_up", i=index, u=uid),
                btn(move_down_text, "move_down", i=index, u=uid),
                btn("❌", "delete", i=index, u=uid),
            ]
            keyboard.append([btn(f"{index+1}. {item.title}", "noop")])
            keyboard.append(buttons)
        return InlineKeyboardMarkup(keyboard)

    async def pause(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)
        await self.reply_text(update.message, self.dj.pause(user.id))
        await self.update_websockets()

    async def unpause(self, update: Update, context: CallbackContext) -> None:
        user = update.message.from_user
        self._register(user)
        await self.reply_text(update.message, self.dj.unpause(user.id))
        await self.update_websockets()

    async def list_all_queues(self, update: Update, context: CallbackContext) -> None:
        is_admin = self.is_admin(update.message.from_user.username)
        text = self.dj.show_all_queues(
            requester=update.message.chat.id, is_admin=is_admin
        )
        await self.reply_text(
            update.message,
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
            show_error=True,
        )

    def is_admin(self, username: str) -> bool:
        return self.dj.is_admin(username)


async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(f"Exception while handling an update ({update}): {context.error}")


def main() -> None:
    application = Application.builder().token(TOKEN).build()
    bot = KaraokeBot(shelve.open("bot"))

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.request_song)
    )

    application.add_handler(CommandHandler("next", bot.next))
    application.add_handler(CommandHandler("remove", bot.remove))
    application.add_handler(CommandHandler("notready", bot.notready))
    application.add_handler(CommandHandler("clear", bot.clear))
    application.add_handler(CommandHandler("list", bot.list_songs))
    application.add_handler(CommandHandler("listall", bot.list_all_queues))
    application.add_handler(CommandHandler("queue", bot.list_all_queues))
    application.add_handler(CommandHandler("pause", bot.pause))
    application.add_handler(CommandHandler("unpause", bot.unpause))
    application.add_handler(CommandHandler("reset", bot.reset))
    application.add_handler(CommandHandler("admins", bot.admins))
    application.add_handler(CommandHandler("undo", bot.undo))
    application.add_handler(CommandHandler("tell", bot.tell))
    application.add_handler(CommandHandler("bcast", bot.bcast))

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^/remove\d+$"),
            lambda update, context: bot.remove_with_id(update, context),
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^/list\d+$"),
            lambda update, context: bot.list_songs(update, context),
        )
    )

    application.add_handler(CallbackQueryHandler(bot.button_callback))

    application.add_error_handler(error_handler)

    async def websocket_handler(request):
        print("running websocket_handler")
        ws = web.WebSocketResponse()
        print("preparing request")
        await ws.prepare(request)
        bot.websockets.append(ws)
        await bot.update_websockets([ws])  # Send initial queue state

        try:
            async for msg in ws:
                print("Received message:", msg)
        finally:
            bot.websockets.remove(ws)
            await ws.close()
        return ws

    async def static_handler(request):
        return web.FileResponse("queue.html")

    async def init_http_server():
        app = web.Application()
        app.router.add_get("/ws", websocket_handler)
        app.router.add_get("/", static_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("HTTP server running on http://0.0.0.0:8080")
        while True:
            await asyncio.sleep(3600)  # Keep the server running

    # Run both the Telegram bot and the HTTP server concurrently
    async def run():
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await init_http_server()

    asyncio.run(run())


if __name__ == "__main__":
    main()
