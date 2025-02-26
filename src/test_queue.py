from dj import DJ
from party import Party
from telegram_markdown_text import MarkdownText
from youtube import SongInfo


def format_next(name, song, url=None):
    return (
        f"Singer: {name}\n" f"Song: {song}",
        url or song,
    )


empty_queue = ("The queue is empty", "")


def test_queue():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    assert dj.next() == format_next("avm", "01")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("avm", "03")
    dj.register(3, "guest1")
    dj.enqueue(3, "01")
    dj.enqueue(3, "02")
    assert dj.next() == format_next("guest1", "01")
    dj.enqueue(3, "03")
    dj.register(4, "guest2")
    dj.enqueue(4, "04")
    assert dj.next() == format_next("guest2", "04")
    assert dj.next() == format_next("alice", "04")
    assert dj.next() == format_next("guest1", "02")
    assert dj.next() == format_next("guest1", "03")
    assert dj.next() == empty_queue


def test_duplicate():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.enqueue(1, "01")
    assert dj.enqueue(1, "01") == False


def test_clear():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    assert dj.next() == format_next("avm", "01")
    dj.clear(1)
    dj.enqueue(1, "Elvis")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == format_next("alice", "04")


def test_reset():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    assert dj.get_queue(1) == [
        SongInfo(title="01", url="01", duration=0),
        SongInfo(title="03", url="03", duration=0),
    ]
    assert dj.next() == format_next("avm", "01")
    assert dj.reset() == [
        (1, "Your song list has been cleared because the queue was reset"),
        (2, "Your song list has been cleared because the queue was reset"),
        (None, "The queue has been reset"),
    ]
    assert dj.get_queue(1) == []
    dj.register(3, "guest1")
    dj.enqueue(3, "01")
    dj.enqueue(3, "02")
    assert dj.next() == format_next("guest1", "01")
    assert dj.next() == format_next("guest1", "02")
    assert dj.next() == empty_queue


def test_empty_queue():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(2, "02")
    dj.enqueue(2, "03")
    dj.enqueue(2, "05")
    assert dj.next() == format_next("avm", "01")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("alice", "03")
    dj.enqueue(1, "04")
    assert dj.next() == format_next("avm", "04")
    assert dj.next() == format_next("alice", "05")


def test_remove():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    dj.enqueue(2, "05")
    assert dj.next() == format_next("avm", "01")
    assert dj.remove() == "avm removed from the queue"
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("alice", "04")
    assert dj.remove_with_id(2) == "alice removed from the queue"
    dj.enqueue(1, "Elvis")
    assert dj.remove_with_id(1) == "avm removed from the queue"
    dj.enqueue(1, "Elvis")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == empty_queue


def test_pause():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    assert dj.next() == format_next("avm", "01")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("avm", "03")
    dj.register(3, "guest1")
    dj.enqueue(3, "01")
    dj.enqueue(3, "02")
    assert dj.notready() == [
        (
            1,
            "You were paused because you missed your turn. "
            "Use /unpause when you are ready!",
        ),
        (None, "avm was paused (/undo)"),
    ]
    assert dj.next() == format_next("guest1", "01")
    dj.enqueue(3, "03")
    dj.register(4, "guest2")
    dj.enqueue(4, "04")
    assert dj.next() == format_next("guest2", "04")
    assert dj.next() == format_next("alice", "04")
    dj.enqueue(1, "Elvis")
    assert dj.next() == format_next("guest1", "02")
    assert dj.unpause(1) == "OK, you are now unpaused"
    assert dj.next() == format_next("avm", "03")
    assert dj.next() == format_next("guest1", "03")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == empty_queue


def test_listall():
    dj = DJ(Party({}, 0))
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.register(3, "@avi_avi")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    dj.enqueue(3, "AA")
    dj.enqueue(3, "BB")
    dj.clear(2)
    dj.pause(2)
    assert dj.show_all_queues() == "\n\n".join(
        (
            "All queues:",
            "avm:\n\\(2 songs\\)",
            "alice:\n\\(queue empty\\)",
            "@avi\\_avi:\n\\(2 songs\\)",
            "Paused users: alice",
        )
    )
    assert dj.show_all_queues(requester=3) == "\n\n".join(
        (
            "All queues:",
            "avm:\n\\(2 songs\\)",
            "alice:\n\\(queue empty\\)",
            "@avi\\_avi:\nAA\nBB",
            "Paused users: alice",
        )
    )
    dj.pause(3)
    assert dj.show_all_queues(is_admin=True) == "\n\n".join(
        (
            "All queues:",
            "avm /remove1:\n01\n03",
            "alice /remove2:\n\\(queue empty\\)",
            "@avi\\_avi /remove3:\nAA\nBB",
            "Paused users: alice, @avi\\_avi",
        )
    )


def test_pause_enqueue():
    dj = DJ(Party({}, 0))
    dj.pause(1)
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    assert dj.next() == empty_queue
    dj.unpause(1)
    assert dj.next() == format_next("1", "01")


class DummyFormatter(dict):
    def tg_format(self, url: str) -> MarkdownText:
        return MarkdownText(self.get(url, url))


def test_formatter():
    fmt = DummyFormatter({"01": "Baseballs — Umbrella"})
    dj = DJ(Party({}, 0), formatter=fmt)
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    assert dj.next() == format_next("avm", "Baseballs — Umbrella", "01")
    assert dj.next() == format_next("avm", "03")
