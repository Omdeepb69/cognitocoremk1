"""
Collection of tools for web access, system commands, emails, and more
"""
import os
import sys
import json
import time
import logging
import smtplib
import subprocess
import requests
import psutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from twilio.rest import Client

import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/tools.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tools")

class WebTools:
    """Tools for web search and information retrieval"""
    
    @staticmethod
    def search_web(query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a web search and return results
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with search results
        """
        try:
            # This is a simplified version that would be replaced with a real search API
            # Like Google Custom Search API, Bing Search API, or SerpAPI
            logger.info(f"Searching web for: {query}")
            
            # Mockup search - in a real application, use an actual search API
            headers = {
                'User-Agent': 'CognitoCoreMk1/1.0 (Educational Project)'
            }
            
            # Use a search engine that allows scraping or better yet, a proper API
            search_url = f"https://duckduckgo.com/html/?q={query}"
            response = requests.get(search_url, headers=headers)
            
            if response.status_code != 200:
                return [{"title": "Search failed", "url": "", "snippet": f"Error: {response.status_code}"}]
            
            # Parse results with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # This is a simplified parser for DuckDuckGo
            # In a real application, use proper selectors based on the search engine
            for result in soup.select('.result')[:num_results]:
                title_elem = result.select_one('.result__title')
                link_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                
                title = title_elem.text if title_elem else "No title"
                url = link_elem.text if link_elem else "#"
                snippet = snippet_elem.text if snippet_elem else "No description"
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in web search: {str(e)}")
            return [{"title": "Search error", "url": "", "snippet": f"An error occurred: {str(e)}"}]
    
    @staticmethod
    def fetch_webpage_content(url: str) -> str:
        """
        Fetch and extract content from a webpage
        
        Args:
            url: URL of the webpage to fetch
            
        Returns:
            Extracted text content from the webpage
        """
        try:
            logger.info(f"Fetching content from: {url}")
            
            headers = {
                'User-Agent': 'CognitoCoreMk1/1.0 (Educational Project)'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return f"Failed to fetch page. Status code: {response.status_code}"
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.extract()
            
            # Extract text
            text = soup.get_text(separator='\n')
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit text length to avoid overwhelming the AI
            max_length = 5000
            if len(text) > max_length:
                text = text[:max_length] + "...\n[Content truncated due to length]"
            
            return text
            
        except Exception as e:
            logger.error(f"Error fetching webpage: {str(e)}")
            return f"Failed to fetch webpage content: {str(e)}"


class SystemTools:
    """Tools for system interaction and management"""
    
    @staticmethod
    def run_command(command: str, safe_mode: bool = True) -> Dict[str, Any]:
        """
        Run a system command and return the output
        
        Args:
            command: Command to execute
            safe_mode: If True, restricts to safe commands only
            
        Returns:
            Dict with command output and status
        """
        try:
            logger.info(f"Running system command: {command}")
            
            # List of allowed commands in safe mode
            safe_commands = [
                'ls', 'dir', 'echo', 'date', 'time', 'whoami', 
                'pwd', 'cd', 'hostname', 'ping', 'python', 'python3',
                'pip', 'pip3', 'type', 'cat', 'more'
            ]
            
            # Check if command is allowed in safe mode
            command_base = command.split()[0].lower()
            if safe_mode and command_base not in safe_commands:
                return {
                    "output": f"Command '{command_base}' not allowed in safe mode",
                    "status": "denied",
                    "error": "Security restriction"
                }
            
            # Run the command and capture output
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=30)
            
            return {
                "output": stdout,
                "error": stderr if stderr else None,
                "status": "success" if process.returncode == 0 else "error",
                "code": process.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return {
                "output": "",
                "error": "Command execution timed out",
                "status": "timeout",
                "code": -1
            }
        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return {
                "output": "",
                "error": str(e),
                "status": "error",
                "code": -1
            }
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get system information
        
        Returns:
            Dict with system information
        """
        try:
            logger.info("Collecting system information")
            
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count(logical=True)
            
            # Memory info
            memory = psutil.virtual_memory()
            
            # Disk info
            disk = psutil.disk_usage('/')
            
            # Network info
            net_io = psutil.net_io_counters()
            
            # Battery info (if available)
            battery = None
            if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
                battery_stats = psutil.sensors_battery()
                battery = {
                    "percent": battery_stats.percent,
                    "power_plugged": battery_stats.power_plugged,
                    "seconds_left": battery_stats.secsleft
                }
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "frequency": cpu_freq.current if cpu_freq else None,
                    "cores": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv
                },
                "battery": battery,
                "uptime": {
                    "seconds": uptime,
                    "formatted": f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m"
                },
                "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)),
                "platform": sys.platform
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {"error": str(e)}


class CommunicationTools:
    """Tools for email, messaging, and communication"""
    
    @staticmethod
    def send_email(recipient: str, subject: str, body: str, html_body: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an email using configured SMTP settings
        
        Args:
            recipient: Email address of the recipient
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML body
            
        Returns:
            Dict with send status and details
        """
        try:
            logger.info(f"Sending email to: {recipient}")
            
            if not all([config.EMAIL_ADDRESS, config.EMAIL_PASSWORD, config.SMTP_SERVER]):
                return {
                    "status": "error",
                    "message": "Email configuration incomplete"
                }
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((config.ASSISTANT_NAME, config.EMAIL_ADDRESS))
            msg['To'] = recipient
            
            # Add plain text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Connect to server and send
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            return {
                "status": "success",
                "recipient": recipient,
                "subject": subject,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @staticmethod
    def send_whatsapp(recipient: str, message: str) -> Dict[str, Any]:
        """
        Send a WhatsApp message using Twilio
        
        Args:
            recipient: Phone number of the recipient (with country code)
            message: Message text
            
        Returns:
            Dict with send status and details
        """
        try:
            logger.info(f"Sending WhatsApp to: {recipient}")
            
            if not all([config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN, config.TWILIO_PHONE_NUMBER]):
                return {
                    "status": "error",
                    "message": "Twilio configuration incomplete"
                }
            
            # Initialize Twilio client
            client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            
            # Send message
            twilio_message = client.messages.create(
                body=message,
                from_=f"whatsapp:{config.TWILIO_PHONE_NUMBER}",
                to=f"whatsapp:{recipient}"
            )
            
            return {
                "status": "success",
                "recipient": recipient,
                "message_sid": twilio_message.sid,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


class ToolManager:
    """Manager class for all available tools"""
    
    def __init__(self):
        """Initialize the tool manager"""
        self.web_tools = WebTools()
        self.system_tools = SystemTools()
        self.communication_tools = CommunicationTools()
        logger.info("ToolManager initialized")
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific tool with provided parameters
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            
        Returns:
            Result of the tool execution
        """
        try:
            logger.info(f"Executing tool: {tool_name} with params: {params}")
            
            # Web tools
            if tool_name == "web_search":
                query = params.get("query", "")
                num_results = params.get("num_results", 5)
                return {"results": self.web_tools.search_web(query, num_results)}
            
            elif tool_name == "fetch_webpage":
                url = params.get("url", "")
                return {"content": self.web_tools.fetch_webpage_content(url)}
            
            # System tools
            elif tool_name == "run_command":
                command = params.get("command", "")
                safe_mode = params.get("safe_mode", True)
                return self.system_tools.run_command(command, safe_mode)
            
            elif tool_name == "system_info":
                return {"info": self.system_tools.get_system_info()}
            
            # Communication tools
            elif tool_name == "send_email":
                recipient = params.get("recipient", "")
                subject = params.get("subject", "")
                body = params.get("body", "")
                html_body = params.get("html_body", None)
                return self.communication_tools.send_email(recipient, subject, body, html_body)
            
            elif tool_name == "send_whatsapp":
                recipient = params.get("recipient", "")
                message = params.get("message", "")
                return self.communication_tools.send_whatsapp(recipient, message)
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "status": "error",
                "tool": tool_name,
                "message": str(e)
            }