# main.py
# Main entry point for the CognitoCoreMk1 AI Assistant with Jarvis-like interface using Pygame.

import sys
import logging
import traceback
import threading
import time
import numpy as np
import pygame
import math
import pyaudio
import struct
import queue
import colorsys
from pygame import gfxdraw

# --- Project Specific Imports ---
# These imports assume the existence of corresponding files/modules
try:
    import config  # Handles configuration loading (API keys, settings)
    import voice_io  # Handles voice input (listening) and output (speaking)
    import agent     # Handles core logic, NLP, tool use, communication
except ImportError as e:
    print(f"Error: Failed to import necessary project modules: {e}")
    print("Please ensure config.py, voice_io.py, and agent.py exist and are accessible.")
    sys.exit(1)

# --- Configuration ---
# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler("cognito_core.log"),
        logging.StreamHandler(sys.stdout) # Also print logs to console
    ]
)

# Define keywords that will trigger the assistant to stop listening
EXIT_COMMANDS = {"goodbye", "exit", "quit", "stop listening", "power down", "go to bed mk1"}
STOP_LISTENING_COMMAND = "over and out"
SHUTDOWN_COMMAND = "go to bed mk1"

# Audio visualization constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# GUI Colors and dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
BACKGROUND_COLOR = (10, 10, 15)  # Dark blue-black
TEXT_COLOR = (0, 191, 255)  # Jarvis blue
USER_TEXT_COLOR = (255, 69, 0)  # User message color
VISUALIZATION_COLOR = (0, 191, 255)
FONT_NAME = "couriernew"  # Default font name - will be replaced with available system font

class AudioProcessor:
    """Handles audio capture and processing for visualization"""
    def __init__(self, callback):
        self.audio_callback = callback
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        self.audio_data = np.zeros(CHUNK)
        self.audio_queue = queue.Queue(maxsize=10)
    
    def start(self):
        """Start audio capture stream"""
        if self.stream is not None and not self.stream.is_stopped():
            return
        
        self.is_running = True
        self.stream = self.pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._audio_callback
        )
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback from PyAudio stream - processes incoming audio data"""
        try:
            # Convert binary data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            
            # Normalize to values between -1 and 1
            audio_data = audio_data / 32768.0
            
            # Put in queue for the main thread to process
            if not self.audio_queue.full():
                self.audio_queue.put(audio_data)
            
            # If we have a callback, call it with the data
            if self.audio_callback:
                self.audio_callback(audio_data)
        except Exception as e:
            logging.error(f"Error in audio callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def stop(self):
        """Stop audio capture"""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.is_running = False
    
    def get_latest_audio(self):
        """Get the latest audio data from the queue"""
        if not self.audio_queue.empty():
            self.audio_data = self.audio_queue.get()
        return self.audio_data
    
    def cleanup(self):
        """Clean up PyAudio resources"""
        self.stop()
        self.pa.terminate()


class JarvisInterface:
    """Graphical user interface for the JARVIS-like assistant using Pygame"""
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CognitoCoreMk1 - JARVIS Interface")
        
        # Find available system fonts similar to what we need
        available_fonts = pygame.font.get_fonts()
        self.font_name = FONT_NAME if FONT_NAME.lower() in available_fonts else pygame.font.get_default_font()
        
        # Setup display and fonts
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont(self.font_name, 24, bold=True)
        self.text_font = pygame.font.SysFont(self.font_name, 18)
        self.status_font = pygame.font.SysFont(self.font_name, 16)
        
        # Initialize audio processor
        self.audio_processor = AudioProcessor(self.on_audio_data)
        
        # Conversation history
        self.conversation = []
        self.max_conversation_lines = 15  # Maximum number of lines to display
        
        # Visual elements
        self.reactor_x = WINDOW_WIDTH // 3
        self.reactor_y = WINDOW_HEIGHT // 2
        self.reactor_size = 150
        self.reactor_pulse = 0
        self.spectrum_height = 100
        
        # Animation variables
        self.animation_counter = 0
        self.last_audio_level = 0
        self.audio_data = np.zeros(CHUNK)
        
        # Status
        self.status_message = "SYSTEM READY"
        self.is_listening = False
        self.is_speaking = False
        self.is_processing = False
        self.is_active = True  # Controls if system is generally active or in "sleep" mode
        
        # Start audio processing for visualizations
        self.audio_processor.start()
    
    def on_audio_data(self, audio_data):
        """Callback for new audio data"""
        self.audio_data = audio_data
        # Calculate audio level for animations
        self.last_audio_level = np.abs(audio_data).mean() * 5.0  # Scale factor
    
    def update(self):
        """Update interface state"""
        # Update animation counter
        self.animation_counter += 1
        self.reactor_pulse = (self.reactor_pulse + 1) % 360
        
        # Get latest audio data for visualization
        self.audio_data = self.audio_processor.get_latest_audio()
    
    def draw_reactor(self):
        """Draw the Jarvis-like reactor visualization"""
        # Calculate pulse effect
        pulse = abs(math.sin(self.reactor_pulse / 180.0 * math.pi))
        pulse_factor = 1.0 + (pulse * 0.2)  # Pulse between 1.0 and 1.2 times size
        
        # Increase size if speaking or processing
        if self.is_speaking or self.is_processing:
            pulse_factor *= 1.2
            pulse_intensity = self.last_audio_level * 5
        else:
            pulse_intensity = pulse * 0.5
        
        # If system is in sleep mode, dim the reactor
        if not self.is_active:
            dim_factor = 0.3  # Dim to 30% brightness
        else:
            dim_factor = 1.0
        
        # Draw reactor rings
        ring_count = 5
        for i in range(ring_count):
            size = (ring_count - i) * (self.reactor_size / ring_count) * pulse_factor
            ring_alpha = int(255 * dim_factor * (0.5 + 0.5 * (ring_count - i) / ring_count))
            ring_color = (
                min(255, int(TEXT_COLOR[0] * dim_factor * (1 + pulse_intensity * 0.5))),
                min(255, int(TEXT_COLOR[1] * dim_factor * (1 + pulse_intensity * 0.2))),
                min(255, int(TEXT_COLOR[2] * dim_factor))
            )
            
            # Draw anti-aliased circle
            gfxdraw.aacircle(
                self.screen, 
                self.reactor_x, 
                self.reactor_y, 
                int(size),
                (*ring_color, ring_alpha)
            )
            
            # Only fill inner circles
            if i >= ring_count - 2:
                glow_alpha = int(100 * pulse * dim_factor)
                gfxdraw.filled_circle(
                    self.screen,
                    self.reactor_x,
                    self.reactor_y,
                    int(size),
                    (*ring_color, glow_alpha)
                )
        
        # Draw core
        core_size = 20 * pulse_factor
        core_color = (
            int(TEXT_COLOR[0] * dim_factor),
            int(TEXT_COLOR[1] * dim_factor),
            int(TEXT_COLOR[2] * dim_factor)
        )
        gfxdraw.filled_circle(
            self.screen,
            self.reactor_x,
            self.reactor_y,
            int(core_size),
            core_color
        )
        
        # Draw audio waveform around the reactor (only if active)
        if self.is_active and len(self.audio_data) > 0:
            for i in range(0, len(self.audio_data), 8):  # Sample every 8th point for performance
                angle = 2 * math.pi * i / len(self.audio_data)
                amplitude = self.audio_data[i] * 100 * pulse_factor  # Scale amplitude
                
                # Calculate start and end points for the line
                inner_radius = self.reactor_size * 1.2
                outer_radius = inner_radius + amplitude
                
                start_x = self.reactor_x + inner_radius * math.cos(angle)
                start_y = self.reactor_y + inner_radius * math.sin(angle)
                
                end_x = self.reactor_x + outer_radius * math.cos(angle)
                end_y = self.reactor_y + outer_radius * math.sin(angle)
                
                # Draw line with thickness based on amplitude
                pygame.draw.line(
                    self.screen,
                    core_color,
                    (start_x, start_y),
                    (end_x, end_y),
                    max(1, int(abs(amplitude) / 10))
                )
    
    def draw_spectrum(self):
        """Draw audio spectrum visualization"""
        if not self.is_active:
            return  # Don't draw spectrum in sleep mode
            
        if len(self.audio_data) > 0:
            # Calculate FFT for spectrum display
            spectrum = np.abs(np.fft.rfft(self.audio_data)) / len(self.audio_data)
            
            # Logarithmically scale frequencies for better visualization
            spectrum = np.log10(spectrum + 1) * 10
            
            # Number of frequency bins to display
            num_bins = min(64, len(spectrum) // 2)
            spectrum = spectrum[:num_bins]
            
            # Calculate positions and dimensions
            bar_width = 8
            bar_spacing = 2
            total_width = num_bins * (bar_width + bar_spacing)
            start_x = self.reactor_x - total_width // 2
            base_y = self.reactor_y + self.reactor_size * 2
            
            # Draw each frequency bin as a bar
            for i, magnitude in enumerate(spectrum):
                # Scale magnitude and add pulse effect
                height = min(self.spectrum_height, int(magnitude * 5 * (1 + self.last_audio_level)))
                
                # Calculate color based on frequency (blue to cyan gradient)
                hue = 0.55 + (i / num_bins) * 0.1  # Range from 0.55 (blue) to 0.65 (cyan)
                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, 1.0)]
                
                # Draw the bar
                x = start_x + i * (bar_width + bar_spacing)
                rect = pygame.Rect(x, base_y - height, bar_width, height)
                pygame.draw.rect(self.screen, (r, g, b), rect)
                
                # Add glow effect with semi-transparent overlay
                glow_rect = pygame.Rect(x-1, base_y - height - 1, bar_width + 2, height + 2)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (r, g, b, 100), glow_surf.get_rect())
                self.screen.blit(glow_surf, glow_rect)
    
    def draw_conversation(self):
        """Draw the conversation history"""
        # Title
        title_color = TEXT_COLOR if self.is_active else (TEXT_COLOR[0]//2, TEXT_COLOR[1]//2, TEXT_COLOR[2]//2)
        title_surface = self.title_font.render("CONVERSATION LOG", True, title_color)
        self.screen.blit(title_surface, (WINDOW_WIDTH - 400, 30))
        
        # Draw divider line
        pygame.draw.line(
            self.screen,
            title_color,
            (WINDOW_WIDTH - 420, 60),
            (WINDOW_WIDTH - 20, 60),
            1
        )
        
        # Draw conversation log
        y_pos = 80
        line_height = 24
        
        # Only show the most recent messages that will fit
        visible_messages = self.conversation[-self.max_conversation_lines:] if len(self.conversation) > self.max_conversation_lines else self.conversation
        
        for speaker, message in visible_messages:
            # Choose color based on speaker
            color = USER_TEXT_COLOR if speaker == "User" else TEXT_COLOR
            
            # If in sleep mode, dim the colors
            if not self.is_active:
                color = (color[0]//2, color[1]//2, color[2]//2)
                
            # Render speaker label
            speaker_surface = self.text_font.render(f"{speaker}:", True, color)
            self.screen.blit(speaker_surface, (WINDOW_WIDTH - 400, y_pos))
            y_pos += line_height
            
            # Wrap and render message
            # Split message into words and recombine into lines that fit
            words = message.split()
            lines = []
            current_line = []
            max_width = 360
            
            for word in words:
                test_line = current_line + [word]
                test_width = self.text_font.size(" ".join(test_line))[0]
                
                if test_width <= max_width:
                    current_line = test_line
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(" ".join(current_line))
            
            # Render each line
            for line in lines:
                text_surface = self.text_font.render(line, True, color)
                self.screen.blit(text_surface, (WINDOW_WIDTH - 380, y_pos))
                y_pos += line_height
            
            # Add spacing between messages
            y_pos += 5
    
    def draw_status(self):
        """Draw system status indicators"""
        # Status area background
        status_rect = pygame.Rect(20, WINDOW_HEIGHT - 50, WINDOW_WIDTH - 40, 30)
        pygame.draw.rect(self.screen, (20, 20, 30), status_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR if self.is_active else (TEXT_COLOR[0]//2, TEXT_COLOR[1]//2, TEXT_COLOR[2]//2), status_rect, 1)
        
        # Status indicators
        status_text = f"STATUS: {self.status_message}"
        if self.is_listening:
            status_text += " | LISTENING"
        if self.is_speaking:
            status_text += " | SPEAKING"
        if self.is_processing:
            status_text += " | PROCESSING"
        if not self.is_active:
            status_text += " | SLEEP MODE"
        
        # Draw status text
        status_surface = self.status_font.render(status_text, True, TEXT_COLOR if self.is_active else (TEXT_COLOR[0]//2, TEXT_COLOR[1]//2, TEXT_COLOR[2]//2))
        self.screen.blit(status_surface, (30, WINDOW_HEIGHT - 40))
        
        # System time
        time_str = time.strftime("%H:%M:%S", time.localtime())
        time_surface = self.status_font.render(time_str, True, TEXT_COLOR if self.is_active else (TEXT_COLOR[0]//2, TEXT_COLOR[1]//2, TEXT_COLOR[2]//2))
        self.screen.blit(time_surface, (WINDOW_WIDTH - 100, WINDOW_HEIGHT - 40))
    
    def draw(self):
        """Draw the entire interface"""
        # Clear screen
        self.screen.fill(BACKGROUND_COLOR)
        
        # Draw visualization elements
        self.draw_reactor()
        self.draw_spectrum()
        
        # Draw conversation history
        self.draw_conversation()
        
        # Draw status bar
        self.draw_status()
        
        # Update display
        pygame.display.flip()
    
    def add_to_conversation(self, speaker, message):
        """Add a message to the conversation history"""
        self.conversation.append((speaker, message))
    
    def set_status(self, status, is_listening=False, is_speaking=False, is_processing=False):
        """Update the assistant's status"""
        self.status_message = status
        self.is_listening = is_listening
        self.is_speaking = is_speaking
        self.is_processing = is_processing
    
    def set_active_state(self, active):
        """Set active/sleep state of the interface"""
        self.is_active = active
        if active:
            self.status_message = "SYSTEM ACTIVATED"
        else:
            self.status_message = "SLEEP MODE"
    
    def cleanup(self):
        """Clean up resources before quitting"""
        self.audio_processor.cleanup()
        pygame.quit()


class MockAgent:
    """
    A mock agent class that simulates the interface for the AI agent.
    Only to be used if actual agent module is not available.
    """
    def __init__(self):
        self.last_response = None
        logging.warning("Using mock agent - actual NLP functionality is not available")
    
    def process_command(self, command):
        """Process a command and return a response"""
        self.last_response = f"I would process '{command}' if I were a real agent."
        return self.last_response
    
    def get_last_response(self):
        """Get the last response generated by the agent"""
        return self.last_response


def main():
    """
    Initializes components and runs the main interaction loop for the AI assistant.
    """
    logging.info("Initializing CognitoCoreMk1...")
    
    # Create the interface
    interface = JarvisInterface()
    
    try:
        # Initialize Voice Input/Output
        speech_processor = voice_io.VoiceIO()
        logging.info("Voice I/O initialized.")

        # Initialize the Agent
        try:
            ai_agent = agent.Agent()
            logging.info("AI Agent initialized.")
        except (ImportError, AttributeError) as e:
            logging.error(f"Failed to initialize Agent module: {e}")
            logging.warning("Using mock agent instead.")
            ai_agent = MockAgent()

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        logging.error(traceback.format_exc())
        print(f"Critical error during initialization: {e}. Exiting.")
        interface.cleanup()
        sys.exit(1)

    # Initial greeting
    greeting = "Cognito Core MK1 online and ready. How can I assist you?"
    logging.info(f"Assistant: {greeting}")
    interface.add_to_conversation("Assistant", greeting)
    
    # Background threads for voice processing
    speak_thread = None
    listen_thread = None
    process_thread = None
    
    # Function to check if all active threads have completed
    def all_threads_complete():
        """Check if all processing threads have completed"""
        return (not speak_thread or not speak_thread.is_alive()) and \
               (not listen_thread or not listen_thread.is_alive()) and \
               (not process_thread or not process_thread.is_alive())
    
    def speak_in_background(text):
        """Function to speak text in a background thread"""
        interface.set_status("Speaking", is_speaking=True)
        speech_processor.speak(text)
        interface.set_status("Ready")
    
    def listen_in_background():
        """Function to listen for commands in a background thread"""
        interface.set_status("Listening", is_listening=True)
        user_input = speech_processor.listen()
        interface.set_status("Ready")
        return user_input
    
    def process_in_background(text):
        """Function to process user commands in a background thread"""
        interface.set_status("Processing", is_processing=True)
        response = ai_agent.process_command(text)
        interface.set_status("Ready")
        return response

    # Create an initial speech thread to speak the greeting
    speak_thread = threading.Thread(target=speak_in_background, args=(greeting,))
    speak_thread.daemon = True
    speak_thread.start()
    
    # Create a flag to track if listening should start automatically
    start_listening = True
    
    # --- Main Interaction Loop ---
    logging.info("Starting interaction loop. Listening for commands...")
    running = True
    
    while running:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Space key triggers listening
                    if all_threads_complete():
                        start_listening = True
                elif event.key == pygame.K_s:
                    # 'S' key toggles sleep/active mode
                    if all_threads_complete():
                        interface.set_active_state(not interface.is_active)
                        if interface.is_active:
                            speak_thread = threading.Thread(target=speak_in_background, args=("System activated and ready for commands.",))
                            speak_thread.daemon = True
                            speak_thread.start()
                        else:
                            speak_thread = threading.Thread(target=speak_in_background, args=("Entering sleep mode.",))
                            speak_thread.daemon = True
                            speak_thread.start()
        
        # Update interface state
        interface.update()
        
        # Draw the interface
        interface.draw()
        
        # Only process voice interactions if system is active
        if interface.is_active:
            # Start listening when previous threads are done
            if start_listening and all_threads_complete():
                listen_thread = threading.Thread(target=listen_in_background)
                listen_thread.daemon = True
                listen_thread.start()
                start_listening = False
                
                # Wait a bit before checking for results
                time.sleep(0.1)
            
            # Check if listening is complete and process the result
            if listen_thread and not listen_thread.is_alive() and not process_thread:
                user_input = speech_processor.get_last_input()
                
                if user_input:
                    logging.info(f"User said: {user_input}")
                    interface.add_to_conversation("User", user_input)
                    
                    # Check for exit command
                    if any(cmd in user_input.lower() for cmd in EXIT_COMMANDS):
                        farewell = "Powering down. Goodbye!"
                        logging.info(f"Assistant: {farewell}")
                        interface.add_to_conversation("Assistant", farewell)
                        
                        # Speak farewell and then exit
                        speak_thread = threading.Thread(target=speak_in_background, args=(farewell,))
                        speak_thread.daemon = True
                        speak_thread.start()
                        
                        # Wait for speak thread to finish
                        speak_thread.join(timeout=5)
                        running = False
                    # Check for sleep command
                    elif STOP_LISTENING_COMMAND.lower() in user_input.lower():
                        sleep_msg = "Stopping active listening."
                        logging.info(f"Assistant: {sleep_msg}")
                        interface.add_to_conversation("Assistant", sleep_msg)
                        
                        # Speak sleep message
                        speak_thread = threading.Thread(target=speak_in_background, args=(sleep_msg,))
                        speak_thread.daemon = True
                        speak_thread.start()
                        
                        # Set to sleep mode
                        interface.set_active_state(False)
                    else:
                        # Process command in background
                        process_thread = threading.Thread(target=process_in_background, args=(user_input,))
                        process_thread.daemon = True
                        process_thread.start()
            
            # Check if processing is complete and speak the result
            if process_thread and not process_thread.is_alive() and not speak_thread:
                response = ai_agent.get_last_response()
                
                if response:
                    logging.info(f"Agent response: {response}")
                    interface.add_to_conversation("Assistant", response)
                    
                    # Speak the response
                    speak_thread = threading.Thread(target=speak_in_background, args=(response,))
                    speak_thread.daemon = True
                    speak_thread.start()
                else:
                    # Handle cases where the agent might not return a response
                    error_msg = "I encountered an issue processing that request."
                    logging.warning("Agent did not provide a response.")
                    interface.add_to_conversation("Assistant", error_msg)
                    
                    speak_thread = threading.Thread(target=speak_in_background, args=(error_msg,))
                    speak_thread.daemon = True
                    speak_thread.start()
                
                # Clear the process thread
                process_thread = None
                
                # Flag to start listening again after speaking is done
                start_listening = True
        
        # Cap the frame rate
        interface.clock.tick(60)

    logging.info("CognitoCoreMk1 shutting down.")
    interface.cleanup()
    print("Application has finished.")

if __name__ == "__main__":
    main()
