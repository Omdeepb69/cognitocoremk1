"""
CognitoCoreMk1 - Your Python-powered AI sidekick
Main application that ties all components together
"""

#just for the commit of the day
import os
import time
import threading
import logging
import argparse
import numpy as np
import pygame
from typing import Dict, Any, List, Optional

import config
from agent import CognitoAgent
from voice_io import VoiceManager
from tools import ToolManager
from ui import JarvisUI

# Create log directory if it doesn't exist
os.makedirs(config.LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

class CognitoCoreMk1:
    """Main application class for CognitoCoreMk1"""
    
    def __init__(self):
        """Initialize the application"""
        logger.info("Initializing CognitoCoreMk1...")
        
        # Initialize components
        self.ai_agent = CognitoAgent()
        self.tool_manager = ToolManager()
        self.voice_manager = VoiceManager(command_callback=self.process_voice_command)
        self.ui = JarvisUI()
        
        # Set button callbacks
        self.ui.set_button_callbacks(
            activate_callback=self.activate,
            deactivate_callback=self.deactivate,
            reset_callback=self.reset_conversation,
            sysinfo_callback=self.show_system_info
        )
        
        # Status flags
        self.running = False
        self.active = False
        
        # Initialize audio visualization data
        self.audio_level = 0
        self.waveform_data = [0] * 20
        self.spectrum_data = np.zeros(64)
        
        # Set up audio visualization update thread
        self.audio_vis_thread = None
        
        logger.info("CognitoCoreMk1 initialized")
    
    def start(self):
        """Start the application"""
        if not self.running:
            self.running = True
            
            # Start UI
            logger.info("Starting UI...")
            self.ui.start()
            
            # Start audio visualization thread
            self.audio_vis_thread = threading.Thread(target=self._update_audio_vis_loop)
            self.audio_vis_thread.daemon = True
            self.audio_vis_thread.start()
            
            # Welcome message
            welcome_msg = f"Welcome to {config.ASSISTANT_NAME}. Click Activate to start voice interface."
            self.ui.add_conversation_message('assistant', welcome_msg)
            
            logger.info("CognitoCoreMk1 started")
            return True
        else:
            logger.warning("Already running")
            return False
    
    def stop(self):
        """Stop the application"""
        if self.running:
            self.running = False
            
            # Deactivate voice if active
            if self.active:
                self.deactivate()
            
            # Stop UI
            self.ui.stop()
            
            # Stop audio visualization thread
            if self.audio_vis_thread:
                self.audio_vis_thread.join(timeout=2)
            
            logger.info("CognitoCoreMk1 stopped")
            return True
        else:
            logger.warning("Not running")
            return False
    
    def activate(self):
        """Activate voice interface"""
        if not self.active:
            self.active = True
            
            # Activate voice manager
            self.voice_manager.activate()
            
            # Update UI
            self.ui.update_status(
                listening=self.voice_manager.is_listening(),
                speaking=self.voice_manager.is_speaking(),
                processing=False
            )
            
            # Add message to conversation
            self.ui.add_conversation_message('assistant', f"{config.ASSISTANT_NAME} activated and ready.")
            
            logger.info("Voice interface activated")
            return True
        else:
            logger.warning("Already active")
            return False
    
    def deactivate(self):
        """Deactivate voice interface"""
        if self.active:
            self.active = False
            
            # Deactivate voice manager
            self.voice_manager.deactivate()
            
            # Update UI
            self.ui.update_status(
                listening=False,
                speaking=False,
                processing=False
            )
            
            # Add message to conversation
            self.ui.add_conversation_message('assistant', "Voice interface deactivated.")
            
            logger.info("Voice interface deactivated")
            return True
        else:
            logger.warning("Not active")
            return False
    
    def reset_conversation(self):
        """Reset the conversation"""
        # Reset agent conversation
        self.ai_agent.reset_conversation()
        
        # Reset UI conversation (keep the last assistant message)
        self.ui.conversation = []
        self.ui.add_conversation_message('assistant', "Conversation history reset.")
        
        logger.info("Conversation reset")
    
    def show_system_info(self):
        """Show system information"""
        # Get system info
        system_info = self.tool_manager.system_tools.get_system_info()
        
        # Format info into a readable message
        if "error" in system_info:
            info_message = f"Error getting system info: {system_info['error']}"
        else:
            cpu_info = system_info["cpu"]
            memory_info = system_info["memory"]
            disk_info = system_info["disk"]
            
            info_message = (
                f"System Info:\n"
                f"CPU: {cpu_info['cores']} cores at {cpu_info['percent']}% usage\n"
                f"Memory: {memory_info['percent']}% used ({memory_info['available'] // (1024*1024)} MB free)\n"
                f"Disk: {disk_info['percent']}% used ({disk_info['free'] // (1024*1024*1024)} GB free)"
            )
        
        # Display in UI and speak
        self.ui.add_conversation_message('assistant', info_message)
        if self.active:
            self.voice_manager.say(info_message)
    
    def process_voice_command(self, command: str):
        """
        Process voice command from user
        
        Args:
            command: Voice command text
        """
        if command == "__shutdown__":
            # Handle shutdown command
            self.deactivate()
            return
        
        logger.info(f"Processing command: {command}")
        
        # Update UI
        self.ui.add_conversation_message('user', command)
        self.ui.update_status(
            listening=self.voice_manager.is_listening(),
            speaking=False,
            processing=True
        )
        
        # Process command in separate thread to avoid blocking UI
        threading.Thread(target=self._process_command_thread, args=(command,)).start()
    
    def _process_command_thread(self, command: str):
        """Background thread for processing commands"""
        try:
            # Determine intent
            intent = self.ai_agent.determine_intent(command)
            logger.info(f"Intent determined: {intent['intent']} (confidence: {intent['confidence']})")
            
            response = ""
            
            # Handle based on intent
            if intent['intent'] == "web_search" and intent['confidence'] > 0.6:
                # Execute web search
                search_results = self.tool_manager.web_tools.search(command)
                context = {"search_results": search_results}
                response = self.ai_agent.process_query(command, context)
                
            elif intent['intent'] == "system_command" and intent['confidence'] > 0.7:
                # Get tool instructions
                tool_params = self.ai_agent.get_tool_instructions("system", command)
                
                # Execute system operation based on params
                if "file_operation" in tool_params:
                    result = self.tool_manager.system_tools.file_operation(
                        tool_params.get("operation"), 
                        tool_params.get("path")
                    )
                else:
                    # Default to system info
                    result = self.tool_manager.system_tools.get_system_info()
                
                context = {"system_result": result}
                response = self.ai_agent.process_query(command, context)
                
            elif intent['intent'] == "send_email" and intent['confidence'] > 0.7:
                # Get email parameters
                email_params = self.ai_agent.get_tool_instructions("email", command)
                
                # Let user know we're preparing an email
                self.ui.add_conversation_message(
                    'assistant', 
                    "I'll help you draft that email. Let me prepare it..."
                )
                
                if self.active:
                    self.voice_manager.say("I'll help you draft that email. Let me prepare it...")
                
                # Process with email context
                context = {"email_request": True}
                response = self.ai_agent.process_query(command, context)
                
            else:
                # General question, no special tools needed
                response = self.ai_agent.process_query(command)
            
            # Update UI with response
            self.ui.add_conversation_message('assistant', response)
            
            # Speak response if active
            if self.active:
                self.voice_manager.say(response)
                
            # Update UI status
            self.ui.update_status(
                listening=self.voice_manager.is_listening(),
                speaking=self.voice_manager.is_speaking(),
                processing=False
            )
            
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            error_msg = f"I'm sorry, I encountered an error processing your request: {str(e)}"
            
            # Update UI with error
            self.ui.add_conversation_message('assistant', error_msg)
            
            # Speak error if active
            if self.active:
                self.voice_manager.say(error_msg)
                
            # Update UI status
            self.ui.update_status(
                listening=self.voice_manager.is_listening(),
                speaking=self.voice_manager.is_speaking(),
                processing=False
            )
    
    def _update_audio_vis_loop(self):
        """Update audio visualization data periodically"""
        while self.running:
            try:
                # Get audio level
                if self.voice_manager.is_listening():
                    level = min(1.0, self.voice_manager.get_audio_level() / 32768.0)  # Normalize
                else:
                    level = 0.0
                
                # Generate waveform data (simulated)
                waveform = []
                if self.voice_manager.is_listening():
                    for _ in range(5):
                        waveform.append(level * np.random.uniform(-1.0, 1.0))
                else:
                    waveform = [0.0] * 5
                
                # Generate spectrum data (simulated)
                spectrum = np.zeros(64)
                if self.voice_manager.is_listening():
                    for i in range(64):
                        # Create a peak in the middle frequencies when detecting audio
                        center = 32
                        distance = abs(i - center)
                        spectrum[i] = level * max(0, 1 - (distance / center) ** 2) * np.random.uniform(0.5, 1.0)
                
                # Update UI with audio data
                self.ui.update_audio_data(level, waveform, spectrum)
                
                # Update speaking status
                self.ui.update_status(
                    listening=self.voice_manager.is_listening(),
                    speaking=self.voice_manager.is_speaking(),
                    processing=False
                )
                
                # Update current speech text
                if self.voice_manager.is_speaking():
                    self.ui.update_current_speech(self.voice_manager.get_current_speech())
                else:
                    self.ui.update_current_speech("")
                
                # Sleep briefly
                time.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error updating audio visualization: {str(e)}")
                time.sleep(0.1)  # Prevent tight loop on errors


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="CognitoCoreMk1 - Python-powered AI Assistant")
    parser.add_argument('--no-voice', action='store_true', help='Disable voice interface')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize and start the application
    app = CognitoCoreMk1()
    
    try:
        app.start()
        
        # If voice is disabled, don't activate automatically
        if not args.no_voice:
            # Wait a bit for UI to initialize
            time.sleep(1)
            app.activate()
        
        # Keep main thread alive while the application runs
        while app.running:
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected, shutting down")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
    finally:
        app.stop()


if __name__ == "__main__":
    main()
