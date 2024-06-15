from bot import KaraokeBot
from youtube import VideoFormatter
from unittest.mock import AsyncMock
from telegram import Update, Message, User
import datetime
import pytest


@pytest.mark.asyncio
async def test_request():
    bot = KaraokeBot({}, ["admin_user"])
    singer1 = User(id=1, first_name="Joe", is_bot=False, username="singer1")
    message = Message(
        from_user=singer1,
        message_id=100,
        date=datetime.datetime.now(),
        chat=singer1,
        text="https://my.favorite.site/song1",
    )
    tgbot = AsyncMock()

    message.set_bot(tgbot)
    update = Update(update_id=200, message=message)

    await bot.request_song(update, context=None)
    assert (
        tgbot.send_message.call_args.kwargs["text"]
        == "Your song request has been added to your list."
    )


@pytest.mark.asyncio
async def test_markdown():
    db = {
        "queue": [1],
        "user:1": ["https://youtu.be/xyzzy42"],
        "user:2": [],
        "names": {1: "@user_name", 2: "@someone_else"},
    }
    bot = KaraokeBot(
        db=db,
        admins=["admin_user"],
    )

    tgbot = AsyncMock()

    admin = User(id=2, first_name="Admin", is_bot=False, username="admin_user")
    admin.set_bot(tgbot)

    def make_message(message_id, text):
        msg = Message(
            from_user=admin,
            message_id=message_id,
            date=datetime.datetime.now(),
            chat=admin,
            text=text,
        )
        msg.set_bot(tgbot)
        return msg

    update = Update(update_id=200, message=make_message(100, "/next"))
    await bot.next(update, context=None)

    bot.dj.new_users = [2]
    bot.dj.user_song_lists[2].append("https://youtu.be/fizzbuzz")

    update = Update(update_id=201, message=make_message(101, "/next"))
    await bot.next(update, context=None)

    assert [call.kwargs["text"] for call in tgbot.send_message.call_args_list] == [
        "Singer: @user\\_name\nSong: https://youtu\\.be/xyzzy42",
        "Singer: @someone\\_else\nSong: https://youtu\\.be/fizzbuzz\n\n"
        "_Next in queue:_ @user\\_name",
    ]


def test_youtube():
    vf = VideoFormatter(
        "", {"youtube:xxx": "Some [] text", "youtube:yyy": "Some (more)"}
    )
    assert (
        vf.tg_format("https://youtu.be/xxx").escaped_text()
        == r"[Some \[\] text](https://youtu.be/xxx)"
    )
    assert (
        vf.tg_format("https://youtu.be/yyy").escaped_text()
        == r"[Some \(more\)](https://youtu.be/yyy)"
    )
