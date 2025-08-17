#!/usr/bin/env python3
import sys
import re
import time
import datetime
import requests
from yt_dlp import YoutubeDL
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError

# Constants for menu
MENU = """
===== 📺 YouTube to Telegram Bot =====

1️⃣ Single Video
2️⃣ Playlist
3️⃣ Channel (all videos)
0️⃣ Exit
"""

# Regex patterns for basic link validation
YOUTUBE_VIDEO_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+')
YOUTUBE_PLAYLIST_REGEX = re.compile(r'(https?://)?(www\.)?youtube\.com/playlist\?list=[\w-]+')
YOUTUBE_CHANNEL_REGEX = re.compile(r'(https?://)?(www\.)?youtube\.com/(channel/|c/|user/)[\w-]+')

# Telegram Bot token and chat_id
# User must replace these with their actual bot token and chat id
TELEGRAM_BOT_TOKEN = "8154976061:AAGryZFYIb5fu6OlCVFMAlWgiu6M8J9j_1o"
TELEGRAM_CHAT_ID = "6956029558"

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def input_choice():
    while True:
        choice = input("Enter choice (0-3): ").strip()
        if choice in {'0', '1', '2', '3'}:
            return choice
        print("❌ Invalid choice. Please enter 0, 1, 2 or 3.")

def input_link(prompt):
    link = input(prompt).strip()
    return link

def validate_link(link: str, mode: str) -> bool:
    if mode == '1':  # Single video
        return bool(YOUTUBE_VIDEO_REGEX.match(link))
    elif mode == '2':  # Playlist
        return bool(YOUTUBE_PLAYLIST_REGEX.match(link))
    elif mode == '3':  # Channel
        return bool(YOUTUBE_CHANNEL_REGEX.match(link))
    return False

def format_duration(seconds: int) -> str:
    if seconds is None:
        return "Unknown"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    else:
        return f"{m:d}:{s:02d}"

def format_date(date_str: str) -> str:
    # date_str usually like '20230801' or '2023-08-01'
    try:
        if '-' in date_str:
            dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        else:
            dt = datetime.datetime.strptime(date_str, '%Y%m%d')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return "Unknown"

def fetch_videos_info(url: str, mode: str):
    print("🔎 Fetching videos from given link...")
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'ignoreerrors': True,
        'extract_flat': True if mode in {'2', '3'} else False,
        'forceurl': True,
        'nocheckcertificate': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception:
            return None, "❌ Invalid YouTube link"

    if info is None:
        return None, "⚠️ No videos found."

    # For playlist and channel, info['entries'] contains video dicts or video URLs (if extract_flat)
    videos = []
    if mode == '1':
        # Single video info
        # Confirm video info presence
        if 'title' not in info:
            return None, "⚠️ No videos found."
        videos.append(info)
    else:
        # Playlist or channel
        entries = info.get('entries', [])
        if not entries:
            return None, "⚠️ No videos found."
        # entries might be incomplete video info (extract_flat=True)
        # We want full info for each video, so we must fetch each video info separately
        print(f"📂 Found {len(entries)} videos in {'playlist' if mode=='2' else 'channel'}")
        # Fetch full info for each video
        for e in entries:
            # e can be a dict with 'url' or 'id', but limited info
            video_url = None
            if 'url' in e:
                # Compose full URL for video
                video_url = f"https://youtu.be/{e['url']}"
            elif 'id' in e:
                video_url = f"https://youtu.be/{e['id']}"
            else:
                continue
            try:
                video_info = ydl.extract_info(video_url, download=False)
                if video_info:
                    videos.append(video_info)
            except Exception:
                # Skip if error occurs fetching video info
                continue
        if not videos:
            return None, "⚠️ No videos found."
    return videos, None

def send_video_info(video):
    # Extract required data
    title = video.get('title', 'Unknown Title')
    url = video.get('webpage_url') or video.get('url') or "https://youtu.be/" + video.get('id', '')
    thumbnail = video.get('thumbnail')
    duration = format_duration(video.get('duration'))
    upload_date = format_date(video.get('upload_date', ''))

    # Compose message caption
    caption = (f"🎬 Title: {title}\n"
               f"🔗 Link: {url}\n"
               f"⏱ Duration: {duration}\n"
               f"📅 Date: {upload_date}")

    try:
        if thumbnail:
            # Send photo with caption
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=thumbnail, caption=caption)
        else:
            # Send text message if no thumbnail
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=caption)
        return True
    except TelegramError as e:
        return False

def main():
    while True:
        print(MENU)
        choice = input_choice()
        if choice == '0':
            print("Exiting... Bye!")
            sys.exit(0)

        # Ask for link corresponding to choice
        prompt_map = {
            '1': "Enter YouTube video URL: ",
            '2': "Enter YouTube playlist URL: ",
            '3': "Enter YouTube channel URL: "
        }
        link = input_link(prompt_map[choice])

        # Validate link
        if not validate_link(link, choice):
            print("❌ Invalid YouTube link")
            continue

        # Fetch videos info
        videos, error = fetch_videos_info(link, choice)
        if error:
            print(error)
            continue

        # Send info for each video
        for idx, video in enumerate(videos, 1):
            title = video.get('title', 'Unknown Title')
            print(f"➡️ Sending: [{title}]")
            success = send_video_info(video)
            if not success:
                print("⚠️ Retry sending failed message.")
                # We do not retry infinitely, just continue
                continue
            time.sleep(0.5)  # small delay to avoid flooding

        print("🎉 Done! All videos sent successfully.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting... Bye!")
        sys.exit(0)
