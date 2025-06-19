import json
import re
from pathlib import Path
import argparse
from dataclasses import dataclass


def parse_messages(messages):
    # Filter messages from the bot that contain singer and song
    tracks = []
    for msg in messages:
        if (
            msg.get("type") == "message"
            and msg.get("from") == "Karaoke Host Bot"
            and isinstance(msg.get("text"), list)
        ):
            singer = None
            song = None

            for part in msg["text"]:
                if isinstance(part, dict):
                    if part.get("type") == "mention":
                        singer = part["text"]
                    elif part.get("type") == "text_link":
                        song = part["text"]
                elif isinstance(part, str):
                    # Look for "Singer: NAME\nSong:"
                    m = re.search(r"Singer: (.+?)\nSong:", part)
                    if m:
                        singer = m.group(1).strip()

            if singer and song:
                timestamp = int(msg["date_unixtime"])
                tracks.append({"time": timestamp, "singer": singer, "song": song})
    # Sort by timestamp just in case
    tracks.sort(key=lambda x: x["time"])
    return tracks


def format_time(seconds):
    return f"{seconds:.3f}"  # float in seconds, 3 decimal places


@dataclass
class Span:
    start: str
    end: str
    label: str


def generate_spans(tracks, final_duration_sec=360) -> list[Span]:
    if not tracks:
        return []

    spans = []
    base_time = tracks[0]["time"]
    for i, track in enumerate(tracks):
        start = track["time"] - base_time
        if i + 1 < len(tracks):
            end = tracks[i + 1]["time"] - base_time
        else:
            end = start + final_duration_sec
        spans.append(
            Span(
                start=format_time(start),
                end=format_time(end),
                label=f"{track['singer']} – {track['song']}",
            )
        )
    return spans


def main():
    parser = argparse.ArgumentParser(
        description="Generate karaoke label spans from chat export."
    )
    parser.add_argument("input_path", help="Path to the chat JSON file")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages", [])
    tracks = parse_messages(messages)
    spans = generate_spans(tracks)

    for span in spans:
        print(f"{span.start}\t{span.end}\t{span.label}")


if __name__ == "__main__":
    main()
