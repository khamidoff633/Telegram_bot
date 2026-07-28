import os
import base64
import logging
import asyncio
import aiohttp
from groq import AsyncGroq
from openai import AsyncOpenAI
from config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY

async def convert_audio_to_wav(input_path: str) -> str:
    """FFmpeg yordamida har qanday ogg/mp3/m4a ovozli faylini AI uchun ideal 16kHz mono WAV faylga o'tkazish"""
    wav_path = os.path.splitext(input_path)[0] + "_converted.wav"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            wav_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
            logging.info(f"✅ FFmpeg audio konvertatsiya qilindi: {wav_path}")
            return wav_path
        else:
            logging.warning(f"⚠️ FFmpeg konvertatsiyada ogohlantirish: {stderr.decode()[:200]}")
    except Exception as e:
        logging.warning(f"⚠️ FFmpeg ishga tushirishda xato (original fayldan foydalaniladi): {e}")
    return input_path

def _transcribe_google_web_speech_sync(wav_path: str) -> str:
    """Bepul Google Web Speech API (API Key talab qilinmaydigan 100% zaxira tizimi)"""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
        
        # O'zbek, rus va ingliz tillarida navbatma-navbat urinish
        languages = ["uz-UZ", "ru-RU", "en-US"]
        for lang in languages:
            try:
                text = r.recognize_google(audio_data, language=lang)
                if text and len(text.strip()) > 0:
                    logging.info(f"✅ Google Free Web Speech API muvaffaqiyatli ({lang}): {text[:50]}")
                    return text.strip()
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"⚠️ Google Free Web Speech API xatosi: {e}")
    return None

async def transcribe_voice(file_path: str) -> str:
    """Ovozli faylni (voice note/audio) aniq matnga aylantirish (Senior Multi-Engine Tizimi)"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logging.error(f"❌ Fayl mavjud emas yoki bo'sh: {file_path}")
        return None

    # 0-Qadam: Audio faylni AI uchun universal 16kHz mono WAV formatiga o'tkazish
    target_path = await convert_audio_to_wav(file_path)

    try:
        # 1-Ustuvorlik: Google Gemini REST API (gemini-1.5-flash / gemini-2.0-flash)
        if GEMINI_API_KEY:
            models_to_try = [
                "gemini-1.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-pro"
            ]
            
            try:
                with open(target_path, "rb") as f:
                    audio_bytes = f.read()
                
                base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                mime_type = "audio/wav" if target_path.endswith(".wav") else "audio/mp3"

                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Ushbu ovozli yoki audio xabarni o'zbek, rus yoki ingliz tilida o'ta aniqlikda matnga o'giring. Faqat eshitilgan matnni yozing, hech qanday qo'shimcha so'z yoki izoh qo'shmang."},
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": base64_audio
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 8192
                    }
                }

                async with aiohttp.ClientSession() as session:
                    for model_name in models_to_try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                        try:
                            async with session.post(url, json=payload, timeout=45) as resp:
                                if resp.status == 200:
                                    result = await resp.json()
                                    if "candidates" in result and len(result["candidates"]) > 0:
                                        cand = result["candidates"][0]
                                        content = cand.get("content", {}) or {}
                                        parts = content.get("parts", []) or []
                                        text_chunks = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                                        text = "".join(text_chunks).strip()
                                        if text:
                                            logging.info(f"✅ Gemini Voice Transcription muvaffaqiyatli model: {model_name}")
                                            return text
                                else:
                                    err_text = await resp.text()
                                    logging.warning(f"⚠️ Gemini API HTTP {resp.status} ({model_name}): {err_text[:200]}")
                        except Exception as model_err:
                            logging.warning(f"⚠️ Gemini Model {model_name} xatosi: {model_err}")

            except Exception as e:
                logging.error(f"❌ Gemini REST Xatosi: {e}")

        # 2-Ustuvorlik: Groq API (Whisper Large V3)
        if GROQ_API_KEY:
            try:
                client = AsyncGroq(api_key=GROQ_API_KEY)
                with open(target_path, "rb") as file:
                    transcription = await client.audio.transcriptions.create(
                        file=(os.path.basename(target_path), file.read()),
                        model="whisper-large-v3",
                        response_format="text"
                    )
                    if transcription:
                        logging.info("✅ Groq Whisper Voice Transcription muvaffaqiyatli")
                        return str(transcription).strip()
            except Exception as e:
                logging.warning(f"⚠️ Groq Whisper Xatosi: {e}")

        # 3-Ustuvorlik: OpenAI Whisper API
        if OPENAI_API_KEY:
            try:
                client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                with open(target_path, "rb") as file:
                    transcription = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=file,
                        response_format="text"
                    )
                    if transcription:
                        logging.info("✅ OpenAI Whisper Voice Transcription muvaffaqiyatli")
                        return str(transcription).strip()
            except Exception as e:
                logging.warning(f"⚠️ OpenAI Whisper Xatosi: {e}")

        # 4-Ustuvorlik: Google Free Web Speech API (Umrbod bepul 100% Zaxira Dvigateli)
        loop = asyncio.get_event_loop()
        free_text = await loop.run_in_executor(None, _transcribe_google_web_speech_sync, target_path)
        if free_text:
            return free_text

    finally:
        # Vaqtinchalik konvertatsiya qilingan faylni o'chirish
        if target_path != file_path and os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass

    return None


