# main.py
# Main entry point for the CognitoCoreMk1 AI Assistant.

import sys
import logging
import traceback

# --- Project Specific Imports ---
# These imports assume the existence of corresponding files/modules
# within the project structure (config.py, voice_io.py, agent.py).
try:
    import config  # Handles configuration loading (API keys, settings)
    import voice_io  # Handles voice input (listening) and output (speaking)
    import agent     # Handles core logic, NLP, tool use, communication
except ImportError as e:
    print(f"Error: Failed to import necessary project modules: {e}")
    print("Please ensure config.py, voice_io.py, and agent.py exist and are accessible.")
    sys.exit(1)
# --- Standard Library Imports ---
# Although many libraries are listed in the project details,
# main.py primarily orchestrates. The specific libraries like
# google-generativeai, requests, os, subprocess, smtplib, etc.,
# are expected to be used within agent.py or voice_io.py as needed.
# We import sys and logging here for main.py's own operation.

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
EXIT_COMMANDS = {"goodbye", "exit", "quit", "stop listening", "power down"}

def main():
    """
    Initializes components and runs the main interaction loop for the AI assistant.
    """
    logging.info("Initializing CognitoCoreMk1...")

    try:
        # Initialize Voice Input/Output
        # This might involve loading models or connecting to services,
        # handled within the VoiceIO class.
        speech_processor = voice_io.VoiceIO()
        logging.info("Voice I/O initialized.")

        # Initialize the Agent
        # This involves setting up the connection to the Gemini API,
        # potentially loading personality prompts, etc.
        ai_agent = agent.Agent()
        logging.info("AI Agent initialized.")

    except Exception as e:
        logging.error(f"Initialization failed: {e}")
        logging.error(traceback.format_exc())
        print(f"Critical error during initialization: {e}. Exiting.")
        sys.exit(1)

    # Initial greeting
    greeting = "Cognito Core online and ready. How can I assist you?"
    logging.info(f"Assistant: {greeting}")
    speech_processor.speak(greeting)

    # --- Main Interaction Loop ---
    logging.info("Starting interaction loop. Listening for commands...")
    while True:
        try:
            # 1. Listen for user command
            user_input = speech_processor.listen()

            if user_input:
                logging.info(f"User said: {user_input}")

                # 2. Check for exit command
                if user_input.lower().strip() in EXIT_COMMANDS:
                    farewell = "Powering down. Goodbye!"
                    logging.info(f"Assistant: {farewell}")
                    speech_processor.speak(farewell)
                    break # Exit the loop

                # 3. Process command with the agent
                logging.info("Processing command with agent...")
                response = ai_agent.process_command(user_input)

                # 4. Speak the response
                if response:
                    logging.info(f"Agent response: {response}")
                    speech_processor.speak(response)
                else:
                    # Handle cases where the agent might not return a response
                    logging.warning("Agent did not provide a response.")
                    speech_processor.speak("I encountered an issue processing that request.")

            else:
                # Handle cases where listening failed or returned nothing (e.g., silence)
                # Optional: Provide feedback or just continue listening
                # logging.debug("No input detected or listening failed.")
                pass # Continue loop silently

        except KeyboardInterrupt:
            logging.info("Keyboard interrupt detected. Shutting down...")
            farewell = "Shutdown sequence initiated via keyboard interrupt. Goodbye!"
            try:
                # Attempt to speak farewell even on Ctrl+C if possible
                speech_processor.speak(farewell)
            except Exception as speak_err:
                logging.error(f"Could not speak farewell message: {speak_err}")
            break # Exit the loop

        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            logging.error(traceback.format_exc())
            # Attempt to inform the user via voice about the error
            try:
                error_message = "I've encountered an unexpected error. Please check the logs. I'll try to continue."
                speech_processor.speak(error_message)
            except Exception as speak_err:
                logging.error(f"Could not speak error message: {speak_err}")
            # Decide whether to continue or exit on error (here we continue)
            # Consider adding a counter for repeated errors to eventually exit

    logging.info("CognitoCoreMk1 shutting down.")
    print("Application has finished.")

if __name__ == "__main__":
    main()