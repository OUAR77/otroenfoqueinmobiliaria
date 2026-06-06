import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
SITE_NAME = "Otro Enfoque Inmobiliaria"
SITE_URL = os.getenv("SITE_URL", "http://localhost:8022")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "614234064")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
