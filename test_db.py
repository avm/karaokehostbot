from bot import DJ
from copy import deepcopy


class CopyingDict:
    def __init__(self):
        self.data = {}

    def __setitem__(self, key, value):
        self.data[key] = deepcopy(value)

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self, key):
        del self.data[key]

    def __contains__(self, key):
        return key in self.data

    def get(self, key, default=None):
        return self.data.get(key, default)


def test_storage():
    db = CopyingDict()
    dj = DJ(db)
    dj.enqueue(1, "avm", "Elvis")
    print(db.data)
    assert db["user:1"] == ["Elvis"]
    assert db["new_users"] == [1]
    assert db["names"] == {1: "avm"}
    dj.enqueue(2, "alice", "Amanda Palmer")
    dj.next()  # Elvis
    assert db["queue"] == [1]
    dj.next()  # Amanda Palmer
    assert db["queue"] == [1, 2]
    assert db["new_users"] == []
    dj.enqueue(2, "alice", "Nickelback")
    dj.next()  # Nickelback
    assert db["queue"] == [2]
    dj.enqueue(1, "avm", "Doors")
    assert db["new_users"] == [1]
    assert db["queue"] == [2]
    assert db["user:1"] == ["Doors"]
    assert db["user:2"] == []
    dj.remove()
    assert db["queue"] == []
    assert "user:2" not in db
