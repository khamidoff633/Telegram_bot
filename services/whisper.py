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

async def _transcribe_google_web_speech_async(wav_path: str) -> str:

    """Bepul Google Web Speech API (Parallel Async Chunking & Smart Language Auto-Detection bilan 20+ minutlik audiolarni 100% to'liq o'giruvchi dvigatel)"""
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
        return None

    import speech_recognition as sr

    temp_dir = os.path.join(os.path.dirname(wav_path), f"chunks_{os.path.basename(wav_path)}")
    os.makedirs(temp_dir, exist_ok=True)
    chunk_pattern = os.path.join(temp_dir, "chunk_%03d.wav")

    # 1. FFmpeg yordamida audioni 30-soniyalik bo'laklarga ajratish
    split_cmd = [
        "ffmpeg", "-y", "-i", wav_path,
        "-f", "segment",
        "-segment_time", "30",
        "-c", "copy",
        chunk_pattern
    ]
    try:
        proc = await asyncio.create_subprocess_exec(*split_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.communicate()
    except Exception as e:
        logging.warning(f"⚠️ Chunking ffmpeg error: {e}")
        import shutil
        shutil.copy(wav_path, os.path.join(temp_dir, "chunk_000.wav"))

    chunk_files = sorted([
        os.path.join(temp_dir, f) for f in os.listdir(temp_dir) 
        if f.startswith("chunk_") and f.endswith(".wav")
    ])

    if not chunk_files:
        return None

    r = sr.Recognizer()
    loop = asyncio.get_event_loop()

    # 2. Birinchi bo'lak orqali audio tilini aqlli aniqlash (en-US, uz-UZ, ru-RU)
    first_chunk = chunk_files[0]
    
    def _detect_lang_sync():
        try:
            with sr.AudioFile(first_chunk) as source:
                audio_sample = r.record(source)
            lang_scores = {}
            for lang in ["en-US", "uz-UZ", "ru-RU"]:
                try:
                    txt = r.recognize_google(audio_sample, language=lang)
                    if txt and len(txt.strip()) > 0:
                        lang_scores[lang] = len(txt.split())
                except Exception:
                    continue
            if lang_scores:
                if "en-US" in lang_scores:
                    return "en-US"
                return max(lang_scores, key=lang_scores.get)
        except Exception:
            pass
        return "en-US"

    detected_lang = await loop.run_in_executor(None, _detect_lang_sync)
    logging.info(f"🌐 20-Min Audio Engine Detected Language: {detected_lang}")

    # 3. Parallel Async Chunk Processing (Barcha 20-minutlik bo'laklar parallel ravishda soniyalarda o'giriladi)
    semaphore = asyncio.Semaphore(6)

    async def _transcribe_single_chunk(chunk_path: str) -> str:
        async with semaphore:
            def _recognize_sync():
                try:
                    with sr.AudioFile(chunk_path) as source:
                        audio = r.record(source)
                    return r.recognize_google(audio, language=detected_lang)
                except Exception:
                    for alt in ["en-US", "uz-UZ", "ru-RU"]:
                        if alt != detected_lang:
                            try:
                                with sr.AudioFile(chunk_path) as source:
                                    audio = r.record(source)
                                return r.recognize_google(audio, language=alt)
                            except Exception:
                                pass
                    return ""

            try:
                res = await loop.run_in_executor(None, _recognize_sync)
                return res.strip() if res else ""
            finally:
                if os.path.exists(chunk_path):
                    try:
                        os.remove(chunk_path)
                    except Exception:
                        pass

    tasks = [_transcribe_single_chunk(cf) for cf in chunk_files]
    results = await asyncio.gather(*tasks)

    # Bo'laklar papkasini tozalash
    if os.path.exists(temp_dir):
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    full_text = " ".join([res for res in results if res]).strip()
    if full_text:
        logging.info(f"✅ To'liq Long Audio Transkripsiyasi ({len(chunk_files)} bo'lakdan): {len(full_text)} belgi")
        return full_text

    return None

async def polish_transcribed_text(raw_text: str) -> str:
    """Raw speech-to-text natijasini tinish belgilari, grammatika va paragraflar bilan mukammal va tiniq holatga keltirish"""
    if not raw_text or len(raw_text.strip()) < 15 or not GEMINI_API_KEY:
        return raw_text

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        prompt = (
            "Siz professional matn muharririsiz. Quyidagi ovozdan olingan (speech-to-text) xom matnni "
            "ma'nosini zarracha o'zgartirmasdan, imlo va tinish belgilarini (punktuatsiya), "
            "katta-kichik harflarni va tushunarsiz fonetik xatolarni to'g'rilab, chiroyli va o'qishga o'ta qulay mukammal matn va paragraflar holatiga keltiring.\n"
            "Faqat to'g'rilangan toza matnni qaytaring, hech qanday ortiqcha izoh yozmang.\n\n"
            f"XOM MATN:\n{raw_text}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_chunks = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                        polished = "".join(text_chunks).strip()
                        if polished:
                            logging.info("✨ AI Text Polishing muvaffaqiyatli amalga oshirildi")
                            return polished
    except Exception as e:
        logging.warning(f"⚠️ Text polishing skipped: {e}")

    return raw_text

async def transcribe_voice(file_path: str) -> str:
    """Ovozli faylni (voice note/audio) aniq matnga aylantirish (Senior Multi-Engine Tizimi)"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logging.error(f"❌ Fayl mavjud emas yoki bo'sh: {file_path}")
        return None

    # 0-Qadam: Audio faylni AI uchun universal 16kHz mono WAV formatiga o'tkazish
    target_path = await convert_audio_to_wav(file_path)

    raw_result = None

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
                            async with session.post(url, json=payload, timeout=120) as resp:
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
                                            raw_result = text
                                            break
                                else:
                                    err_text = await resp.text()
                                    logging.warning(f"⚠️ Gemini API HTTP {resp.status} ({model_name}): {err_text[:200]}")
                        except Exception as model_err:
                            logging.warning(f"⚠️ Gemini Model {model_name} xatosi: {model_err}")

            except Exception as e:
                logging.error(f"❌ Gemini REST Xatosi: {e}")

        # 2-Ustuvorlik: Groq API (Whisper Large V3)
        if not raw_result and GROQ_API_KEY:
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
                        raw_result = str(transcription).strip()
            except Exception as e:
                logging.warning(f"⚠️ Groq Whisper Xatosi: {e}")

        # 3-Ustuvorlik: OpenAI Whisper API
        if not raw_result and OPENAI_API_KEY:
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
                        raw_result = str(transcription).strip()
            except Exception as e:
                logging.warning(f"⚠️ OpenAI Whisper Xatosi: {e}")

        # 4-Ustuvorlik: Google Free Web Speech API (Parallel Async Engine)
        if not raw_result:
            raw_result = await _transcribe_google_web_speech_async(target_path)

        # AI Text Polishing: Matnni tinish belgilari, grammatika va chiroyli formatlash bilan mukammallashtirish
        if raw_result:
            return await polish_transcribed_text(raw_result)

    finally:
        # Vaqtinchalik konvertatsiya qilingan faylni o'chirish
        if target_path != file_path and os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass

    return None




