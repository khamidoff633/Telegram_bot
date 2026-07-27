import os
import asyncio
import uuid
import re
import base64
import aiohttp
import yt_dlp
from config import GEMINI_API_KEY

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
]

def extract_audio_from_local_file(video_path: str) -> str:
    """Yuklab olingan MP4 fayldan musiqani (MP3) ajratib olish"""
    file_id = str(uuid.uuid4())[:8]
    output_mp3_path = os.path.join(DOWNLOAD_DIR, f"audio_{file_id}.mp3")

    try:
        from moviepy import VideoFileClip
        video = VideoFileClip(video_path)
        if video.audio is not None:
            video.audio.write_audiofile(output_mp3_path, logger=None)
            video.close()
            if os.path.exists(output_mp3_path):
                return output_mp3_path
    except Exception as e:
        print(f"Moviepy extract err: {e}")

    return video_path

async def identify_original_song(file_path: str) -> dict:
    """Gemini 2.5 Flash AI yordamida audiodan musiqaning va qo'shiqchining asl original nomini aniqlash"""
    if not GEMINI_API_KEY or not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        mime_type = "audio/mp3" if file_path.endswith(".mp3") else "audio/ogg"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": (
                            "Siz professional musiqa taniyydigan AI mutaxassisisiz.\n"
                            "Ushbu audio fayldagi musiqaning va qo'shiqchining (artist) asl rasmiy original nomini aniqlang.\n"
                            "Qo'shiq tili har qanday bo'lishi mumkin (O'zbek, Uyg'ur, Rus, Ingliz, Turk, Arab va b.).\n"
                            "Faqat bitta qatorda quyidagi aniq formatda javob bering:\n"
                            "ARTIST: <Muallif/Qo'shiqchi nomi> | TITLE: <Musiqa original nomi>\n"
                            "Agar bu qo'shiq bo'lmasa yoki umuman aniqlab bo'lmasa, UNKNOWN deb javob bering."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_audio
                        }
                    }
                ]
            }]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=20) as resp:
                res = await resp.json()
                if "candidates" in res and len(res["candidates"]) > 0:
                    text = res["candidates"][0]["content"]["parts"][0].get("text", "").strip()
                    if "ARTIST:" in text and "TITLE:" in text:
                        parts = text.split("|")
                        artist = parts[0].replace("ARTIST:", "").strip()
                        title = parts[1].replace("TITLE:", "").strip()
                        if artist.upper() != "UNKNOWN" and title.upper() != "UNKNOWN":
                            return {"artist": artist, "title": title}
    except Exception as e:
        print(f"Gemini Music Identification Error: {e}")

    return None

def _download_full_original_song_sync(query_term: str) -> dict:
    """YouTube Android/iOS Engine orqali musiqaning to'liq (3-4 daqiqalik) original MP3 versiyasini yuklab olish"""
    # Clean query (remove TikTok/Reel noise)
    cleaned = re.sub(r'[\(\[\{].*?[\)\]\}]', '', query_term)
    cleaned = re.sub(r'#\w+', '', cleaned).strip()

    queries = [
        f"ytsearch1:{cleaned} official audio",
        f"ytsearch1:{cleaned} original track",
        f"ytsearch1:{cleaned} audio",
        f"ytsearch1:{cleaned}",
    ]

    for query in queries:
        file_id = str(uuid.uuid4())[:8]
        output_template = os.path.join(DOWNLOAD_DIR, f"full_{file_id}.%(ext)s")

        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'user_agent': USER_AGENTS[0],
            'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp4_filename = base + ".mp4"
                if os.path.exists(mp4_filename):
                    filename = mp4_filename

                mp3_path = extract_audio_from_local_file(filename)
                if os.path.exists(filename) and filename != mp3_path:
                    try:
                        os.remove(filename)
                    except Exception:
                        pass

                duration = info.get('duration', 0)
                title = info.get('title', cleaned)
                uploader = info.get('uploader', 'VoxMedia Music')

                print(f"✅ TO'LIQ ORIGINAL MUSIQA YUKLANDI: {title} ({duration} sec)")
                return {
                    'file_path': mp3_path,
                    'title': title,
                    'performer': uploader,
                    'duration': duration
                }
        except Exception as e:
            print(f"Full song download attempt for '{query}' error: {e}")

    return None

async def download_full_original_song(artist: str, title: str) -> dict:
    query_term = f"{artist} {title}".strip()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_full_original_song_sync, query_term)

async def download_full_song_by_title(video_title: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_full_original_song_sync, video_title)

def _extract_audio_sync(url: str) -> dict:
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"audio_{file_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return {
                'file_path': filename,
                'title': info.get('title', 'Original Sound'),
                'uploader': 'VoxMedia AI',
            }
    except Exception as e:
        print(f"Audio extract error: {e}")
        return None

async def extract_audio_from_url(url: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_audio_sync, url)
