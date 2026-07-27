import os
import base64
import aiohttp
from groq import AsyncGroq
from openai import AsyncOpenAI
from config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY

async def transcribe_voice(file_path: str) -> str:
    """Ovozli faylni (voice note) aniq matnga aylantirish"""
    
    # 1-Ustuvorlik: Google Gemini REST API (gemini-2.5-flash)
    if GEMINI_API_KEY:
        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            
            base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            
            mime_type = "audio/ogg" if file_path.endswith((".ogg", ".oga", ".opus")) else "audio/mp3"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Ushbu ovozli xabarni (voice note) o'zbek, rus yoki ingliz tilida o'ta aniqlikda matnga o'giring. Faqat eshitilgan matnni yozing."},
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
                async with session.post(url, json=payload, timeout=30) as resp:
                    result = await resp.json()
                    if "candidates" in result and len(result["candidates"]) > 0:
                        parts = result["candidates"][0]["content"]["parts"]
                        text = "".join([p.get("text", "") for p in parts])
                        if text:
                            return text.strip()
                    elif "error" in result:
                        print("Gemini REST API Error:", result["error"])
        except Exception as e:
            print(f"Gemini REST Error: {e}")

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
                    return str(transcription).strip()
        except Exception as e:
            print(f"Groq Whisper Xatosi: {e}")

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
                    return str(transcription).strip()
        except Exception as e:
            print(f"OpenAI Whisper Xatosi: {e}")

    return "⚠️ Ovozli xabarni matnga o'girishda xatolik yuz berdi. Iltimos API kalitingizni tekshiring."
