from bot import KaraokeBot
from youtube import VideoFormatter, SongInfo
from unittest.mock import AsyncMock
from telegram import Update, Message, CallbackQuery, Chat
import datetime
import pytest


@pytest.mark.asyncio
async def test_request():
    bot = KaraokeBot({}, ["admin_user"])
    singer1 = Chat(id=1, first_name="Joe", username="singer1", type="private")
    singer2 = Chat(id=2, first_name="Jane", last_name="Eyre", type="private")

    tgbot = AsyncMock()

    def make_message(message_id, from_user, text):
        msg = Message(
            from_user=from_user,
            message_id=message_id,
            date=datetime.datetime.now(),
            chat=from_user,
            text=text,
        )
        msg.set_bot(tgbot)
        return msg

    message = make_message(100, singer1, "https://my.favorite.site/song1")
    update = Update(update_id=200, message=message)
    await bot.request_song(update, context=None)

    message = make_message(101, singer2, "https://my.favorite.site/song2")
    update = Update(update_id=201, message=message)
    await bot.request_song(update, context=None)

    update = Update(update_id=202, message=message)
    await bot.request_song(update, context=None)

    assert [call.kwargs["text"] for call in tgbot.send_message.call_args_list] == [
        "Your song request has been added to your list.",
        "Your song request has been added to your list.",
        "This song is already on your /list",
    ]


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

    admin = Chat(id=2, first_name="Admin", username="admin_user", type="private")
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

    update = Update(update_id=202, message=make_message(102, "/list"))
    update.set_bot(tgbot)
    await bot.list_songs(update, context=None)

    assert [call.kwargs["text"] for call in tgbot.send_message.call_args_list] == [
        "Singer: @user\\_name\nSong: https://youtu\\.be/xyzzy42",
        "You are next in the queue. Add a song to your list to sing next!",
        "Singer: @someone\\_else\nSong: https://youtu\\.be/fizzbuzz",
        "You are next in the queue. Add a song to your list to sing next!",
        "You may be called to sing next if the singer ahead of you is not ready",
        "Your list is empty",
    ]


@pytest.mark.asyncio
async def test_buttons():
    db = {
        "queue": [1],
        "user:1": ["https://youtu.be/xyzzy42"],
        "user:2": [],
        "names": {1: "@user_name", 2: "@someone_else", 3: "@random"},
    }
    bot = KaraokeBot(
        db=db,
        admins=["admin_user"],
    )

    tgbot = AsyncMock()

    admin = Chat(id=2, first_name="Admin", type="private", username="admin_user")
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

    callback_query = CallbackQuery(
        from_user=admin,
        id=101,
        chat_instance="chat_instance",
        data="next",
        message=make_message(100, "/next"),
    )
    callback_query.set_bot(tgbot)
    update = Update(update_id=200, callback_query=callback_query)
    await bot.button_callback(update, context=None)

    bot.dj.new_users = [2, 3]
    bot.dj.user_song_lists[2].append("https://youtu.be/fizzbuzz")

    update = Update(update_id=201, message=make_message(101, "/next"))
    await bot.next(update, context=None)

    assert [call.kwargs["text"] for call in tgbot.send_message.call_args_list] == [
        "Singer: @user\\_name\nSong: https://youtu\\.be/xyzzy42",
        "You are next in the queue. Add a song to your list to sing next!",
        "Singer: @someone\\_else\nSong: https://youtu\\.be/fizzbuzz\n\n"
        "_Next in queue:_ @random",
        "You are next in the queue. Add a song to your list to sing next!",
        "You may be called to sing next if the singer ahead of you is not ready",
        "You may be called to sing next if the 2 singers ahead of you are not ready",
    ]


@pytest.mark.asyncio
async def test_notready():
    db = {
        "queue": [1, 2],
        "user:1": ["https://youtu.be/xyzzy42"],
        "user:2": ["https://youtu.be/fizzbuzz"],
        "names": {1: "@user_name", 2: "@someone_else"},
    }
    bot = KaraokeBot(
        db=db,
        admins=["admin_user"],
    )

    tgbot = AsyncMock()

    admin = Chat(id=2, first_name="Admin", type="private", username="admin_user")
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

    update = Update(update_id=201, message=make_message(101, "/next"))
    await bot.next(update, context=None)

    callback_query = CallbackQuery(
        from_user=admin,
        id=101,
        chat_instance="chat_instance",
        data="not_ready",
        message=make_message(100, "/next"),
    )
    callback_query.set_bot(tgbot)
    update = Update(update_id=200, callback_query=callback_query)
    update.set_bot(tgbot)
    await bot.button_callback(update, context=None)

    print(tgbot.send_message.call_args_list)
    assert [call.kwargs["text"] for call in tgbot.send_message.call_args_list] == [
        "Singer: @user\\_name\nSong: https://youtu\\.be/xyzzy42",
        "You are next in the queue. Get ready to sing!",
        "You were paused because you missed your turn. "
        "Use /unpause when you are ready!",
        "@user_name was paused",
    ]


def test_youtube():
    vf = VideoFormatter(
        "",
        {
            "youtube:xxx": "Some [] text",
            "youtube:yyy": "Some (more)",
            "youtube:zzz": '{"title":"Title","duration":70}',
        },
    )
    assert (
        vf.tg_format("https://youtu.be/xxx").escaped_text()
        == r"[Some \[\] text](https://youtu.be/xxx)"
    )
    assert vf.song_info("https://youtu.be/xxx") == SongInfo(
        title="Some [] text",
        url="https://youtu.be/xxx",
        duration=0,
    )
    assert (
        vf.tg_format("https://youtu.be/yyy").escaped_text()
        == r"[Some \(more\)](https://youtu.be/yyy)"
    )
    assert (
        vf.tg_format("https://youtu.be/zzz").escaped_text()
        == r"[Title \(1:10\)](https://youtu.be/zzz)"
    )
    assert (
        vf.tg_format("https://youtube.com/watch?v=zzz").escaped_text()
        == r"[Title \(1:10\)](https://youtube.com/watch?v=zzz)"
    )
    assert (
        vf.tg_format("https://music.yandex.ru/somesong").escaped_text()
        == r"https://music\.yandex\.ru/somesong"
    )
    assert vf.song_info("https://music.yandex.ru/somesong") == SongInfo(
        title="https://music.yandex.ru/somesong",
        url="https://music.yandex.ru/somesong",
        duration=0,
    )
