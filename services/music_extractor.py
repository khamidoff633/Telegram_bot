import os
import uuid
import re
import asyncio
import aiohttp
import base64
import yt_dlp
from config import GEMINI_API_KEY, INSTAGRAM_COOKIE

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

def extract_audio_from_local_file(video_path: str) -> str:
    """Videodan audioni toza MP3 shaklida ajratish"""
    file_id = str(uuid.uuid4())[:8]
    output_mp3_path = os.path.join(DOWNLOAD_DIR, f"audio_{file_id}.mp3")

    # 1. FFmpeg CLI orqali tezkor ajratish
    cmd = f'ffmpeg -y -i "{video_path}" -vn -acodec libmp3lame -q:a 2 "{output_mp3_path}" >/dev/null 2>&1'
    res = os.system(cmd)
    if res == 0 and os.path.exists(output_mp3_path) and os.path.getsize(output_mp3_path) > 1000:
        return output_mp3_path

    # 2. Moviepy fallback
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
    """Google Gemini AI orqali videodagi asl qo'shiq va muallifini aniqlash"""
    if not GEMINI_API_KEY:
        return None

    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        mime_type = "audio/mp3" if file_path.endswith(".mp3") else "audio/ogg"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
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
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if "ARTIST:" in text and "TITLE:" in text:
                            artist_match = re.search(r'ARTIST:\s*(.*?)\s*\|', text)
                            title_match = re.search(r'TITLE:\s*(.*)', text)
                            if artist_match and title_match:
                                artist = artist_match.group(1).strip()
                                title = title_match.group(1).strip()
                                if artist.upper() != "UNKNOWN" and title.upper() != "UNKNOWN":
                                    return {'artist': artist, 'title': title}
                else:
                    err_txt = await resp.text()
                    print(f"Gemini Music ID API Error status {resp.status}: {err_txt[:150]}")
    except Exception as e:
        print(f"Gemini Music Identification Error: {e}")

    return None

def _download_full_original_song_sync(query_term: str) -> dict:
    """YouTube platformasidan qo'shiqning TO'LIQ ORIGINAL (3+ MINUTE) MP3 trekini yuklab olish"""
    cleaned = re.sub(r'[\(\[\{].*?[\)\]\}]', '', query_term)
    cleaned = re.sub(r'#\w+', '', cleaned).strip()

    queries = [
        f"ytsearch1:{cleaned} official audio",
        f"ytsearch1:{cleaned} full song",
        f"ytsearch1:{cleaned} original song",
        f"ytsearch1:{cleaned}",
    ]

    for query in queries:
        file_id = str(uuid.uuid4())[:8]
        output_template = os.path.join(DOWNLOAD_DIR, f"full_song_{file_id}.%(ext)s")
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'user_agent': USER_AGENTS[0],
            'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr']}},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp3_filename = base + ".mp3"
                if os.path.exists(mp3_filename):
                    filename = mp3_filename

                mp3_path = extract_audio_from_local_file(filename)
                if os.path.exists(filename) and filename != mp3_path:
                    try:
                        os.remove(filename)
                    except Exception:
                        pass

                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                    full_title = info.get('title', 'Original Song')
                    performer = info.get('uploader') or info.get('artist') or 'VoxMedia AI'
                    duration = info.get('duration', 0)
                    print(f"✅ TO'LIQ ORIGINAL MUSIQA YUKLANDI: {performer} - {full_title} ({duration} sec)")
                    return {
                        'file_path': mp3_path,
                        'title': full_title,
                        'performer': performer,
                        'duration': duration
                    }
        except Exception as e:
            print(f"YouTube Full Song Download query error '{query}': {e}")

    return None

async def download_full_original_song(artist: str, title: str) -> dict:
    query = f"{artist} {title}"
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_full_original_song_sync, query)

async def download_full_song_by_title(title: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_full_original_song_sync, title)

def _extract_audio_from_url_sync(url: str) -> dict:
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"audio_{file_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'user_agent': USER_AGENTS[0],
        'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp3_filename = base + ".mp3"
            if os.path.exists(mp3_filename):
                filename = mp3_filename

            mp3_path = extract_audio_from_local_file(filename)
            if os.path.exists(filename) and filename != mp3_path:
                try:
                    os.remove(filename)
                except Exception:
                    pass

            return {
                'file_path': mp3_path,
                'title': info.get('title', 'Original Sound'),
                'uploader': info.get('uploader', 'VoxMedia AI')
            }
    except Exception as e:
        print(f"Extract audio from URL error: {e}")

    return None

async def extract_audio_from_url(url: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_audio_from_url_sync, url)
