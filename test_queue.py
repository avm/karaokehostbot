from bot import DJ


def format_next(name, song):
    return f"Next up: {song} (by {name})\nCommands: /next /listall /remove"


def test_queue():
    dj = DJ({})
    dj.enqueue(1, "avm", "01")
    dj.enqueue(1, "avm", "03")
    dj.enqueue(2, "alice", "02")
    dj.enqueue(2, "alice", "04")
    assert dj.next() == format_next("avm", "01")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("avm", "03")
    dj.enqueue(3, "guest1", "01")
    dj.enqueue(3, "guest1", "02")
    assert dj.next() == format_next("guest1", "01")
    dj.enqueue(3, "guest1", "03")
    dj.enqueue(4, "guest2", "04")
    assert dj.next() == format_next("guest2", "04")
    assert dj.next() == format_next("alice", "04")
    assert dj.next() == format_next("guest1", "02")
    assert dj.next() == format_next("guest1", "03")
    assert dj.next() == "The queue is empty"


def test_clear():
    dj = DJ({})
    dj.enqueue(1, "avm", "01")
    dj.enqueue(1, "avm", "03")
    dj.enqueue(2, "alice", "02")
    dj.enqueue(2, "alice", "04")
    assert dj.next() == format_next("avm", "01")
    dj.clear(1)
    dj.enqueue(1, "avm", "Elvis")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == format_next("alice", "04")


def test_empty_queue():
    dj = DJ({})
    dj.enqueue(1, "avm", "01")
    dj.enqueue(2, "alice", "02")
    dj.enqueue(2, "alice", "03")
    dj.enqueue(2, "alice", "05")
    assert dj.next() == format_next("avm", "01")
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("alice", "03")
    dj.enqueue(1, "avm", "04")
    assert dj.next() == format_next("avm", "04")
    assert dj.next() == format_next("alice", "05")


def test_remove():
    dj = DJ({})
    dj.enqueue(1, "avm", "01")
    dj.enqueue(1, "avm", "03")
    dj.enqueue(2, "alice", "02")
    dj.enqueue(2, "alice", "04")
    dj.enqueue(2, "alice", "05")
    assert dj.next() == format_next("avm", "01")
    assert dj.remove() == "avm removed from the queue"
    assert dj.next() == format_next("alice", "02")
    assert dj.next() == format_next("alice", "04")
    dj.enqueue(1, "avm", "Elvis")
    assert dj.next() == format_next("avm", "Elvis")
    assert dj.next() == format_next("alice", "05")
