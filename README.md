# 🎬🎙️ VIP Media & Voice Downloader SaaS Telegram Bot

Instagram Reels, YouTube Shorts video yuklovchi, Ovozli xabarlarni matnga o'giruvchi hamda Payme/Click obuna tizimiga ega mukammal Telegram Bot.

---

## 🌟 Funksiyalari:

1. **🎬 Instagram & YouTube Downloader:**
   - Bepul foydalanuvchilar: **480p format**, **3 ta limit** (har 48 soatda tiklanadi).
   - Video ostida: *"Sifatli (HD) videolarni yuklash va cheksiz foydalanish uchun obuna bo'ling"* + **[💳 Obuna bo'lish]** & **[🎵 Musiqani ajratish]** tugmalari.
   - Limit tugaganda: **48 soatlik ogohlantirish** va VIP obuna taklifi.
2. **🎙️ Voice-to-Text Transcriber (Whisper AI):**
   - Uzbek, Rus, Ingliz tillaridagi voice xabarlarni matnga o'giradi.
   - Separate limit: Bepul foydalanuvchilarga **3 ta voice** (Video limitidan ayri!).
3. **🎵 Videodan Musiqani Ajratib Berish (MP3):**
   - Video tagidagi tugmani bosish orqali musiqasini MP3 sifatli formatda olish.
4. **👑 `@bakhridd1n_dev` VIP Bypass:**
   - VIP Admin uchun **1080p/4K HD**, **cheksiz limit** va reklamalarsiz tezkor rejim.
5. **💳 Obuna & To'lovlar Tizimi:**
   - Click va Payme integratsiyasi.
   - Referal taklifnoma tizimi (Do'stini taklif qilsa +2 limit).

---

## 🚀 Ishga Tushirish Yo'riqnomasi

### 1-Qadam: `.env` Faylini Sozlash
`.env` faylini oching va ma'lumotlarni kiriting:

```env
BOT_TOKEN=7777777777:AAEE... # Telegram BotFather tokeningiz
ADMIN_USERNAME=bakhridd1n_dev # Sizning Telegram username'ingiz
GROQ_API_KEY=gsk_... # Ovozni matnga o'girish uchun (console.groq.com - bepul)
```

### 2-Qadam: Botni Ishga Tushirish
Virtual muhit (venv) orqali botni ishga tushiring:

```bash
./venv/bin/python main.py
```

---

## 🛠️ Loyiha Fayllari Tuzilishi

* `main.py` — Asosiy ishga tushiruvchi fayl.
* `config.py` — Bot sozlamalari.
* `database/` — SQLite baza va async SQLALchemy modellar.
* `services/downloader.py` — `yt-dlp` orqali video yuklash xizmati.
* `services/music_extractor.py` — Videodan MP3 ajratish xizmati.
* `services/whisper.py` — Groq/OpenAI Whisper audio matn xizmati.
* `handlers/` — Botning barcha buyruq va xabarlar ishlovchilari.
