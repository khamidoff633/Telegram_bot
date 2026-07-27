import os
import base64
import logging
import aiohttp
from groq import AsyncGroq
from openai import AsyncOpenAI
from config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY

async def transcribe_voice(file_path: str) -> str:
    """Ovozli faylni (voice note/audio) aniq matnga aylantirish"""
    
    # Audio fayl kengaytmasi bo'yicha to'g'ri MIME turini aniqlash
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".ogg": "audio/ogg",
        ".oga": "audio/ogg",
        ".opus": "audio/ogg",
        ".mp3": "audio/mp3",
        ".m4a": "audio/m4a",
        ".wav": "audio/wav",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
    }
    mime_type = mime_map.get(ext, "audio/mp3")

    # 1-Ustuvorlik: Google Gemini REST API (gemini-1.5-flash / gemini-2.0-flash)
    if GEMINI_API_KEY:
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro"
        ]
        
        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            
            base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Ushbu ovozli xabarni (voice note) o'zbek, rus yoki ingliz tilida o'ta aniqlikda matnga o'giring. Faqat eshitilgan matnni yozing. Ortiqcha izoh bermang."},
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
                for model_name in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                    try:
                        async with session.post(url, json=payload, timeout=45) as resp:
                            result = await resp.json()
                            if "candidates" in result and len(result["candidates"]) > 0:
                                parts = result["candidates"][0]["content"]["parts"]
                                text = "".join([p.get("text", "") for p in parts]).strip()
                                if text:
                                    logging.info(f"✅ Gemini Voice Transcription muvaffaqiyatli model: {model_name}")
                                    return text
                            elif "error" in result:
                                logging.warning(f"⚠️ Gemini API Xatosi ({model_name}): {result['error']}")
                    except Exception as model_err:
                        logging.warning(f"⚠️ Gemini Model {model_name} xatosi: {model_err}")

        except Exception as e:
            logging.error(f"❌ Gemini REST Xatosi: {e}")

    # 2-Ustuvorlik: Groq API (Whisper Large V3)
    if GROQ_API_KEY:
        try:
            client = AsyncGroq(api_key=GROQ_API_KEY)
            with open(file_path, "rb") as file:
                transcription = await client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
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
            with open(file_path, "rb") as file:
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

    return None

