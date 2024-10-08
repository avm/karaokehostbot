import httpx
from urllib.parse import urlparse, parse_qs
from telegram.helpers import escape_markdown
from telegram_markdown_text import MarkdownText, InlineUrl
import isodate
import json


def extract_youtube_id(url: str) -> str | None:
    # Parse the URL
    parsed_url = urlparse(url)
    # Check if the domain is a YouTube domain
    if "youtube.com" in parsed_url.netloc or "youtu.be" in parsed_url.netloc:
        # Extract video ID from query parameters for full YouTube links
        if "watch" in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]  # Extract the 'v' parameter
        # Extract video ID from path for shortened YouTube links
        elif parsed_url.path.startswith("/"):
            return parsed_url.path.lstrip("/")
    return None


class VideoFormatter:
    def __init__(self, yt_api_key: str, db={}):
        self.db = db
        self.yt_api_key = yt_api_key
        self.http = httpx.AsyncClient()

    def get_title(self, url: str) -> dict[str, str | int] | None:
        if not (yt_id := extract_youtube_id(url)):
            return None
        record = self.db.get(self._db_key(yt_id))
        if record and record.startswith('{'):
            data = json.loads(record)
            return data
        if record:
            return {'title': record, 'duration': 0}
        return None

    def tg_format(self, url: str) -> MarkdownText:
        if data := self.get_title(url):
            title = data['title']
            if duration := data.get('duration', 0):
                minutes = duration // 60
                seconds = duration % 60
                title += r' (%d:%02d)' % (minutes, seconds)
            return InlineUrl(text=title, url=url)
        return MarkdownText(url)

    @staticmethod
    def _db_key(yt_id: str) -> str:
        return f"youtube:{yt_id}"

    async def _fetch_details(self, yt_id: str) -> None:
        url = "https://www.googleapis.com/youtube/v3/videos"
        response = await self.http.get(
            url, params=dict(part="snippet,contentDetails", id=yt_id, key=self.yt_api_key)
        )
        data = response.json()

        # Extract video title and thumbnail URL
        try:
            title = data["items"][0]["snippet"]["title"]
            duration = isodate.parse_duration(data["items"][0]["contentDetails"]["duration"])
            seconds = duration.total_seconds()
            print("Got title for", yt_id, title, 'duration', seconds)
            self.db[self._db_key(yt_id)] = json.dumps({'title': title, 'duration': seconds})
        except (KeyError, IndexError):
            print("data format error", data)

    async def register_url(self, url: str) -> None:
        yt_id = extract_youtube_id(url)
        if not yt_id:
            return
        if self._db_key(yt_id) in self.db:
            return
        await self._fetch_details(yt_id)
