from collections import defaultdict
from youtube import VideoFormatter, SongInfo
from gettext import ngettext
from telegram_markdown_text import MarkdownText
from collections import namedtuple
from party import Party
import json

QueueEntry = namedtuple("QueueEntry", ["singer", "is_ready"])


class DJ:
    def __init__(self, party: Party, formatter: VideoFormatter | None = None):
        self.party = party
        self.formatter = formatter
        self.admins: set[str] = self.party.get("admins")
        self.names: dict[int, str] = self.party.get("names", {})
        self.queue: list[int] = self.party.get("queue", [])
        self.new_users: list[int] = self.party.get("new_users", [])
        self.paused: set[int] = self.party.get("paused", set())
        self.user_song_lists: dict[int, list[str]] = self.load_song_lists()
        self.current: tuple[int, str] = self.party.get("current")
        self.undo_list: list[tuple[str, int]] = self.party.get("undo_list", [])

    def save_global(self):
        self.party["admins"] = self.admins
        self.party["names"] = self.names
        self.party["queue"] = self.queue
        self.party["new_users"] = self.new_users
        self.party["current"] = self.current
        self.party["paused"] = self.paused
        self.party["undo_list"] = self.undo_list

    def is_admin(self, user: str) -> bool:
        return user in self.admins

    def admins_cmd(self, modifications: list[str]):
        if not modifications:
            return self._format_admins()
        for mod in modifications:
            if mod.startswith("+"):
                self.admins.add(mod[1:])
            elif mod.startswith("-"):
                self.admins.remove(mod[1:])
            else:
                return "Invalid modification: " + mod
        self.save_global()
        return self._format_admins()

    def _format_admins(self) -> str:
        return f"Admins: @{', @'.join(sorted(self.admins))}"

    def load_song_lists(self):
        loaded = {user: self.load_song_list(user) for user in self._known_users()}
        return defaultdict(list, loaded)

    def _song_list_key(self, user: int) -> str:
        return f"user:{user}"

    def load_song_list(self, user: int) -> list[str]:
        return self.party.load_song_list(user)

    def save_song_list(self, user: int) -> None:
        self.party.save_song_list(user, self.user_song_lists.get(user, []))

    def _name(self, chat_id: int) -> str:
        return self.names.get(chat_id, str(chat_id))

    def clear(self, user: int) -> str:
        if self.user_song_lists.get(user):
            self.user_song_lists[user].clear()
            self.save_song_list(user)
            return "Your song list has been cleared"
        return "You don't have any songs in your list"

    def reset(self) -> list[tuple[int | None, str]]:
        self.queue.clear()
        self.new_users.clear()
        self.paused.clear()
        messages: list[tuple[int | None, str]] = []
        for user, song_list in self.user_song_lists.items():
            if not song_list:
                continue
            messages.append(
                (
                    user,
                    "Your song list has been cleared because the queue was reset",
                )
            )
            song_list.clear()
            self.save_song_list(user)
        self.user_song_lists.clear()
        self.save_global()
        messages.append((None, "The queue has been reset"))
        return messages

    def undo(self) -> list[tuple[int | None, str]]:
        if not self.undo_list:
            return [(None, "Nothing to undo")]
        action, user = self.undo_list.pop()
        if action == "paused":
            messages: list[tuple[int | None, str]] = [
                (None, f"{self._name(user)} is now unpaused")
            ]
            if user not in self.paused:
                return messages
            self.paused.remove(user)
            if user not in (self.new_users + self.queue):
                self.queue.append(user)
            self.save_global()
            return messages + [
                (user, "You are now unpaused"),
            ]
        return [(None, "Unknown undo action")]

    def notready(self) -> list[tuple[int | None, str]]:
        if self.current is None:
            return [(None, "No current singer")]
        user, song = self.current
        self._unget_song(user, song)
        if user in self.paused:
            return []
        self.paused.add(user)
        if user in self.queue:
            self.queue.remove(user)
        self.undo_list.append(("paused", user))
        messages = [
            (
                user,
                "You were paused because you missed your turn. "
                "Use /unpause when you are ready!",
            ),
            (None, f"{self._name(user)} was paused (/undo)"),
        ]
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
        return self.remove_with_id(user)

    def remove_with_id(self, user: int) -> str:
        if user in self._known_users():
            remove_if_present(self.new_users, user)
            remove_if_present(self.queue, user)
            remove_if_present(self.paused, user)
            self.save_global()
            if user in self.user_song_lists:
                del self.user_song_lists[user]
                self.save_song_list(user)
            return f"{self._name(user)} removed from the queue"
        return f"{self._name(user)} was not on the queue :-o"

    def _song_info(self, url: str) -> SongInfo:
        if self.formatter:
            return self.formatter.song_info(url)
        return SongInfo(title=url, duration=0, url=url)

    def _format_song(self, url: str) -> MarkdownText:
        if self.formatter:
            return self.formatter.tg_format(url)
        return MarkdownText(url)

    def _format_singer(self, singer: int) -> MarkdownText:
        return MarkdownText(self._name(singer))

    def show_queue(
        self, user: int, show_songs: bool = False, show_remove: bool = False
    ) -> str:
        their_queue = self.user_song_lists.get(user)
        remove = "" if not show_remove else f" /remove{user} /list{user}"
        user_str = f"{self._format_singer(user)}{remove}:\n"
        if not their_queue:
            return user_str + r"\(queue empty\)"
        if not show_songs:
            n = len(their_queue)
            return user_str + ngettext(r"\(%d song\)", r"\(%d songs\)", n) % n
        return user_str + "\n".join(
            self._format_song(song).escaped_text() for song in their_queue
        )

    def get_queue(self, user: int) -> list[SongInfo]:
        their_queue = self.user_song_lists.get(user)
        return [self._song_info(song) for song in their_queue or []]

    def remove_song(self, user: int, index: int) -> bool:
        their_queue = self.user_song_lists.get(user)
        if not their_queue:
            return False
        try:
            their_queue.pop(index)
            self.save_song_list(user)
        except IndexError:
            return False
        return True

    def move_song(self, user: int, action: str, index: int) -> bool:
        their_queue = self.user_song_lists.get(user)
        if not their_queue:
            return False
        if action == "move_up":
            if index <= 0:
                return False
            idx = index - 1
        else:
            if index >= len(their_queue) - 1:
                return False
            idx = index
        try:
            their_queue[idx : idx + 2] = their_queue[idx + 1], their_queue[idx]
            self.save_song_list(user)
        except IndexError:
            return False
        return True

    def show_all_queues(
        self, requester: int | None = None, is_admin: bool = False
    ) -> str:
        all_queues = self.new_users + self.queue
        queues_str = (
            (
                "All singers:\n\n"
                + "\n\n".join(
                    self.show_queue(
                        u,
                        show_songs=(is_admin or (u == requester)),
                        show_remove=is_admin,
                    )
                    for u in all_queues
                )
            )
            if all_queues
            else "No active singers"
        )
        paused_str = (
            "Paused singers: "
            + ", ".join(
                self._format_singer(user).escaped_text() for user in self.paused
            )
            if self.paused
            else "No paused singers"
        )
        return f"{queues_str}\n\n{paused_str}"

    def register(self, user: int, name: str) -> None:
        self.names[user] = name

    def _known_users(self) -> set[int]:
        return self.paused.union(self.new_users).union(self.queue)

    def enqueue(self, user: int, link: str) -> bool:
        song_list = self.user_song_lists[user]
        if link in song_list:
            return False
        song_list.append(link)
        self.save_song_list(user)
        if user not in self._known_users():
            self.new_users.append(user)
            self.save_global()
        return True

    def peek_next(self) -> int | None:
        if len(self.new_users) + len(self.queue) <= 2:
            return None
        next = self._pop_next_singer()
        if next is not None:
            # save them a place at the front
            self.new_users.insert(0, next)
            self.save_global()
        return next

    def get_upcoming_singers(self) -> list[QueueEntry]:
        all_queues = self.new_users + self.queue
        result: list[QueueEntry] = []
        for singer in all_queues:
            if singer in self.paused:
                continue
            their_queue = self.user_song_lists.get(singer)
            ready = bool(their_queue)
            result.append(QueueEntry(singer, ready))
            if ready or len(result) >= 3:
                break
        return result

    def next(self) -> tuple[str, str]:
        ready = self._get_ready_singer()
        if ready is None:
            self.save_global()
            return ("The queue is empty", "")
        singer, song = ready
        self.queue.append(singer)
        self.current = (singer, song)
        self.save_global()
        return (
            f"Singer: {self._format_singer(singer)}\n"
            f"Song: {self._format_song(song)}",
            song,
        )

    def get_queue_json(self) -> str:
        current_singer, current_song = self.current or (None, None)
        data = None
        if current_song and self.formatter:
            data = self.formatter.get_data(current_song)
        all_queues = self.new_users + self.queue
        queue = {
            "current": {
                "singer": self._name(current_singer) if current_singer else "No singer",
                "title": data.title if data else current_song or "",
                "url": data.url if data else current_song or "",
            },
            "queue": [
                {"singer": self._name(singer), "paused": singer in self.paused}
                for singer in all_queues
            ],
        }
        return json.dumps(queue, ensure_ascii=False)

    def _pop_next_singer(self) -> int | None:
        if self.new_users:
            return self.new_users.pop(0)
        if self.queue:
            return self.queue.pop(0)
        return None

    def _get_ready_singer(self) -> tuple[int, str] | None:
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


def remove_if_present(queue: list[int] | set[int], user: int) -> None:
    if user in queue:
        queue.remove(user)
