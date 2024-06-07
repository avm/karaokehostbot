from bot import KaraokeBot
from youtube import VideoFormatter
from unittest.mock import AsyncMock
from telegram import Update, Message, User
from telegram.constants import ParseMode
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
    bot = KaraokeBot(
        {
            "queue": [1],
            "user:1": ["https://youtu.be/xyzzy42"],
            "names": {1: "@user_name"},
        },
        admins=["admin_user"],
    )

    admin = User(id=2, first_name="Admin", is_bot=False, username="admin_user")
    message = Message(
        from_user=admin,
        message_id=100,
        date=datetime.datetime.now(),
        chat=admin,
        text="/next",
    )
    tgbot = AsyncMock()

    message.set_bot(tgbot)
    update = Update(update_id=200, message=message)

    await bot.next(update, context=None)
    for call in tgbot.send_message.call_args_list:
        if call.kwargs["parse_mode"] == ParseMode.MARKDOWN_V2:
            assert call.kwargs["text"] == (
                "Singer: @user\\_name\nSong: https://youtu\\.be/xyzzy42\n\n"
                "_Next in queue: _@user\\_name"
            )


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
