"""
Configuration settings for CognitoCoreMk1
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API keys and credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro"

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# WhatsApp configuration (via Twilio)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# Voice settings
TTS_ENGINE = os.getenv("TTS_ENGINE", "pyttsx3")  # Options: pyttsx3, gtts
TTS_VOICE_ID = os.getenv("TTS_VOICE_ID", "0")  # Default voice for pyttsx3
TTS_RATE = int(os.getenv("TTS_RATE", "170"))  # Speech rate for pyttsx3
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "0.9"))  # Volume for pyttsx3

# Speech recognition settings
STT_ENGINE = os.getenv("STT_ENGINE", "google")  # Options: google, whisper
STT_ENERGY_THRESHOLD = int(os.getenv("STT_ENERGY_THRESHOLD", "4000"))
STT_PAUSE_THRESHOLD = float(os.getenv("STT_PAUSE_THRESHOLD", "0.8"))

# UI Settings
UI_WIDTH = int(os.getenv("UI_WIDTH", "1280"))
UI_HEIGHT = int(os.getenv("UI_HEIGHT", "720"))
UI_TITLE = os.getenv("UI_TITLE", "CognitoCoreMk1")
UI_THEME_COLOR = (0, 180, 210)  # Jarvis-like blue color
UI_BACKGROUND_COLOR = (0, 10, 30)  # Dark blue/black background

# System paths
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
LOG_DIR = os.getenv("LOG_DIR", "./logs")

# Create directories if they don't exist
for directory in [CACHE_DIR, LOG_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Assistant personality
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "CognitoCoreMk1")
ASSISTANT_PERSONA = os.getenv("ASSISTANT_PERSONA", """
You are CognitoCoreMk1, a JARVIS-like AI assistant with a helpful but slightly sarcastic personality.
You're efficient, witty, and speak in a conversational tone. You're knowledgeable but willing to admit when
you don't know something. Occasionally add subtle humor to your responses. Keep your responses
concise unless detailed information is specifically requested.
""")

# Activation phrases
WAKE_WORDS = ["hey core", "hey cognito", "okay core", "wake up"]
SHUTDOWN_PHRASES = ["shutdown", "shut down", "power off", "goodbye"]