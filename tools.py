# tools.py

"""
Implements the agent's callable functions (tools):
- Web searching/scraping
- System command execution
- Email composition/sending
- System status retrieval
"""

import os
import subprocess
import smtplib
import ssl
import logging
import shlex
from email.message import EmailMessage
from typing import List, Dict, Union, Optional

import requests
from bs4 import BeautifulSoup
import psutil
from duckduckgo_search import DDGS

# Attempt to import configuration, handle potential ImportError
try:
    from config import (
        SMTP_SERVER, SMTP_PORT, SMTP_USERNAME,
        SMTP_PASSWORD, SENDER_EMAIL, ALLOWED_COMMANDS
    )
    CONFIG_LOADED = True
except ImportError:
    logging.warning("Could not import configuration from config.py. Email and specific command execution might be limited.")
    CONFIG_LOADED = False
    # Define placeholders if config is missing, email won't work
    SMTP_SERVER = None
    SMTP_PORT = None
    SMTP_USERNAME = None
    SMTP_PASSWORD = None
    SENDER_EMAIL = None
    ALLOWED_COMMANDS = ["ls", "dir", "pwd", "echo", "ping", "netstat", "ipconfig", "ifconfig", "date", "time", "whoami"] # Default safe commands

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Tool Functions ---

def search_web(query: str, num_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo and returns summarized results.

    Args:
        query: The search query string.
        num_results: The maximum number of search results to return.

    Returns:
        A string containing the search results, or an error message.
    """
    logging.info(f"Performing web search for: {query}")
    results_str = f"Search results for '{query}':\n"
    try:
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=num_results))

        if not search_results:
            return f"No search results found for '{query}'."

        for i, result in enumerate(search_results, 1):
            results_str += f"{i}. {result.get('title', 'No Title')}\n"
            results_str += f"   URL: {result.get('href', 'No URL')}\n"
            results_str += f"   Snippet: {result.get('body', 'No Snippet')}\n\n"

        # Optional: Fetch content from the top result (be mindful of website terms of service)
        # try:
        #     top_url = search_results[0].get('href')
        #     if top_url:
        #         response = requests.get(top_url, timeout=10, headers={'User-Agent': 'CognitoCoreMk1/1.0'})
        #         response.raise_for_status()
        #         soup = BeautifulSoup(response.text, 'html.parser')
        #         # Extract relevant text (this needs refinement based on common page structures)
        #         paragraphs = soup.find_all('p', limit=3)
        #         content_summary = "\n".join([p.get_text() for p in paragraphs])
        #         if content_summary:
        #             results_str += f"--- Top Result Content Summary ---\n{content_summary}\n-------------------------------\n"
        # except requests.RequestException as e:
        #     logging.warning(f"Could not fetch content from top result {top_url}: {e}")
        # except Exception as e:
        #      logging.warning(f"Error parsing content from {top_url}: {e}")


        return results_str.strip()

    except Exception as e:
        logging.error(f"Web search failed for query '{query}': {e}", exc_info=True)
        return f"An error occurred during the web search: {e}"

def execute_system_command(command: str) -> str:
    """
    Executes a system command if it's in the allowed list.

    Args:
        command: The command string to execute.

    Returns:
        A string containing the command's stdout and stderr, or an error message.
    """
    logging.info(f"Attempting to execute system command: {command}")

    if not CONFIG_LOADED and not ALLOWED_COMMANDS:
         return "Error: Command execution is disabled because configuration could not be loaded."

    try:
        # Use shlex.split for safer argument parsing
        args = shlex.split(command)
        base_command = args[0]

        # Security Check: Only allow commands from the predefined list
        if base_command not in ALLOWED_COMMANDS:
            logging.warning(f"Execution denied for disallowed command: {command}")
            return f"Error: Command '{base_command}' is not allowed."

        # Execute the command
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
            timeout=30  # Add a timeout for safety
        )

        output = f"Command: '{command}'\n"
        output += f"Return Code: {result.returncode}\n"
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout.strip()}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr.strip()}\n"

        logging.info(f"Command '{command}' executed with return code {result.returncode}")
        return output.strip()

    except FileNotFoundError:
        logging.error(f"Command not found: {args[0]}")
        return f"Error: Command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out: {command}")
        return f"Error: Command '{command}' timed out after 30 seconds."
    except Exception as e:
        logging.error(f"Failed to execute command '{command}': {e}", exc_info=True)
        return f"An unexpected error occurred while executing the command: {e}"

def send_email(recipient: str, subject: str, body: str) -> str:
    """
    Sends an email using SMTP configuration from config.py.

    Args:
        recipient: The email address of the recipient.
        subject: The subject line of the email.
        body: The main content/body of the email.

    Returns:
        A string indicating success or failure.
    """
    logging.info(f"Attempting to send email to: {recipient}")

    if not CONFIG_LOADED or not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL]):
        logging.error("Email configuration is missing or incomplete in config.py.")
        return "Error: Email configuration is missing or incomplete. Cannot send email."

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg.set_content(body)

    try:
        # Establish secure connection
        context = ssl.create_default_context()
        if SMTP_PORT == 465: # Typically SSL
             server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
        else: # Typically STARTTLS (e.g., port 587)
             server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
             server.starttls(context=context) # Secure the connection

        # Login and send
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info(f"Email successfully sent to {recipient} with subject '{subject}'")
        return f"Email successfully sent to {recipient}."

    except smtplib.SMTPAuthenticationError:
        logging.error("SMTP Authentication failed. Check username/password.")
        return "Error: Email authentication failed. Please check credentials."
    except smtplib.SMTPConnectError:
        logging.error(f"Failed to connect to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        return "Error: Could not connect to the email server."
    except smtplib.SMTPSenderRefused:
         logging.error(f"Sender address {SENDER_EMAIL} refused by the server.")
         return f"Error: Sender address {SENDER_EMAIL} was refused."
    except smtplib.SMTPRecipientsRefused:
         logging.error(f"Recipient address {recipient} refused by the server.")
         return f"Error: Recipient address {recipient} was refused."
    except TimeoutError:
         logging.error("Connection to SMTP server timed out.")
         return "Error: Connection to the email server timed out."
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
        return f"An unexpected error occurred while sending the email: {e}"

def get_system_status() -> str:
    """
    Retrieves basic system status information (CPU, Memory, Disk).

    Returns:
        A string summarizing the current system status.
    """
    logging.info("Retrieving system status.")
    try:
        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=1) # Check over 1 second

        # Memory Usage
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent
        memory_total_gb = round(memory_info.total / (1024**3), 2)
        memory_available_gb = round(memory_info.available / (1024**3), 2)

        # Disk Usage (Root partition)
        # Use '/' for Unix-like systems, 'C:\\' for Windows as a common default
        disk_path = '/' if os.name != 'nt' else 'C:\\'
        try:
            disk_info = psutil.disk_usage(disk_path)
            disk_percent = disk_info.percent
            disk_total_gb = round(disk_info.total / (1024**3), 2)
            disk_free_gb = round(disk_info.free / (1024**3), 2)
            disk_status = (f"Disk Usage ({disk_path}): {disk_percent}% "
                           f"(Free: {disk_free_gb} GB / Total: {disk_total_gb} GB)")
        except FileNotFoundError:
             disk_status = f"Disk Usage ({disk_path}): Path not found."
        except Exception as e:
            logging.warning(f"Could not get disk usage for {disk_path}: {e}")
            disk_status = f"Disk Usage ({disk_path}): Error retrieving status."


        status_report = (
            f"--- System Status ---\n"
            f"CPU Usage: {cpu_percent}%\n"
            f"Memory Usage: {memory_percent}% (Available: {memory_available_gb} GB / Total: {memory_total_gb} GB)\n"
            f"{disk_status}\n"
            f"---------------------"
        )
        logging.info("System status retrieved successfully.")
        return status_report

    except Exception as e:
        logging.error(f"Failed to retrieve system status: {e}", exc_info=True)
        return f"An error occurred while retrieving system status: {e}"

# --- Example Usage (for testing) ---
if __name__ == "__main__":
    print("--- Testing Tools ---")

    # Test Web Search
    print("\nTesting Web Search...")
    search_result = search_web("What is the weather in London?")
    print(search_result)

    # Test System Command (Safe command)
    print("\nTesting System Command (Safe)...")
    # Use 'dir' on Windows, 'ls -l' on Unix-like
    safe_cmd = "dir" if os.name == 'nt' else "ls -l"
    command_result_safe = execute_system_command(safe_cmd)
    print(command_result_safe)

    # Test System Command (Disallowed command - example)
    print("\nTesting System Command (Disallowed)...")
    command_result_unsafe = execute_system_command("rm -rf /") # This should be blocked
    print(command_result_unsafe)

    # Test System Status
    print("\nTesting System Status...")
    status = get_system_status()
    print(status)

    # Test Email Sending (Requires config.py to be set up)
    print("\nTesting Email Sending...")
    if CONFIG_LOADED and SENDER_EMAIL and SMTP_USERNAME: # Basic check if config seems present
        # Replace with a real recipient for actual testing
        test_recipient = "test@example.com"
        print(f"Note: This will attempt to send a real email to {test_recipient} if config.py is set up.")
        # Uncomment the line below to actually send a test email
        # email_result = send_email(test_recipient, "CognitoCore Test Email", "This is a test email from CognitoCoreMk1 tools.py.")
        # print(email_result)
        print(f"Email test skipped (uncomment in code to run). Requires valid config.py and recipient.")

    else:
        print("Email test skipped: config.py not found or incomplete.")

    print("\n--- Testing Complete ---")