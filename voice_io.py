"""
Voice input/output functionality for CognitoCoreMk1
"""
import os
import time
import queue
import logging
import threading
import numpy as np
from typing import Optional, Callable, List, Dict, Any
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
from tempfile import NamedTemporaryFile
import pygame

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/voice_io.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("voice_io")

class SpeechRecognizer:
    """Handle speech recognition functionality"""
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        """
        Initialize speech recognizer
        
        Args:
            callback: Function to call when speech is recognized
        """
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = config.STT_ENERGY_THRESHOLD
        self.recognizer.pause_threshold = config.STT_PAUSE_THRESHOLD
        self.microphone = sr.Microphone()
        self.callback = callback
        self.listening = False
        self.listen_thread = None
        self.audio_data_queue = queue.Queue()
        self.audio_level = 0
        
        # Initialize background noise adjustment
        logger.info("Adjusting for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        logger.info("Ambient noise adjustment complete")
    
    def start_listening(self):
        """Start listening for voice input in a background thread"""
        if not self.listening:
            self.listening = True
            self.listen_thread = threading.Thread(target=self._listen_loop)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            logger.info("Voice recognition started")
            return True
        else:
            logger.warning("Already listening")
            return False
    
    def stop_listening(self):
        """Stop listening for voice input"""
        if self.listening:
            self.listening = False
            if self.listen_thread:
                self.listen_thread.join(timeout=2)
            logger.info("Voice recognition stopped")
            return True
        else:
            logger.warning("Not currently listening")
            return False
    
    def _listen_loop(self):
        """Background thread that continuously listens for speech"""
        while self.listening:
            try:
                with self.microphone as source:
                    logger.debug("Listening for speech...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                    
                    # Update audio level for visualization
                    self.audio_level = max(np.frombuffer(audio.frame_data, np.int16))
                    
                    # Add to queue
                    self.audio_data_queue.put(audio)
                    
                    # Process speech in another thread
                    threading.Thread(target=self._process_audio, args=(audio,)).start()
                    
            except sr.WaitTimeoutError:
                logger.debug("No speech detected in timeout period")
                continue
            except Exception as e:
                logger.error(f"Error in listen loop: {str(e)}")
                time.sleep(1)  # Prevent tight loop if there's an error
    
    def _process_audio(self, audio):
        """Process audio data and convert to text"""
        try:
            if config.STT_ENGINE == "google":
                text = self.recognizer.recognize_google(audio)
            elif config.STT_ENGINE == "whisper":
                import whisper
                # Save audio to temporary file
                with NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    temp_path = temp_audio.name
                    with open(temp_path, "wb") as f:
                        f.write(audio.get_wav_data())
                
                # Use OpenAI's Whisper model (local)
                model = whisper.load_model("base")
                result = model.transcribe(temp_path)
                text = result["text"]
                
                # Clean up
                os.remove(temp_path)
            else:
                text = self.recognizer.recognize_sphinx(audio)  # Fallback to offline
            
            logger.info(f"Recognized: {text}")
            
            # Check for wake words
            text_lower = text.lower()
            if any(wake_word in text_lower for wake_word in config.WAKE_WORDS):
                logger.info("Wake word detected!")
                # Extract command after wake word
                for wake_word in config.WAKE_WORDS:
                    if wake_word in text_lower:
                        command = text_lower.split(wake_word, 1)[1].strip()
                        if command and self.callback:
                            self.callback(command)
                        break
            
            # Check for shutdown phrases
            if any(shutdown_phrase in text_lower for shutdown_phrase in config.SHUTDOWN_PHRASES):
                logger.info("Shutdown phrase detected!")
                if self.callback:
                    self.callback("__shutdown__")
            
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
        except sr.RequestError as e:
            logger.error(f"Recognition service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing speech: {str(e)}")
    
    def get_audio_level(self) -> float:
        """Get current audio level for visualization"""
        return self.audio_level
    
    def get_audio_data(self) -> Optional[sr.AudioData]:
        """Get the next audio data from the queue if available"""
        try:
            return self.audio_data_queue.get_nowait()
        except queue.Empty:
            return None


class SpeechSynthesizer:
    """Handle text-to-speech functionality"""
    
    def __init__(self):
        """Initialize the speech synthesizer"""
        self.speaking = False
        self.speech_queue = queue.Queue()
        self.current_text = ""
        
        # Initialize TTS engine
        if config.TTS_ENGINE == "pyttsx3":
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', config.TTS_RATE)
            self.engine.setProperty('volume', config.TTS_VOLUME)
            
            # Set voice if specified
            if config.TTS_VOICE_ID != "0":
                self.engine.setProperty('voice', config.TTS_VOICE_ID)
            else:
                # Try to set a voice
                voices = self.engine.getProperty('voices')
                if voices:
                    self.engine.setProperty('voice', voices[0].id)
        
        # Start background thread
        self.tts_thread = threading.Thread(target=self._tts_loop)
        self.tts_thread.daemon = True
        self.tts_thread.start()
        
        # Initialize pygame for gTTS playback
        pygame.mixer.init()
        
        logger.info("Speech synthesizer initialized")
    
    def speak(self, text: str, priority: bool = False) -> bool:
        """
        Queue text to be spoken
        
        Args:
            text: Text to speak
            priority: If True, put at front of queue
            
        Returns:
            True if successfully queued
        """
        try:
            logger.info(f"Queueing speech: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            if priority:
                # Empty the queue and add the priority text
                while not self.speech_queue.empty():
                    try:
                        self.speech_queue.get_nowait()
                    except queue.Empty:
                        break
                self.speech_queue.put(text)
            else:
                self.speech_queue.put(text)
            
            return True
        except Exception as e:
            logger.error(f"Error queueing speech: {str(e)}")
            return False
    
    def _tts_loop(self):
        """Background thread that processes speech queue"""
        while True:
            try:
                # Get next text to speak
                text = self.speech_queue.get()
                self.current_text = text
                self.speaking = True
                
                if config.TTS_ENGINE == "pyttsx3":
                    self.engine.say(text)
                    self.engine.runAndWait()
                else:  # Use gTTS
                    with NamedTemporaryFile(suffix='.mp3', delete=False) as temp_speech:
                        temp_path = temp_speech.name
                    
                    tts = gTTS(text=text, lang='en', slow=False)
                    tts.save(temp_path)
                    
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to finish
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    # Clean up
                    os.remove(temp_path)
                
                self.speaking = False
                self.current_text = ""
                self.speech_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in TTS loop: {str(e)}")
                self.speaking = False
                time.sleep(1)  # Prevent tight loop on errors
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        return self.speaking
    
    def get_current_text(self) -> str:
        """Get the text currently being spoken"""
        return self.current_text
    
    def stop_speaking(self):
        """Stop current speech and clear queue"""
        # Clear the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        
        # Stop current speech
        if config.TTS_ENGINE == "pyttsx3":
            self.engine.stop()
        else:
            pygame.mixer.music.stop()
        
        self.speaking = False
        self.current_text = ""
        logger.info("Speech stopped")


class VoiceManager:
    """Manage speech recognition and synthesis"""
    
    def __init__(self, command_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize voice manager
        
        Args:
            command_callback: Function to call when a command is recognized
        """
        self.speech_recognizer = SpeechRecognizer(callback=command_callback)
        self.speech_synthesizer = SpeechSynthesizer()
        self.active = False
        logger.info("VoiceManager initialized")
    
    def activate(self) -> bool:
        """Activate voice interface"""
        if not self.active:
            self.active = True
            self.speech_recognizer.start_listening()
            self.speech_synthesizer.speak(f"{config.ASSISTANT_NAME} activated and ready.", priority=True)
            logger.info("Voice interface activated")
            return True
        else:
            logger.warning("Voice interface already active")
            return False
    
    def deactivate(self) -> bool:
        """Deactivate voice interface"""
        if self.active:
            self.active = False
            self.speech_synthesizer.speak("Voice interface shutting down.", priority=True)
            time.sleep(2)  # Give time to speak the shutdown message
            self.speech_recognizer.stop_listening()
            self.speech_synthesizer.stop_speaking()
            logger.info("Voice interface deactivated")
            return True
        else:
            logger.warning("Voice interface not active")
            return False
    
    def say(self, text: str, priority: bool = False) -> bool:
        """
        Speak text using the speech synthesizer
        
        Args:
            text: Text to speak
            priority: If True, speak immediately
            
        Returns:
            True if successfully queued
        """
        return self.speech_synthesizer.speak(text, priority)
    
    def is_listening(self) -> bool:
        """Check if voice recognition is active"""
        return self.speech_recognizer.listening
    
    def is_speaking(self) -> bool:
        """Check if currently speaking"""
        return self.speech_synthesizer.is_speaking()
    
    def get_audio_level(self) -> float:
        """Get current audio input level"""
        return self.speech_recognizer.get_audio_level()
    
    def get_current_speech(self) -> str:
        """Get text currently being spoken"""
        return self.speech_synthesizer.get_current_text()