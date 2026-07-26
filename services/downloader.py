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

def _download_instagram_direct(url: str) -> str:
    """Instagram Reels / Posts uchun maxsus to'g'ridan-to'g'ri scraping usuli"""
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', url)
    if not match:
        return None
    shortcode = match.group(1)

    headers = {
        'User-Agent': USER_AGENTS[0],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    if INSTAGRAM_COOKIE:
        headers['Cookie'] = f"sessionid={INSTAGRAM_COOKIE}"

    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/"
    try:
        res = requests.get(embed_url, headers=headers, timeout=10)
        if res.status_code == 200:
            video_matches = re.findall(r'\"video_url\":\"(.*?)\"', res.text)
            if not video_matches:
                video_matches = re.findall(r'<video[^>]+src=\"(.*?)\"', res.text)
            
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
                        return file_path
    except Exception as e:
        print(f"Instagram Direct Scrape Error: {e}")

    return None

def _download_video_sync(url: str, is_vip: bool = False) -> dict:
    """yt-dlp va Direct Scraper yordamida videolarni yuklash"""
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"%(title).30s_{file_id}.%(ext)s")

    clean_url = url.split('?')[0] if ('instagram.com' in url or 'instagr.am' in url) else url

    # Instagram bo'lsa avval Direct Scraper'ni sinaymiz
    if 'instagram.com' in url or 'instagr.am' in url:
        direct_path = _download_instagram_direct(clean_url)
        if direct_path and os.path.exists(direct_path):
            return {
                'file_path': direct_path,
                'title': 'Instagram Video',
                'duration': 0,
                'uploader': 'Instagram',
                'ext': 'mp4'
            }

    # Format tanlovi
    if is_vip:
        format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    else:
        format_spec = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]/best"

    headers = {
        'User-Agent': USER_AGENTS[0],
        'Accept': '*/*',
    }

    ydl_opts = {
        'format': format_spec,
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50 * 1024 * 1024,
        'user_agent': USER_AGENTS[0],
        'http_headers': headers,
        'retries': 3,
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
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Media'),
                'ext': 'mp4'
            }
    except Exception as first_err:
        print(f"yt-dlp birinchi xato: {first_err}. Fallback usul o'tkazilmoqda...")
        
        fallback_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'user_agent': USER_AGENTS[0],
            'http_headers': headers,
        }
        if os.path.exists(COOKIE_FILE_PATH):
            fallback_opts['cookiefile'] = COOKIE_FILE_PATH

        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_filename = base + ".mp4"
            if os.path.exists(mp4_filename):
                filename = mp4_filename

            return {
                'file_path': filename,
                'title': info.get('title', 'Media Video'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Media'),
                'ext': 'mp4'
            }

async def download_video(url: str, is_vip: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download_video_sync, url, is_vip)
