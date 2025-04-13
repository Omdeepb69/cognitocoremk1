# voice_io.py
# Description: Manages all voice interaction for CognitoCoreMk1.
# Handles capturing audio input using SpeechRecognition/Whisper
# and synthesizing speech output using pyttsx3/gTTS.

import speech_recognition as sr
import pyttsx3
import logging
import sys
import time
import threading

# Attempt to import configuration, use defaults if not found
try:
    from config import (
        TTS_ENGINE_PREFERENCE,  # 'pyttsx3' or 'gtts' (gTTS not implemented here yet)
        PYTTSX3_RATE,
        PYTTSX3_VOLUME,
        PYTTSX3_VOICE_ID, # Optional: Set specific voice ID if known
        STT_ENGINE_PREFERENCE, # 'google', 'whisper', 'sphinx' (only google implemented here)
        MIC_INDEX, # Optional: Specify microphone index if needed
        ENERGY_THRESHOLD,
        PAUSE_THRESHOLD,
        PHRASE_TIME_LIMIT,
        LOG_LEVEL
    )
except ImportError:
    print("Warning: config.py not found or incomplete. Using default voice I/O settings.", file=sys.stderr)
    TTS_ENGINE_PREFERENCE = 'pyttsx3'
    PYTTSX3_RATE = 180
    PYTTSX3_VOLUME = 1.0
    PYTTSX3_VOICE_ID = None # Use default voice
    STT_ENGINE_PREFERENCE = 'google' # Default to Google Web Speech API
    MIC_INDEX = None # Use default microphone
    ENERGY_THRESHOLD = 300 # Default energy threshold for silence detection
    PAUSE_THRESHOLD = 0.8 # Default seconds of silence before considering phrase complete
    PHRASE_TIME_LIMIT = 10 # Default max seconds to listen for a phrase
    LOG_LEVEL = "INFO" # Default logging level

# --- Logging Setup ---
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
logging.basicConfig(
    level=log_level_map.get(LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Log to stdout
)
logger = logging.getLogger(__name__)

# --- Text-to-Speech (TTS) Initialization ---
tts_engine = None
if TTS_ENGINE_PREFERENCE.lower() == 'pyttsx3':
    try:
        tts_engine = pyttsx3.init()
        tts_engine.setProperty('rate', PYTTSX3_RATE)
        tts_engine.setProperty('volume', PYTTSX3_VOLUME)
        if PYTTSX3_VOICE_ID:
            # Attempt to set a specific voice ID if provided
            voices = tts_engine.getProperty('voices')
            voice_found = False
            for voice in voices:
                if voice.id == PYTTSX3_VOICE_ID:
                    tts_engine.setProperty('voice', voice.id)
                    voice_found = True
                    logger.info(f"pyttsx3 using configured voice ID: {PYTTSX3_VOICE_ID}")
                    break
            if not voice_found:
                 logger.warning(f"pyttsx3 voice ID '{PYTTSX3_VOICE_ID}' not found. Using default voice.")
        else:
            logger.info("pyttsx3 using default voice.")
        logger.info(f"pyttsx3 initialized successfully (Rate: {PYTTSX3_RATE}, Volume: {PYTTSX3_VOLUME}).")
    except Exception as e:
        logger.error(f"Failed to initialize pyttsx3 engine: {e}", exc_info=True)
        tts_engine = None
elif TTS_ENGINE_PREFERENCE.lower() == 'gtts':
    logger.warning("gTTS engine selected in config, but not yet implemented in voice_io.py. Falling back to pyttsx3 if available.")
    # Placeholder for potential future gTTS implementation
    # Requires 'pip install gTTS playsound'
    pass # Fallback handled by the 'speak' function if tts_engine is None

# --- Speech-to-Text (STT) Initialization ---
recognizer = sr.Recognizer()
recognizer.energy_threshold = ENERGY_THRESHOLD
recognizer.pause_threshold = PAUSE_THRESHOLD

# --- Control Variables ---
is_listening_active = False  # Flag to control continuous listening
listening_thread = None      # Thread for continuous listening
last_input = None            # Stores the last recognized input

# Constants for control phrases
STOP_PHRASE = "over and out"
SHUTDOWN_PHRASE = "go to bed mk1"
CONTROL_PHRASES = [STOP_PHRASE, SHUTDOWN_PHRASE]

# --- Core Functions ---

def speak(text: str):
    """
    Synthesizes the given text into speech using the configured TTS engine.

    Args:
        text (str): The text to be spoken.
    """
    if not text:
        logger.warning("Speak function called with empty text.")
        return

    logger.info(f"Speaking: '{text}'")
    if tts_engine and TTS_ENGINE_PREFERENCE.lower() == 'pyttsx3':
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error during speech synthesis: {e}", exc_info=True)
    # Add elif for gTTS here if implemented
    # elif TTS_ENGINE_PREFERENCE.lower() == 'gtts':
    #     try:
    #         # Implementation using gTTS and playsound
    #         from gtts import gTTS
    #         import os
    #         tts = gTTS(text=text, lang='en')
    #         filename = "temp_speech.mp3"
    #         tts.save(filename)
    #         # Use playsound or another library to play the audio
    #         # import playsound
    #         # playsound.playsound(filename)
    #         # os.remove(filename) # Clean up the temporary file
    #         logger.warning("gTTS playback not fully implemented (requires audio player like playsound).")
    #     except Exception as e:
    #         logger.error(f"gTTS error: {e}", exc_info=True)
    else:
        logger.error(f"No supported TTS engine ('{TTS_ENGINE_PREFERENCE}') is available or initialized.")
        # Fallback: Print to console if TTS fails
        print(f"Fallback TTS: {text}")


def listen(single_phrase=True) -> str | None:
    """
    Listens for audio input from the microphone and transcribes it into text
    using the configured STT engine.

    Args:
        single_phrase (bool): If True, listens for a single phrase and returns.
                             If False, listens continuously until stopped.

    Returns:
        str | None: The transcribed text, or None if an error occurred or
                    no speech was detected within the time limit.
    """
    global recognizer, last_input  # Allow modification for dynamic energy threshold adjustment

    # Check available microphones if index is not specified
    if MIC_INDEX is None:
        logger.debug(f"Available microphones: {sr.Microphone.list_microphone_names()}")
        # Using default microphone

    mic_kwargs = {"device_index": MIC_INDEX} if MIC_INDEX is not None else {}

    with sr.Microphone(**mic_kwargs) as source:
        if single_phrase:
            logger.info("Adjusting for ambient noise... Please wait.")
            try:
                # Adjust for ambient noise dynamically (optional but recommended)
                recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info(f"Ambient noise adjustment complete. Energy threshold: {recognizer.energy_threshold:.2f}")
                logger.info("Listening for command...")
                speak("Listening...") # Provide feedback to the user

                try:
                    # Listen for audio input with a timeout
                    audio = recognizer.listen(
                        source,
                        timeout=5, # Max time to wait for speech to start
                        phrase_time_limit=PHRASE_TIME_LIMIT # Max seconds of speech to record
                    )
                    logger.info("Audio captured, attempting recognition...")
                    
                    # Process the audio and return result
                    return process_audio(audio)

                except sr.WaitTimeoutError:
                    logger.warning("No speech detected within the timeout period.")
                    speak("I didn't hear anything.")
                    return None

            except Exception as e:
                handle_listening_error(e)
                return None
        else:
            # Continuous listening mode
            logger.info("Starting continuous listening mode...")
            try:
                # Adjust once at the beginning
                recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info(f"Continuous mode - ambient noise adjustment complete. Energy threshold: {recognizer.energy_threshold:.2f}")
                speak("Listening mode activated.")
                
                # Continue listening until the flag is set to False
                while is_listening_active:
                    try:
                        audio = recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=PHRASE_TIME_LIMIT
                        )
                        
                        # Process the audio
                        text = process_audio(audio)
                        
                        if text:
                            # Store the recognized text
                            last_input = text
                            
                            # Check for control phrases
                            if STOP_PHRASE in text.lower():
                                logger.info("Stop phrase detected. Stopping continuous listening.")
                                speak("Listening mode deactivated.")
                                return text
                            elif SHUTDOWN_PHRASE in text.lower():
                                logger.info("Shutdown phrase detected.")
                                return text
                    
                    except sr.WaitTimeoutError:
                        # Just continue listening on timeout
                        continue
                    
                    # Small delay to prevent CPU overload
                    time.sleep(0.1)
                
                logger.info("Continuous listening stopped externally.")
                return None
                
            except Exception as e:
                handle_listening_error(e)
                return None


def handle_listening_error(error):
    """Helper function to handle listening errors"""
    if isinstance(error, OSError):
        logger.error(f"Microphone OS Error: {error}. Check if microphone is connected/available.", exc_info=True)
        if "Invalid input device" in str(error) and MIC_INDEX is not None:
            logger.error(f"Specified MIC_INDEX {MIC_INDEX} might be incorrect.")
        elif "No Default Input Device Available" in str(error):
            logger.error("No default microphone found. Please ensure one is connected and configured.")
        speak("Sorry, I encountered a problem accessing the microphone.")
    else:
        logger.error(f"An unexpected error occurred during microphone setup or listening: {error}", exc_info=True)
        speak("Sorry, an unexpected error occurred while trying to listen.")


def process_audio(audio) -> str | None:
    """
    Process audio data using the configured STT engine.
    
    Args:
        audio: Audio data from recognizer.listen()
        
    Returns:
        str | None: Recognized text or None if recognition failed
    """
    # --- Perform Speech Recognition ---
    if STT_ENGINE_PREFERENCE.lower() == 'google':
        try:
            # Use Google Web Speech API for recognition
            text = recognizer.recognize_google(audio)
            logger.info(f"Google Web Speech recognized: '{text}'")
            return text.lower() # Return recognized text in lowercase
        except sr.UnknownValueError:
            logger.warning("Google Web Speech could not understand audio.")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Web Speech service; {e}", exc_info=True)
            speak("Sorry, I'm having trouble connecting to the speech recognition service.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Google Web Speech recognition: {e}", exc_info=True)
            speak("Sorry, an unexpected error occurred during speech recognition.")
            return None

    elif STT_ENGINE_PREFERENCE.lower() == 'whisper':
        logger.warning("Whisper STT selected but requires separate setup (API key or local model).")
        # Placeholder: Requires 'pip install openai-whisper' or using OpenAI API
        # Example (local model):
        # try:
        #     text = recognizer.recognize_whisper(audio, model="base.en") # Choose model size
        #     logger.info(f"Whisper recognized: '{text}'")
        #     return text.lower()
        # except sr.UnknownValueError:
        #     logger.warning("Whisper could not understand audio.")
        #     speak("Sorry, I couldn't understand what you said.")
        #     return None
        # except Exception as e: # Catch potential Whisper setup/runtime errors
        #     logger.error(f"Whisper recognition error: {e}", exc_info=True)
        #     speak("Sorry, there was an issue with the Whisper speech recognition.")
        #     return None
        speak("Whisper recognition is not fully configured in this version.")
        return None

    elif STT_ENGINE_PREFERENCE.lower() == 'sphinx':
        logger.warning("Sphinx STT selected. Requires 'pip install pocketsphinx'. Quality may vary.")
        # Requires offline model installation
        try:
            text = recognizer.recognize_sphinx(audio)
            logger.info(f"Sphinx recognized: '{text}'")
            return text.lower()
        except sr.UnknownValueError:
            logger.warning("Sphinx could not understand audio.")
            return None
        except sr.RequestError as e: # May occur if language models aren't found
            logger.error(f"Could not request results from Sphinx; {e}", exc_info=True)
            speak("Sorry, there seems to be an issue with the offline speech recognition setup.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Sphinx recognition: {e}", exc_info=True)
            speak("Sorry, an unexpected error occurred during offline speech recognition.")
            return None
    else:
        logger.error(f"Unsupported STT engine configured: {STT_ENGINE_PREFERENCE}")
        speak("Sorry, the configured speech recognition engine is not supported.")
        return None


def start_listening_thread():
    """Start a background thread for continuous listening"""
    global is_listening_active, listening_thread
    
    if listening_thread and listening_thread.is_alive():
        logger.warning("Listening thread is already active")
        return
    
    is_listening_active = True
    listening_thread = threading.Thread(target=listen, args=(False,))
    listening_thread.daemon = True
    listening_thread.start()
    logger.info("Started listening thread")


def stop_listening_thread():
    """Stop the continuous listening thread"""
    global is_listening_active
    is_listening_active = False
    logger.info("Stopping listening thread...")


def get_last_input():
    """Return the last recognized input"""
    global last_input
    result = last_input
    last_input = None
    return result


def prompt_for_next_task():
    """Ask the user what they want to do next"""
    speak("What would you like me to do next?")


def is_active():
    """Check if the listening thread is active"""
    global listening_thread, is_listening_active
    return is_listening_active and (listening_thread and listening_thread.is_alive())


# --- Main execution block for testing ---
if __name__ == "__main__":
    print("CognitoCoreMk1 Voice I/O Module Test")
    print("------------------------------------")

    # Test TTS
    print("\nTesting Text-to-Speech (TTS)...")
    try:
        speak("Hello! This is a test of the text to speech system.")
        speak(f"Using {TTS_ENGINE_PREFERENCE} engine.")
        print("TTS test completed.")
    except Exception as e:
        print(f"TTS test failed: {e}")

    # Test STT
    print("\nTesting Speech-to-Text (STT)...")
    print(f"Using {STT_ENGINE_PREFERENCE} engine.")
    print(f"Please say something clearly into the microphone within {PHRASE_TIME_LIMIT} seconds.")

    # Add a small delay before listening
    time.sleep(1)

    try:
        recognized_text = listen()
        if recognized_text:
            print(f"\nRecognition Result: '{recognized_text}'")
            speak(f"I think you said: {recognized_text}")
        else:
            print("\nNo text recognized or an error occurred.")
    except Exception as e:
        print(f"\nSTT test failed: {e}")
        logger.error("STT test failed in main block.", exc_info=True)

    print("\nVoice I/O test finished.")
