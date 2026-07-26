import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "bakhridd1n_dev")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
INSTAGRAM_COOKIE = os.getenv("INSTAGRAM_COOKIE", "")

PAYME_PROVIDER_TOKEN = os.getenv("PAYME_PROVIDER_TOKEN", "")
CLICK_PROVIDER_TOKEN = os.getenv("CLICK_PROVIDER_TOKEN", "")
MONTHLY_SUB_PRICE = 15000

# Majburiy obuna kanali
REQUIRED_CHANNEL = "@backend_dev1"

# Bepul foydalanuvchi limitlari
FREE_VIDEO_LIMIT = 3
FREE_VOICE_LIMIT = 3
RESET_LIMIT_HOURS = 48
LIMIT_RESET_HOURS = 48
