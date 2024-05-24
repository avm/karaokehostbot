from bot import KaraokeBot
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
