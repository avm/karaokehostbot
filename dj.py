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
