# config.py
# Configuration loader for CognitoCoreMk1

import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from a .env file if it exists
# This is crucial for keeping sensitive information like API keys secure
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logging.info(".env file loaded successfully.")
else:
    logging.warning(".env file not found. Relying on system environment variables.")

def get_env_variable(var_name: str, default: str = None, required: bool = False) -> str:
    """
    Retrieves an environment variable.

    Args:
        var_name (str): The name of the environment variable.
        default (str, optional): The default value if the variable is not found. Defaults to None.
        required (bool, optional): If True, raises an error if the variable is not found and no default is provided. Defaults to False.

    Returns:
        str: The value of the environment variable or the default value.

    Raises:
        ValueError: If the variable is required but not found and no default is set.
    """
    value = os.getenv(var_name, default)
    if required and value is None:
        error_msg = f"Missing required environment variable: '{var_name}'. Please set it in your .env file or system environment."
        logging.error(error_msg)
        raise ValueError(error_msg)
    if value is None:
        logging.warning(f"Environment variable '{var_name}' not set. Using default value: {default}")
    return value

# --- Gemini API Configuration ---
GEMINI_API_KEY = get_env_variable("GEMINI_API_KEY", required=True)
# Specify the Gemini model to use (e.g., 'gemini-1.5-flash', 'gemini-1.5-pro')
GEMINI_MODEL_NAME = get_env_variable("GEMINI_MODEL_NAME", default="gemini-1.5-flash")

# --- Email Configuration (SMTP) ---
SMTP_SERVER = get_env_variable("SMTP_SERVER", required=False) # Required only if email sending is used
SMTP_PORT_STR = get_env_variable("SMTP_PORT", default="587") # Default SMTP TLS port
SMTP_PORT = 587 # Default value if conversion fails
try:
    SMTP_PORT = int(SMTP_PORT_STR)
except (ValueError, TypeError):
     logging.warning(f"Invalid SMTP_PORT value '{SMTP_PORT_STR}'. Using default port 587.")

EMAIL_USER = get_env_variable("EMAIL_USER", required=False) # Required only if email sending is used
EMAIL_PASS = get_env_variable("EMAIL_PASS", required=False) # Required only if email sending is used

# --- WhatsApp Configuration (Optional - Example using Twilio) ---
# Uncomment and configure if using Twilio for WhatsApp
# TWILIO_ACCOUNT_SID = get_env_variable("TWILIO_ACCOUNT_SID", required=False)
# TWILIO_AUTH_TOKEN = get_env_variable("TWILIO_AUTH_TOKEN", required=False)
# TWILIO_WHATSAPP_NUMBER = get_env_variable("TWILIO_WHATSAPP_NUMBER", required=False) # e.g., 'whatsapp:+14155238886'
# RECIPIENT_WHATSAPP_NUMBER = get_env_variable("RECIPIENT_WHATSAPP_NUMBER", required=False) # e.g., 'whatsapp:+1...'

# --- Speech Recognition (Whisper) Configuration ---
# Options: 'tiny', 'base', 'small', 'medium', 'large'
# Smaller models are faster but less accurate. 'base' or 'small' recommended for decent performance.
WHISPER_MODEL_NAME = get_env_variable("WHISPER_MODEL_NAME", default="base")
# Set to True to use the English-only model version (e.g., 'base.en') for potentially better performance on English speech
WHISPER_USE_ENGLISH_ONLY_MODEL = get_env_variable("WHISPER_USE_ENGLISH_ONLY_MODEL", default="True").lower() == 'true'
if WHISPER_USE_ENGLISH_ONLY_MODEL and not WHISPER_MODEL_NAME.endswith('.en'):
    WHISPER_MODEL_NAME += ".en"

# --- Text-to-Speech (TTS) Configuration ---
# Choose between 'pyttsx3' (offline, basic) and 'gTTS' (online, Google voices)
TTS_ENGINE = get_env_variable("TTS_ENGINE", default="pyttsx3").lower()

# Settings specific to pyttsx3
PYTTSX3_RATE_STR = get_env_variable("PYTTSX3_RATE", default="180") # Words per minute
PYTTSX3_VOLUME_STR = get_env_variable("PYTTSX3_VOLUME", default="1.0") # Float between 0.0 and 1.0
PYTTSX3_VOICE_INDEX_STR = get_env_variable("PYTTSX3_VOICE_INDEX", default="0") # Index of the voice to use (depends on system)

# Convert pyttsx3 settings to appropriate types with error handling
try:
    pyttsx3_rate = int(PYTTSX3_RATE_STR)
except (ValueError, TypeError):
    logging.warning(f"Invalid PYTTSX3_RATE value '{PYTTSX3_RATE_STR}'. Using default 180.")
    pyttsx3_rate = 180

try:
    pyttsx3_volume = float(PYTTSX3_VOLUME_STR)
    if not (0.0 <= pyttsx3_volume <= 1.0):
        raise ValueError("Volume must be between 0.0 and 1.0")
except (ValueError, TypeError):
    logging.warning(f"Invalid PYTTSX3_VOLUME value '{PYTTSX3_VOLUME_STR}'. Using default 1.0.")
    pyttsx3_volume = 1.0

try:
    pyttsx3_voice_index = int(PYTTSX3_VOICE_INDEX_STR)
except (ValueError, TypeError):
    logging.warning(f"Invalid PYTTSX3_VOICE_INDEX value '{PYTTSX3_VOICE_INDEX_STR}'. Using default 0.")
    pyttsx3_voice_index = 0

TTS_ENGINE_SETTINGS = {
    'engine': TTS_ENGINE,
    'pyttsx3': {
        'rate': pyttsx3_rate,
        'volume': pyttsx3_volume,
        'voice_index': pyttsx3_voice_index,
    },
    'gtts': {
        'lang': get_env_variable("GTTS_LANG", default="en"), # Language for gTTS
        'tld': get_env_variable("GTTS_TLD", default="com"), # Top-level domain for Google Translate URL
    }
}

# --- Assistant Personality ---
ASSISTANT_NAME = get_env_variable("ASSISTANT_NAME", default="Cognito")
# Base prompt defining the assistant's personality and core instructions
# This can be customized extensively in the .env file
ASSISTANT_SYSTEM_PROMPT = get_env_variable(
    "ASSISTANT_SYSTEM_PROMPT",
    default=(
        f"You are {ASSISTANT_NAME}, a highly advanced AI assistant inspired by JARVIS. "
        "Your personality is witty, helpful, and occasionally sarcastic, but always professional and efficient. "
        "You can access real-time information, control system functions, and manage communications as requested. "
        "You should strive to understand user intent, ask clarifying questions if needed, and execute tasks autonomously when possible. "
        "Maintain context in conversations. Use humor appropriately. Do not reveal you are an AI model unless specifically asked. "
        "You have access to tools for web browsing, system commands, and sending emails."
    )
)

# --- Other Constants ---
MAX_CONVERSATION_HISTORY = int(get_env_variable("MAX_CONVERSATION_HISTORY", default="10")) # Number of past exchanges to remember
WEB_REQUEST_TIMEOUT = int(get_env_variable("WEB_REQUEST_TIMEOUT", default="10")) # Seconds before web requests time out

# --- Validation for Email ---
# Warn if email functionality might be used but configuration is incomplete
if (EMAIL_USER or EMAIL_PASS or SMTP_SERVER != get_env_variable("SMTP_SERVER", default=None)) and not (EMAIL_USER and EMAIL_PASS and SMTP_SERVER):
     logging.warning("Email settings (EMAIL_USER, EMAIL_PASS, SMTP_SERVER) seem partially configured. Email functionality might fail.")


# Log the loaded configuration (excluding sensitive keys)
logging.info("Configuration loaded:")
logging.info(f"  GEMINI_MODEL_NAME: {GEMINI_MODEL_NAME}")
logging.info(f"  SMTP_SERVER: {SMTP_SERVER}")
logging.info(f"  SMTP_PORT: {SMTP_PORT}")
logging.info(f"  EMAIL_USER: {'Set' if EMAIL_USER else 'Not Set'}")
logging.info(f"  WHISPER_MODEL_NAME: {WHISPER_MODEL_NAME}")
logging.info(f"  TTS_ENGINE: {TTS_ENGINE_SETTINGS['engine']}")
logging.info(f"  ASSISTANT_NAME: {ASSISTANT_NAME}")
logging.info(f"  MAX_CONVERSATION_HISTORY: {MAX_CONVERSATION_HISTORY}")
logging.info(f"  WEB_REQUEST_TIMEOUT: {WEB_REQUEST_TIMEOUT}")

# --- End of Configuration ---