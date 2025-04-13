"""
Core AI agent functionality using Google's Gemini API
"""
import google.generativeai as genai
import time
import logging
from typing import Dict, List, Any, Optional

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agent")

class CognitoAgent:
    def __init__(self):
        """Initialize the Gemini-powered agent"""
        self.configure_gemini()
        self.conversation_history = []
        self.message_count = 0
        logger.info("CognitoAgent initialized")

    def configure_gemini(self):
        """Set up the Gemini API with API key and model configuration"""
        if not config.GEMINI_API_KEY:
            logger.error("Gemini API key not found. Please add it to your .env file.")
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        
        # Initialize model
        try:
            self.model = genai.GenerativeModel(config.GEMINI_MODEL)
            self.chat_session = self.model.start_chat(
                history=[],
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
            )
            # Add initial system prompt to set the assistant's persona
            self._send_system_message(config.ASSISTANT_PERSONA)
            logger.info(f"Successfully initialized Gemini model: {config.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise

    def _send_system_message(self, content: str):
        """Send a system message to set context/behavior"""
        try:
            self.chat_session.send_message(f"System: {content}")
            logger.debug("System message sent to Gemini")
        except Exception as e:
            logger.error(f"Error sending system message: {str(e)}")

    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a user query and return the AI response
        
        Args:
            query: The user's input text
            context: Optional context dict with additional information
            
        Returns:
            The agent's response as a string
        """
        try:
            # Add any relevant context to the query
            enhanced_query = query
            if context:
                context_str = " ".join([f"{k}: {v}" for k, v in context.items()])
                enhanced_query = f"{query}\n\nContext: {context_str}"
            
            # Send to Gemini and get response
            response = self.chat_session.send_message(enhanced_query)
            response_text = response.text
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            self.message_count += 2
            
            # Trim history if it gets too long
            if self.message_count > 50:
                self.conversation_history = self.conversation_history[-40:]
                self.message_count = len(self.conversation_history)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"I apologize, but I encountered an error processing your request. {str(e)}"

    def get_tool_instructions(self, tool_name: str, user_query: str) -> Dict[str, Any]:
        """
        Get specific instructions for a tool based on the user query
        
        Args:
            tool_name: The name of the tool to get instructions for
            user_query: The user's original query
            
        Returns:
            A dictionary with parameters for the tool
        """
        try:
            prompt = f"""
            Based on the user query: "{user_query}"
            
            Generate specific parameters for the {tool_name} tool in JSON format.
            Only include necessary parameters that can be extracted from the query.
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract parameters from response
            # This is simplified - in a real application you'd want to parse JSON properly
            params_text = response.text
            
            # For now, just return a basic dict with the tool name and query
            return {
                "tool": tool_name,
                "query": user_query,
                "raw_response": params_text
            }
            
        except Exception as e:
            logger.error(f"Error getting tool instructions: {str(e)}")
            return {"tool": tool_name, "error": str(e)}
    
    def determine_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze the user query to determine intent and required tools
        
        Args:
            query: The user's input
            
        Returns:
            A dictionary with intent classification
        """
        try:
            prompt = f"""
            Analyze this user query: "{query}"
            
            Determine:
            1. The primary intent (web_search, system_command, send_email, general_question, etc.)
            2. If tools are needed, which one(s)?
            3. A confidence score (0-1) for this classification
            
            Format your response as concise key-value pairs.
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse the response - in a real scenario you would parse this properly
            intent_analysis = response.text
            
            # For now, let's use a simplified approach
            if "search" in query.lower() or "find" in query.lower() or "look up" in query.lower():
                return {"intent": "web_search", "confidence": 0.8}
            elif "email" in query.lower() or "send message" in query.lower():
                return {"intent": "send_email", "confidence": 0.8}
            elif "system" in query.lower() or "run" in query.lower() or "execute" in query.lower():
                return {"intent": "system_command", "confidence": 0.7}
            else:
                return {"intent": "general_question", "confidence": 0.9}
                
        except Exception as e:
            logger.error(f"Error determining intent: {str(e)}")
            return {"intent": "unknown", "error": str(e), "confidence": 0}

    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []
        self.message_count = 0
        self.configure_gemini()  # Reinitialize the chat session
        logger.info("Conversation reset")