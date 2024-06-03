from collections import defaultdict
from youtube import VideoFormatter
from gettext import ngettext
from telegram.helpers import escape_markdown
from telegram_markdown_text import MarkdownText


class DJ:
    def __init__(self, db, formatter: VideoFormatter | None = None):
        self.db = db
        self.formatter = formatter
        self.names: dict[int, str] = self.db.get("names", {})
        self.queue: list[str] = self.db.get("queue", [])
        self.new_users: list[str] = self.db.get("new_users", [])
        self.paused: set[int] = self.db.get("paused", set())
        self.user_song_lists: dict[int, list[str]] = self.load_song_lists()
        self.current: tuple[int, str] = self.db.get("current")

    def save_global(self):
        self.db["names"] = self.names
        self.db["queue"] = self.queue
        self.db["new_users"] = self.new_users
        self.db["current"] = self.current
        self.db["paused"] = self.paused

    def load_song_lists(self):
        loaded = {user: self.load_song_list(user) for user in self._known_users()}
        return defaultdict(list, loaded)

    def _song_list_key(self, user: int) -> str:
        return f"user:{user}"

    def load_song_list(self, user: int) -> list[str]:
        return self.db.get(self._song_list_key(user), [])

    def save_song_list(self, user: int) -> None:
        queue = self.user_song_lists.get(user)
        key = self._song_list_key(user)
        if (not queue) and key in self.db:
            del self.db[key]
        elif queue:
            self.db[key] = queue

    def _name(self, chat_id: int) -> str:
        return self.names.get(chat_id, str(chat_id))

    def clear(self, user: int) -> str:
        if self.user_song_lists.get(user):
            self.user_song_lists[user].clear()
            self.save_song_list(user)
            return "Your song list has been cleared"
        return "You don't have any songs in your list"

    def notready(self) -> list[tuple[int, str]]:
        if self.current is None:
            return [(None, "No current singer")]
        messages: list[tuple[int, str]] = []
        user, song = self.current
        self._unget_song(user, song)
        if user not in self.paused:
            self.paused.add(user)
            if user in self.queue:
                self.queue.remove(user)
            messages.append(
                (
                    user,
                    "You were paused because you missed your turn. "
                    "Use /unpause when you are ready!",
                )
            )
            messages.append((None, f"{self._name(user)} was paused"))
        messages.append((None, self.next()))
        return messages

    def pause(self, user: int) -> str:
        if user in self.paused:
            return "You are already paused"
        self.paused.add(user)
        self.save_global()
        return "OK, you are now paused"

    def unpause(self, user) -> str:
        if user not in self.paused:
            return "You are not paused"
        self.paused.remove(user)
        if user not in (self.new_users + self.queue):
            self.new_users.append(user)
        self.save_global()
        return "OK, you are now unpaused"

    def _unget_song(self, user: int, song: str) -> None:
        self.user_song_lists[user].insert(0, song)
        self.save_song_list(user)

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

    def _format_song(self, song: str) -> MarkdownText:
        if self.formatter:
            return self.formatter.tg_format(song)
        return MarkdownText(song)

    def show_queue(self, user: int, show_songs: bool = False) -> str:
        their_queue = self.user_song_lists.get(user)
        user_str = escape_markdown(f"{self._name(user)}:\n", version=2)
        if not their_queue:
            return user_str + r"\(queue empty\)"
        if not show_songs:
            n = len(their_queue)
            return user_str + ngettext(r"\(%d song\)", r"\(%d songs\)", n) % n
        return user_str + "\n".join(self._format_song(song).escaped_text() for song in their_queue)

    def show_all_queues(
        self, requester: int | None = None, is_admin: bool = False
    ) -> str:
        all_queues = self.new_users + self.queue
        queues_str = (
            (
                "All queues:\n\n"
                + "\n\n".join(
                    self.show_queue(u, (is_admin or (u == requester)))
                    for u in all_queues
                )
            )
            if all_queues
            else "No active queues"
        )
        paused_str = (
            "Paused users: " + ", ".join(self._name(user) for user in self.paused)
            if self.paused
            else "No paused users"
        )
        return f"{queues_str}\n\n{paused_str}"

    def register(self, user: int, name: str) -> None:
        self.names[user] = name

    def _known_users(self) -> set[int]:
        return self.paused.union(self.new_users).union(self.queue)

    def enqueue(self, user: int, link: str) -> list[str]:
        self.user_song_lists[user].append(link)
        self.save_song_list(user)
        if user not in self._known_users():
            self.new_users.append(user)
            self.save_global()

    def next(self) -> tuple[str, str]:
        ready = self._get_ready_singer()
        if ready is None:
            self.save_global()
            return ("The queue is empty", None)
        singer, song = ready
        self.queue.append(singer)
        self.current = (singer, song)
        self.save_global()
        return (
            f"Singer: {escape_markdown(self._name(singer))}\n"
            f"Song: {self._format_song(song)}",
            song,
        )

    def _pop_next_singer(self) -> int | None:
        if self.new_users:
            return self.new_users.pop(0)
        if self.queue:
            return self.queue.pop(0)
        return None

    def _get_ready_singer(self) -> tuple[str, str] | None:
        """Remove singers from the queue until we get to one who has songs in their queue"""
        return_value = None
        while singer := self._pop_next_singer():
            if singer in self.paused:
                continue
            their_queue = self.user_song_lists.get(singer)
            if not their_queue:
                self.user_song_lists.pop(singer, None)
                self.save_song_list(singer)
                continue
            return_value = (singer, their_queue.pop(0))
            self.save_song_list(singer)
            break

        return return_value
