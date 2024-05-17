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

load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot API token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Admin user configuration
ADMIN_USERNAMES = os.environ.get("ADMIN_USERNAMES", "").split(",")


class DJ:
    def __init__(self, db):
        self.db = db
        self.names: dict[int, str] = self.db.get("names", {})
        self.queue: list[str] = self.db.get("queue", [])
        self.new_users: list[str] = self.db.get("new_users", [])
        self.user_song_lists: dict[int, list[str]] = self.load_song_lists()
        self.current: tuple[int, str] = self.db.get("current")

    def save_global(self):
        self.db["names"] = self.names
        self.db["queue"] = self.queue
        self.db["new_users"] = self.new_users
        self.db["current"] = self.current

    def load_song_lists(self):
        return {user: self.load_song_list(user) for user in self.queue + self.new_users}

    def _song_list_key(self, user: int) -> str:
        return f"user:{user}"

    def load_song_list(self, user: int) -> list[str] | None:
        return self.db.get(self._song_list_key(user))

    def save_song_list(self, user: int) -> None:
        queue = self.user_song_lists.get(user)
        key = self._song_list_key(user)
        if queue is None and key in self.db:
            del self.db[key]
        elif queue is not None:
            self.db[key] = queue

    def _name(self, chat_id: int) -> str:
        return self.names.get(chat_id, str(chat_id))

    def clear(self, user: int) -> str:
        if self.user_song_lists.get(user):
            self.user_song_lists[user].clear()
            self.save_song_list(user)
            return "Your song list has been cleared"
        return "You don't have any songs in your list"

    def remove(self) -> str:
        if self.current is None:
            return "No current singer"
        user, _ = self.current
        if user in self.queue:
            self.queue.remove(user)
            self.save_global()
            if user in self.user_song_lists:
                del self.user_song_lists[user]
                self.save_song_list(user)
            return f"{self._name(user)} removed from the queue"
        return f"{self._name(user)} was not on the queue :-o"

    def show_queue(self, user: int) -> str:
        their_queue = self.user_song_lists.get(user, [])
        return f"{self._name(user)}:\n" + (
            "\n".join(their_queue) if their_queue else "(queue empty)"
        )

    def show_all_queues(self) -> str:
        return "All queues:\n\n" + "\n\n".join(
            self.show_queue(u) for u in self.new_users + self.queue
        )

    def enqueue(self, user: int, name: str, link: str) -> list[str]:
        self.names[user] = name
        if user in self.user_song_lists:
            self.user_song_lists[user].append(link)
        else:
            self.user_song_lists[user] = [link]
            self.new_users.append(user)
            self.save_global()
        self.save_song_list(user)

    def next(self) -> str:
        ready = self._get_ready_singer()
        if ready is None:
            self.save_global()
            return "The queue is empty"
        singer, song = ready
        self.queue.append(singer)
        self.current = (singer, song)
        self.save_global()
        return f"Next up: {song} (by {self._name(singer)})\nCommands: /next /listall /remove"

    def _pop_next_singer(self) -> int | None:
        if self.new_users:
            return self.new_users.pop(0)
        if self.queue:
            return self.queue.pop(0)
        return None

    def _get_ready_singer(self) -> tuple[str, str] | None:
        """Remove singers at `position` until we get to one who has songs in their queue"""
        return_value = None
        while singer := self._pop_next_singer():
            their_queue = self.user_song_lists.get(singer)
            if not their_queue:
                self.user_song_lists.pop(singer, None)
                self.save_song_list(singer)
                continue
            return_value = (singer, their_queue.pop(0))
            self.save_song_list(singer)
            break

        return return_value


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
