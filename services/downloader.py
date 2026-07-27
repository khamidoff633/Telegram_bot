import os
import asyncio
import uuid
import re
import requests
import yt_dlp
from config import INSTAGRAM_COOKIE

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIE_FILE_PATH = "cookies.txt"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
]

def ensure_cookies_file():
    if INSTAGRAM_COOKIE and not os.path.exists(COOKIE_FILE_PATH):
        cookie_content = (
            "# Netscape HTTP Cookie File\n"
            ".instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t" + INSTAGRAM_COOKIE + "\n"
        )
        with open(COOKIE_FILE_PATH, "w") as f:
            f.write(cookie_content)

def _download_instagram_direct(url: str) -> dict:
    """Instagram Reels / Posts uchun maxsus scraping usuli"""
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        return None
    shortcode = match.group(1)

    headers = {
        'User-Agent': USER_AGENTS[0],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    if INSTAGRAM_COOKIE:
        headers['Cookie'] = f"sessionid={INSTAGRAM_COOKIE}"

    embed_urls = [
        f"https://www.instagram.com/p/{shortcode}/embed/",
        f"https://www.instagram.com/p/{shortcode}/embed/captioned/",
    ]

    for embed_url in embed_urls:
        try:
            res = requests.get(embed_url, headers=headers, timeout=10)
            if res.status_code == 200:
                video_matches = re.findall(r'\"video_url\":\"(.*?)\"', res.text)
                if not video_matches:
                    video_matches = re.findall(r'<video[^>]+src=\"(.*?)\"', res.text)
                if not video_matches:
                    video_matches = re.findall(r'https?://[^\s\"\']+\.mp4[^\s\"\']*', res.text)

                if video_matches:
                    video_url = video_matches[0].replace('\\u0026', '&').replace('\\/', '/')
                    file_id = str(uuid.uuid4())[:8]
                    file_path = os.path.join(DOWNLOAD_DIR, f"insta_{shortcode}_{file_id}.mp4")

                    v_res = requests.get(video_url, headers=headers, stream=True, timeout=25)
                    if v_res.status_code == 200:
                        with open(file_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=8192):
                                f.write(chunk)
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                            return {
                                'file_path': file_path,
                                'title': 'Instagram Reel',
                                'uploader': 'VoxMedia Video',
                                'track': None,
                                'artist': None,
                                'description': ''
                            }
        except Exception as e:
            print(f"Instagram Direct Scrape Error: {e}")

    return None

def _download_tiktok_direct(url: str) -> dict:
    """TikTok HD Video Watermark-Free Direct Scraper Engine (TikWM API)"""
    try:
        api_url = f"https://www.tikwm.com/api/?url={url}"
        headers = {'User-Agent': USER_AGENTS[0]}
        res = requests.get(api_url, headers=headers, timeout=12)
        if res.status_code == 200:
            res_data = res.json()
            data = res_data.get("data", {})
            video_url = data.get("play") or data.get("wmplay")
            if video_url:
                if not video_url.startswith("http"):
                    video_url = "https://www.tikwm.com" + video_url
                file_id = str(uuid.uuid4())[:8]
                file_path = os.path.join(DOWNLOAD_DIR, f"tiktok_{file_id}.mp4")
                v_res = requests.get(video_url, headers=headers, stream=True, timeout=30)
                if v_res.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in v_res.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                        music_info = data.get("music_info", {})
                        return {
                            'file_path': file_path,
                            'title': data.get("title", "TikTok Video"),
                            'uploader': data.get("author", {}).get("nickname", "TikTok Creator"),
                            'track': music_info.get("title"),
                            'artist': music_info.get("author"),
                            'description': data.get("title", "")
                        }
    except Exception as e:
        print(f"TikTok Direct Scrape Error: {e}")
    return None

def _download_video_sync(url: str, is_vip: bool = False) -> dict:
    ensure_cookies_file()
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"video_{file_id}.%(ext)s")

    clean_url = url.split('?')[0] if '?' in url and ('instagram.com' in url or 'instagr.am' in url or 'tiktok.com' in url) else url

    # TikTok zaxira dvigateli
    if 'tiktok.com' in url or 'vt.tiktok.com' in url:
        tt_result = _download_tiktok_direct(url)
        if tt_result and os.path.exists(tt_result['file_path']):
            return tt_result

    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'user_agent': USER_AGENTS[0],
        'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr', 'web']}},
    }

    if os.path.exists(COOKIE_FILE_PATH):
        ydl_opts['cookiefile'] = COOKIE_FILE_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_filename = base + ".mp4"
            if os.path.exists(mp4_filename):
                filename = mp4_filename

            return {
                'file_path': filename,
                'title': info.get('title', 'Media Video'),
                'uploader': info.get('uploader', 'VoxMedia Video'),
                'track': info.get('track'),
                'artist': info.get('artist'),
                'description': info.get('description', '')
            }
    except Exception as e:
        print(f"yt-dlp birinchi xato: {e}. Fallback usul o'tkazilmoqda...")

    if 'instagram.com' in url or 'instagr.am' in url:
        direct_result = _download_instagram_direct(clean_url)
        if direct_result and os.path.exists(direct_result['file_path']):
            return direct_result

    ydl_opts_fallback = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['tv', 'android_vr', 'web']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_filename = base + ".mp4"
            if os.path.exists(mp4_filename):
                filename = mp4_filename

            return {
                'file_path': filename,
                'title': info.get('title', 'Media Video'),
                'uploader': info.get('uploader', 'VoxMedia Video'),
                'track': info.get('track'),
                'artist': info.get('artist'),
                'description': info.get('description', '')
            }
    except Exception as fallback_e:
        print(f"yt-dlp zaxira xatosi: {fallback_e}")

    raise Exception("Videoni yuklab bo'lmadi.")

async def download_video(url: str, is_vip: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_video_sync, url, is_vip)
