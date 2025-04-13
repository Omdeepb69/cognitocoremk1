"""
Pygame-based retro JARVIS-like interface for CognitoCoreMk1
"""
import os
import time
import math
import random
import logging
import threading
import pygame
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/ui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ui")

class JarvisUI:
    """Retro JARVIS-like UI using Pygame"""
    
    def __init__(self, width=None, height=None):
        """
        Initialize the UI
        
        Args:
            width: Screen width (default from config)
            height: Screen height (default from config)
        """
        self.width = width or config.UI_WIDTH
        self.height = height or config.UI_HEIGHT
        self.running = False
        self.ui_thread = None
        
        # Audio visualization
        self.audio_levels = deque(maxlen=100)
        self.waveform_points = deque(maxlen=100)
        self.spectrum_data = np.zeros(64)
        
        # Conversation history
        self.conversation = []
        self.max_conversation_lines = 8
        
        # UI elements
        self.circles = []
        self.particles = []
        self.hexagons = []
        
        # Status indicators
        self.listening = False
        self.speaking = False
        self.processing = False
        self.current_speech = ""
        
        # Initialize pygame
        pygame.init()
        pygame.font.init()
        self.screen = None
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.title_font = pygame.font.SysFont('Arial', 28, bold=True)
        self.status_font = pygame.font.SysFont('Arial', 18)
        self.conversation_font = pygame.font.SysFont('Consolas', 16)
        
        # Colors
        self.bg_color = config.UI_BACKGROUND_COLOR
        self.main_color = config.UI_THEME_COLOR
        self.highlight_color = (min(255, self.main_color[0] + 50), 
                               min(255, self.main_color[1] + 50), 
                               min(255, self.main_color[2] + 50))
        self.dim_color = (max(0, self.main_color[0] - 100), 
                         max(0, self.main_color[1] - 100), 
                         max(0, self.main_color[2] - 100))
        
        # Buttons
        self.buttons = []
        self._create_buttons()
        
        logger.info("JarvisUI initialized")
    
    def _create_buttons(self):
        """Create UI control buttons"""
        button_width = 120
        button_height = 40
        margin = 10
        y_position = self.height - button_height - margin
        
        # Add activation button
        self.buttons.append({
            'rect': pygame.Rect(margin, y_position, button_width, button_height),
            'text': "Activate",
            'action': "activate",
            'active': False
        })
        
        # Add deactivation button
        self.buttons.append({
            'rect': pygame.Rect(margin + button_width + margin, y_position, button_width, button_height),
            'text': "Deactivate",
            'action': "deactivate",
            'active': False
        })
        
        # Add reset conversation button
        self.buttons.append({
            'rect': pygame.Rect(margin + (button_width + margin) * 2, y_position, button_width, button_height),
            'text': "Reset Conv",
            'action': "reset",
            'active': False
        })
        
        # Add system info button
        self.buttons.append({
            'rect': pygame.Rect(margin + (button_width + margin) * 3, y_position, button_width, button_height),
            'text': "System Info",
            'action': "sysinfo",
            'active': False
        })
    
    def start(self):
        """Start the UI in a background thread"""
        if not self.running:
            self.running = True
            self.ui_thread = threading.Thread(target=self._ui_loop)
            self.ui_thread.daemon = True
            self.ui_thread.start()
            logger.info("UI started")
            return True
        else:
            logger.warning("UI already running")
            return False
    
    def stop(self):
        """Stop the UI"""
        if self.running:
            self.running = False
            if self.ui_thread:
                self.ui_thread.join(timeout=2)
            pygame.quit()
            logger.info("UI stopped")
            return True
        else:
            logger.warning("UI not running")
            return False
    
    def _ui_loop(self):
        """Main UI loop"""
        try:
            # Initialize pygame window
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption(config.UI_TITLE)
            
            # Generate initial UI elements
            self._generate_ui_elements()
            
            # Main loop
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.MOUSEBUTTONUP:
                        pos = pygame.mouse.get_pos()
                        self._handle_click(pos)
                
                # Update UI elements
                self._update_ui_elements()
                
                # Clear screen
                self.screen.fill(self.bg_color)
                
                # Draw UI elements
                self._draw_background()
                self._draw_audio_visualizations()
                self._draw_status_indicators()
                self._draw_conversation()
                self._draw_buttons()
                
                # Update display
                pygame.display.flip()
                self.clock.tick(30)
            
        except Exception as e:
            logger.error(f"Error in UI loop: {str(e)}")
        finally:
            pygame.quit()
    
    def _handle_click(self, pos):
        """Handle mouse clicks on buttons"""
        for button in self.buttons:
            if button['rect'].collidepoint(pos):
                button['active'] = True
                
                # Return the action to the main application
                logger.info(f"Button clicked: {button['action']}")
                
                # Call the associated callback if it exists
                callback_name = f"on_{button['action']}_click"
                if hasattr(self, callback_name) and callable(getattr(self, callback_name)):
                    getattr(self, callback_name)()
    
    def set_button_callbacks(self, activate_callback=None, deactivate_callback=None, 
                             reset_callback=None, sysinfo_callback=None):
        """Set button click callbacks"""
        self.on_activate_click = activate_callback
        self.on_deactivate_click = deactivate_callback
        self.on_reset_click = reset_callback
        self.on_sysinfo_click = sysinfo_callback
    
    def _generate_ui_elements(self):
        """Generate initial UI elements"""
        # Generate circles
        for _ in range(5):
            self.circles.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'radius': random.randint(50, 150),
                'alpha': random.randint(5, 20),
                'speed': random.uniform(0.2, 1.0)
            })
        
        # Generate hexagons
        for _ in range(15):
            self.hexagons.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'size': random.randint(20, 60),
                'alpha': random.randint(5, 30),
                'rotation': random.uniform(0, math.pi * 2),
                'rotation_speed': random.uniform(-0.02, 0.02)
            })
    
    def _update_ui_elements(self):
        """Update positions and properties of UI elements"""
        # Update circles
        for circle in self.circles:
            circle['x'] += circle['speed']
            if circle['x'] - circle['radius'] > self.width:
                circle['x'] = -circle['radius']
                circle['y'] = random.randint(0, self.height)
        
        # Update hexagons
        for hexagon in self.hexagons:
            hexagon['rotation'] += hexagon['rotation_speed']
        
        # Update particles
        new_particles = []
        for particle in self.particles:
            particle['life'] -= 1
            if particle['life'] > 0:
                particle['x'] += particle['vx']
                particle['y'] += particle['vy']
                particle['vx'] *= 0.98
                particle['vy'] *= 0.98
                new_particles.append(particle)
        self.particles = new_particles
        
        # Generate new particles
        if self.listening and random.random() < 0.3:
            self._add_particle()
    
    def _add_particle(self):
        """Add a new particle to the system"""
        side = random.randint(0, 3)
        if side == 0:  # Top
            x = random.randint(0, self.width)
            y = 0
            vx = random.uniform(-1, 1)
            vy = random.uniform(0.5, 2)
        elif side == 1:  # Right
            x = self.width
            y = random.randint(0, self.height)
            vx = random.uniform(-2, -0.5)
            vy = random.uniform(-1, 1)
        elif side == 2:  # Bottom
            x = random.randint(0, self.width)
            y = self.height
            vx = random.uniform(-1, 1)
            vy = random.uniform(-2, -0.5)
        else:  # Left
            x = 0
            y = random.randint(0, self.height)
            vx = random.uniform(0.5, 2)
            vy = random.uniform(-1, 1)
        
        self.particles.append({
            'x': x,
            'y': y,
            'vx': vx,
            'vy': vy,
            'size': random.randint(2, 5),
            'life': random.randint(30, 90),
            'color': self.main_color
        })
    
    def _draw_background(self):
        """Draw background elements"""
        # Draw circles
        for circle in self.circles:
            surface = pygame.Surface((circle['radius'] * 2, circle['radius'] * 2), pygame.SRCALPHA)
            color = (*self.main_color, circle['alpha'])
            pygame.draw.circle(surface, color, (circle['radius'], circle['radius']), circle['radius'])
            self.screen.blit(surface, (circle['x'] - circle['radius'], circle['y'] - circle['radius']))
        
        # Draw hexagons
        for hexagon in self.hexagons:
            surface = pygame.Surface((hexagon['size'] * 2, hexagon['size'] * 2), pygame.SRCALPHA)
            color = (*self.main_color, hexagon['alpha'])
            
            # Calculate hexagon points
            points = []
            for i in range(6):
                angle = hexagon['rotation'] + (math.pi * 2 * i / 6)
                x = hexagon['size'] + hexagon['size'] * 0.8 * math.cos(angle)
                y = hexagon['size'] + hexagon['size'] * 0.8 * math.sin(angle)
                points.append((x, y))
            
            pygame.draw.polygon(surface, color, points)
            self.screen.blit(surface, (hexagon['x'] - hexagon['size'], hexagon['y'] - hexagon['size']))
        
        # Draw particles
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / 90))
            color = (*particle['color'], alpha)
            surface = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, color, (particle['size'], particle['size']), particle['size'])
            self.screen.blit(surface, (particle['x'] - particle['size'], particle['y'] - particle['size']))
        
        # Draw grid lines
        for x in range(0, self.width, 50):
            alpha = 10 + 20 * (1 - (x % 200) / 200)
            color = (*self.main_color, alpha)
            pygame.draw.line(self.screen, color, (x, 0), (x, self.height), 1)
        
        for y in range(0, self.height, 50):
            alpha = 10 + 20 * (1 - (y % 200) / 200)
            color = (*self.main_color, alpha)
            pygame.draw.line(self.screen, color, (0, y), (self.width, y), 1)
    
    def _draw_audio_visualizations(self):
        """Draw audio visualizations"""
        # Draw waveform
        if self.waveform_points:
            waveform_surface = pygame.Surface((self.width, 100), pygame.SRCALPHA)
            points = [(i * (self.width / len(self.waveform_points)), 50 + amplitude * 40) 
                     for i, amplitude in enumerate(self.waveform_points)]
            if len(points) > 1:
                pygame.draw.lines(waveform_surface, self.main_color, False, points, 2)
            self.screen.blit(waveform_surface, (0, self.height - 150))
        
        # Draw spectrum analyzer
        spectrum_width = self.width - 100
        bar_width = max(2, spectrum_width // len(self.spectrum_data))
        spectrum_surface = pygame.Surface((spectrum_width, 100), pygame.SRCALPHA)
        
        for i, value in enumerate(self.spectrum_data):
            bar_height = int(value * 80)
            color = (
                min(255, self.main_color[0] + int(value * 100)),
                min(255, self.main_color[1] + int(value * 50)),
                min(255, self.main_color[2] + int(value * 150))
            )
            pygame.draw.rect(
                spectrum_surface, 
                color, 
                (i * bar_width, 100 - bar_height, bar_width - 1, bar_height)
            )
        
        self.screen.blit(spectrum_surface, (50, self.height - 250))
        
        # Draw circular audio meter
        if self.audio_levels:
            meter_center = (self.width - 100, 100)
            meter_radius = 60
            avg_level = sum(self.audio_levels) / len(self.audio_levels)
            active_radius = meter_radius * (0.5 + avg_level * 0.5)
            
            # Draw background circle
            pygame.draw.circle(self.screen, self.dim_color, meter_center, meter_radius, 2)
            
            # Draw active circle
            active_color = (*self.main_color, 100)
            active_surface = pygame.Surface((active_radius * 2, active_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(active_surface, active_color, (active_radius, active_radius), active_radius)
            self.screen.blit(
                active_surface, 
                (meter_center[0] - active_radius, meter_center[1] - active_radius)
            )
            
            # Draw level indicator arcs
            for i in range(1, 5):
                level_radius = meter_radius * (i / 4)
                pygame.draw.circle(
                    self.screen, 
                    self.dim_color, 
                    meter_center, 
                    level_radius, 
                    1
                )
            
            # Add label
            label = self.status_font.render("Audio Level", True, self.main_color)
            self.screen.blit(
                label, 
                (meter_center[0] - label.get_width() // 2, meter_center[1] + meter_radius + 5)
            )
    
    def _draw_status_indicators(self):
        """Draw status indicators and information"""
        # Draw title
        title = self.title_font.render(config.ASSISTANT_NAME, True, self.main_color)
        self.screen.blit(title, (20, 20))
        
        # Draw status text
        status_text = "Listening..." if self.listening else "Idle"
        if self.speaking:
            status_text = "Speaking"
        if self.processing:
            status_text = "Processing..."
        
        status = self.status_font.render(status_text, True, self.highlight_color)
        self.screen.blit(status, (20, 60))
        
        # Draw speech text
        if self.speaking and self.current_speech:
            # Create a text box for the current speech
            speech_box = pygame.Surface((self.width - 40, 60), pygame.SRCALPHA)
            speech_box.fill((*self.bg_color, 150))
            pygame.draw.rect(speech_box, self.main_color, (0, 0, speech_box.get_width(), speech_box.get_height()), 1)
            
            # Render the text (with wrapping)
            display_text = self.current_speech
            if len(display_text) > 100:
                display_text = display_text[:97] + "..."
            
            speech_text = self.conversation_font.render(display_text, True, self.main_color)
            speech_box.blit(speech_text, (10, (60 - speech_text.get_height()) // 2))
            
            self.screen.blit(speech_box, (20, 90))
        
        # Draw system time
        time_text = time.strftime("%H:%M:%S")
        time_surface = self.status_font.render(time_text, True, self.main_color)
        self.screen.blit(time_surface, (self.width - time_surface.get_width() - 20, 20))
        
        # Draw indicators
        self._draw_indicator("Listening", self.listening, (20, self.height - 300))
        self._draw_indicator("Speaking", self.speaking, (120, self.height - 300))
        self._draw_indicator("Processing", self.processing, (220, self.height - 300))
    
    def _draw_indicator(self, label: str, active: bool, position: Tuple[int, int]):
        """Draw an indicator with label"""
        # Draw circle
        color = self.highlight_color if active else self.dim_color
        pygame.draw.circle(self.screen, color, (position[0] + 10, position[1] + 10), 8)
        
        # Draw pulse effect if active
        if active:
            pulse_size = 8 + 4 * math.sin(time.time() * 5)
            pulse_surface = pygame.Surface((pulse_size * 2, pulse_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(pulse_surface, (*color, 100), (pulse_size, pulse_size), pulse_size)
            self.screen.blit(
                pulse_surface, 
                (position[0] + 10 - pulse_size, position[1] + 10 - pulse_size)
            )
        
        # Draw label
        label_surface = self.status_font.render(label, True, self.main_color)
        self.screen.blit(label_surface, (position[0] + 25, position[1] + 5))
    
    def _draw_buttons(self):
        """Draw UI control buttons"""
        for button in self.buttons:
            # Draw button background
            color = self.highlight_color if button['active'] else self.main_color
            pygame.draw.rect(self.screen, color, button['rect'], 2, border_radius=5)
            
            # Draw button text
            text_surface = self.status_font.render(button['text'], True, color)
            text_rect = text_surface.get_rect(center=button['rect'].center)
            self.screen.blit(text_surface, text_rect)
            
            # Reset active state after drawing
            button['active'] = False
    
    def _draw_conversation(self):
        """Draw conversation history"""
        # Draw conversation box
        conv_box = pygame.Surface((self.width - 40, 300), pygame.SRCALPHA)
        conv_box.fill((*self.bg_color, 150))
        pygame.draw.rect(conv_box, self.main_color, (0, 0, conv_box.get_width(), conv_box.get_height()), 1)
        
        # Draw title
        title = self.status_font.render("Conversation History", True, self.main_color)
        conv_box.blit(title, (10, 10))
        
        # Draw conversation lines
        y_offset = 40
        for i, message in enumerate(self.conversation[-self.max_conversation_lines:]):
            role = "You: " if message['role'] == 'user' else f"{config.ASSISTANT_NAME}: "
            color = (200, 200, 200) if message['role'] == 'user' else self.main_color
            
            # Display text with wrapping
            max_width = conv_box.get_width() - 20
            text = role + message['content']
            
            # Simple text wrapping
            wrapped_text = []
            words = text.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + word + " "
                # Check if adding the word would exceed the width
                test_surface = self.conversation_font.render(test_line, True, color)
                if test_surface.get_width() > max_width:
                    wrapped_text.append(current_line)
                    current_line = word + " "
                else:
                    current_line = test_line
            
            # Add the last line
            if current_line:
                wrapped_text.append(current_line)
            
            # Draw each line
            for line in wrapped_text:
                text_surface = self.conversation_font.render(line, True, color)
                conv_box.blit(text_surface, (10, y_offset))
                y_offset += 20
                
                # Check if we've reached the bottom of the box
                if y_offset >= conv_box.get_height() - 10:
                    break
            
            # Add spacing between messages
            y_offset += 5
            
            # Check if we've reached the bottom of the box
            if y_offset >= conv_box.get_height() - 10:
                break
        
        self.screen.blit(conv_box, (20, 160))
    
    def update_audio_data(self, level: float, waveform: List[float], spectrum: np.ndarray):
        """
        Update audio visualization data
        
        Args:
            level: Current audio level (0.0-1.0)
            waveform: List of waveform amplitude values
            spectrum: Frequency spectrum data
        """
        self.audio_levels.append(level)
        
        # Update waveform
        for point in waveform:
            self.waveform_points.append(point)
        
        # Update spectrum
        if len(spectrum) == len(self.spectrum_data):
            self.spectrum_data = spectrum
    
    def update_status(self, listening: bool, speaking: bool, processing: bool):
        """
        Update status indicators
        
        Args:
            listening: Whether system is listening
            speaking: Whether system is speaking
            processing: Whether system is processing
        """
        self.listening = listening
        self.speaking = speaking
        self.processing = processing
    
    def update_current_speech(self, text: str):
        """
        Update the text currently being spoken
        
        Args:
            text: Current speech text
        """
        self.current_speech = text
    
    def add_conversation_message(self, role: str, content: str):
        """
        Add a message to the conversation history
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.conversation.append({
            'role': role,
            'content': content
        })