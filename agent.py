# agent.py
# Contains the core agent logic for CognitoCoreMk1

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, FunctionDeclaration, Tool
import json
import logging
import os
from typing import List, Dict, Any, Tuple, Optional

# Assuming config.py exists in the same directory or is accessible
try:
    import config
except ImportError:
    print("Error: config.py not found. Please ensure it exists and contains GEMINI_API_KEY.")
    exit(1)

# Assuming tools.py exists and contains the necessary tool functions
try:
    import tools
except ImportError:
    print("Error: tools.py not found. Please ensure it exists and contains the required tool functions.")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Gemini API Configuration ---
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except AttributeError:
    logger.error("GEMINI_API_KEY not found in config.py. Please add it.")
    exit(1)
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    exit(1)

# --- Tool Definitions for Gemini Function Calling ---
# Define the structure of functions available to the Gemini model.
# These should correspond to functions implemented in tools.py

# Define schemas using FunctionDeclaration
# Example: Web Browsing
browse_web_declaration = FunctionDeclaration(
    name="browse_web",
    description="Fetches the content of a given URL or performs a web search if URL is not specific. Use this for real-time information, news, or specific website content.",
    parameters={
        "type": "object",
        "properties": {
            "query_or_url": {
                "type": "string",
                "description": "The URL to fetch or the search query to perform."
            }
        },
        "required": ["query_or_url"]
    }
)

# Example: System Command Execution
run_command_declaration = FunctionDeclaration(
    name="run_command",
    description="Executes a basic OS-level shell command (e.g., ls, pwd, echo). Use with caution. Avoid destructive commands.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute (e.g., 'ls -l', 'pwd')."
            }
        },
        "required": ["command"]
    }
)

# Example: Send Email
send_email_declaration = FunctionDeclaration(
    name="send_email",
    description="Drafts and sends an email using SMTP.",
    parameters={
        "type": "object",
        "properties": {
            "to_address": {
                "type": "string",
                "description": "The recipient's email address."
            },
            "subject": {
                "type": "string",
                "description": "The subject line of the email."
            },
            "body": {
                "type": "string",
                "description": "The main content/body of the email."
            }
        },
        "required": ["to_address", "subject", "body"]
    }
)

# Example: Check System Status
check_system_status_declaration = FunctionDeclaration(
    name="check_system_status",
    description="Retrieves system status information like CPU usage, memory usage, and disk space.",
    parameters={} # No parameters needed for this example
)

# Create a Tool object incorporating all defined functions
AVAILABLE_TOOLS = Tool(
    function_declarations=[
        browse_web_declaration,
        run_command_declaration,
        send_email_declaration,
        check_system_status_declaration,
        # Add other function declarations from tools.py here
    ]
)

# Map tool names to actual functions in tools.py
TOOL_FUNCTION_MAP = {
    "browse_web": tools.browse_web,
    "run_command": tools.run_command,
    "send_email": tools.send_email,
    "check_system_status": tools.check_system_status,
    # Add other mappings here
}

# --- Personality Prompt ---
# Loaded from config or defined here
DEFAULT_PERSONALITY_PROMPT = (
    "You are CognitoCoreMk1, a highly advanced AI assistant inspired by JARVIS. "
    "Your personality is witty, helpful, slightly sarcastic, and always professional. "
    "You assist the user with tasks, provide information, and manage communications. "
    "You have access to tools for web browsing, system commands, and sending emails. "
    "When asked to perform an action requiring a tool, clearly state your intention and use the appropriate function call. "
    "If a request is ambiguous, ask clarifying questions. Maintain context throughout the conversation. "
    "Inject appropriate humor or witty remarks when suitable, but prioritize helpfulness and accuracy. "
    "Do not perform harmful or unethical actions. If asked to execute a potentially dangerous command, express caution or refuse if necessary."
)
PERSONALITY_PROMPT = getattr(config, 'PERSONALITY_PROMPT', DEFAULT_PERSONALITY_PROMPT)

# --- Safety Settings ---
# Adjust safety settings as needed
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# --- Core Agent Class ---

class CognitoCoreAgent:
    """
    The core agent class responsible for processing input, interacting with the
    Gemini API, managing tools, and generating responses.
    """
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        """
        Initializes the CognitoCoreAgent.

        Args:
            model_name (str): The name of the Gemini model to use.
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initializes the Gemini Generative Model instance."""
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=PERSONALITY_PROMPT,
                safety_settings=SAFETY_SETTINGS,
                tools=[AVAILABLE_TOOLS] # Pass the Tool object directly
            )
            logger.info(f"Gemini model '{self.model_name}' initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Gemini model '{self.model_name}': {e}", exc_info=True)
            # Fallback or critical error handling can be added here
            raise RuntimeError(f"Failed to initialize Gemini model: {e}") from e

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the specified tool function with the given arguments.

        Args:
            tool_name (str): The name of the tool (function) to execute.
            tool_args (Dict[str, Any]): The arguments for the tool function.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the tool execution.
                           Expected format: {"result": <tool_output>}
        """
        if tool_name not in TOOL_FUNCTION_MAP:
            logger.error(f"Attempted to call unknown tool: {tool_name}")
            return {"result": f"Error: Tool '{tool_name}' is not available."}

        tool_function = TOOL_FUNCTION_MAP[tool_name]
        logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")

        try:
            # Ensure arguments are passed correctly, handling potential missing args if needed
            # For simplicity, we assume Gemini provides all required args defined in the schema
            result = tool_function(**tool_args)
            logger.info(f"Tool '{tool_name}' executed successfully.")
            # Ensure the result is serializable (e.g., string) if necessary
            return {"result": str(result)}
        except TypeError as e:
            logger.error(f"Type error executing tool '{tool_name}' with args {tool_args}: {e}", exc_info=True)
            return {"result": f"Error: Invalid arguments provided for tool '{tool_name}'. {e}"}
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return {"result": f"Error: Failed to execute tool '{tool_name}'. {e}"}

    def process_input(self, user_text: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Processes user input, interacts with Gemini, handles tool calls, and returns the response.

        Args:
            user_text (str): The text input from the user.
            conversation_history (Optional[List[Dict[str, Any]]]): The history of the conversation
                in the format expected by Gemini API (list of {'role': 'user'/'model', 'parts': [{'text': '...'}]}).

        Returns:
            Tuple[str, List[Dict[str, Any]]]: A tuple containing:
                - The final text response to the user.
                - The updated conversation history.
        """
        if not self.model:
            logger.error("Model not initialized. Cannot process input.")
            return "Error: The AI model is not available. Please try again later.", conversation_history or []

        if conversation_history is None:
            conversation_history = []

        try:
            # Start a chat session using the existing history
            # Note: Gemini API expects history as Content objects, but the library handles dict conversion.
            chat = self.model.start_chat(history=conversation_history)

            # Send the user message
            logger.info(f"Sending user message to Gemini: '{user_text}'")
            response = chat.send_message(user_text)
            logger.debug(f"Initial Gemini response received: {response}")

            # Check for function calls requested by the model
            while response.candidates[0].content.parts and isinstance(response.candidates[0].content.parts[0], genai.types.FunctionCall):
                function_call = response.candidates[0].content.parts[0].function_call
                tool_name = function_call.name
                tool_args = dict(function_call.args) # Convert proto Map to dict

                logger.info(f"Gemini requested function call: {tool_name} with args: {tool_args}")

                # Execute the tool
                api_response = self._execute_tool(tool_name, tool_args)

                # Send the tool's result back to the model
                logger.info(f"Sending tool response back to Gemini for tool {tool_name}")
                response = chat.send_message(
                    genai.types.FunctionResponse(name=tool_name, response=api_response)
                )
                logger.debug(f"Gemini response after tool execution: {response}")

            # Once no more function calls, the final response is in the text part
            final_response_text = response.text
            logger.info(f"Final response from Gemini: '{final_response_text}'")

            # The chat object's history is automatically updated
            updated_history = chat.history
            # Convert Content objects back to simple dicts if needed for external storage
            serializable_history = [
                {'role': msg.role, 'parts': [{'text': part.text} for part in msg.parts]}
                for msg in updated_history
            ]

            return final_response_text, serializable_history

        except genai.types.BlockedPromptException as e:
            logger.warning(f"User input blocked by safety settings: {e}")
            return "I cannot process that request due to safety restrictions.", conversation_history
        except genai.types.StopCandidateException as e:
             logger.warning(f"Model response stopped: {e}")
             # Attempt to get partial text if available
             try:
                 partial_text = e.response.text
                 if partial_text:
                     logger.info(f"Returning partial response due to stop candidate: {partial_text}")
                     # Manually update history with the partial response
                     updated_history = conversation_history + [
                         {'role': 'user', 'parts': [{'text': user_text}]},
                         {'role': 'model', 'parts': [{'text': partial_text}]}
                     ]
                     return partial_text, updated_history
                 else:
                    return "My response was interrupted. Could you please rephrase?", conversation_history
             except Exception:
                 return "My response was interrupted. Could you please rephrase?", conversation_history
        except Exception as e:
            logger.error(f"An unexpected error occurred during processing: {e}", exc_info=True)
            return "I encountered an internal error. Please try again later.", conversation_history


# --- Example Usage (for testing purposes) ---
if __name__ == "__main__":
    print("Initializing CognitoCore Agent...")
    agent = CognitoCoreAgent()
    print("Agent Initialized. Type 'quit' to exit.")

    # Simple conversation loop
    history = []
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        if not user_input:
            continue

        response_text, updated_history = agent.process_input(user_input, history)
        print(f"CognitoCore: {response_text}")
        history = updated_history # Maintain conversation context

    print("Exiting CognitoCore agent.")