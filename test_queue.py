from dj import DJ


def format_next(name, song):
    return f"Next up: {song} (by {name})\nCommands: /next /listall /remove /notready"


def test_queue():
    dj = DJ({})
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
    assert dj.next() == "The queue is empty"


def test_clear():
    dj = DJ({})
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


def test_empty_queue():
    dj = DJ({})
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
    dj = DJ({})
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
    dj.enqueue(1, "Elvis")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == format_next("alice", "05")


def test_pause():
    dj = DJ({})
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
        (None, "avm was paused"),
        (None, format_next("guest1", "01")),
    ]
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
    assert dj.next() == "The queue is empty"


def test_listall():
    dj = DJ({})
    dj.register(1, "avm")
    dj.register(2, "alice")
    dj.register(3, "avi")
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    dj.enqueue(2, "02")
    dj.enqueue(2, "04")
    dj.enqueue(3, "AA")
    dj.enqueue(3, "BB")
    dj.pause(2)
    assert dj.show_all_queues() == "\n\n".join(
        (
            "All queues:",
            "avm:\n01\n03",
            "alice:\n02\n04",
            "avi:\nAA\nBB",
            "Paused users: alice",
        )
    )


def test_pause_enqueue():
    dj = DJ({})
    dj.pause(1)
    dj.enqueue(1, "01")
    dj.enqueue(1, "03")
    assert dj.next() == "The queue is empty"
    dj.unpause(1)
    assert dj.next() == format_next("1", "01")
