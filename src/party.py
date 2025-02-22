class Party:
    def __init__(self, db, id: int = 0):
        self.db = db
        self.id: int = id

    def _getkey(self, key: str) -> str:
        if self.id == 0:
            return key
        return f"party{self.id}:{key}"

    def __getattr__(self, name):
        return getattr(self.db, name)

    def __contains__(self, key):
        return key in self.db

    def __getitem__(self, key):
        return self.db[self._getkey(key)]

    def __setitem__(self, key, value):
        self.db[self._getkey(key)] = value

    def __delitem__(self, key):
        del self.db[self._getkey(key)]

    def get(self, key, default=None):
        return self.db.get(self._getkey(key), default)
