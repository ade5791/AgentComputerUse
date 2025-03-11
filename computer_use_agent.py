import os
import json
import requests
from openai import OpenAI

class ComputerUseAgent:
    """
    A class to handle interaction with OpenAI's Computer Use Agent API.
    """
    
    def __init__(self, api_key, environment="browser", display_width=1024, display_height=768):
        """
        Initialize the Computer Use Agent.
        
        Args:
            api_key (str): The OpenAI API key.
            environment (str): The environment to use (browser, mac, windows, ubuntu).
            display_width (int): The width of the display.
            display_height (int): The height of the display.
        """
        self.client = OpenAI(api_key=api_key)
        self.environment = environment
        self.display_width = display_width
        self.display_height = display_height
        
    def initial_request(self, task, screenshot_base64):
        """
        Send the initial request to the Computer Use Agent.
        
        Args:
            task (str): The task to perform.
            screenshot_base64 (str): The base64-encoded screenshot.
            
        Returns:
            object: The response from the API.
        """
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a computer use agent operating in a {self.environment} environment with dimensions {self.display_width}x{self.display_height}."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Task: {task}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_action",
                            "description": "Perform an action in the browser",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["click", "double_click", "scroll", "type", "keypress", "wait", "navigate"],
                                        "description": "The type of action to perform"
                                    },
                                    "x": {
                                        "type": "integer",
                                        "description": "The x-coordinate for click actions"
                                    },
                                    "y": {
                                        "type": "integer",
                                        "description": "The y-coordinate for click actions"
                                    },
                                    "dx": {
                                        "type": "integer",
                                        "description": "The horizontal scroll amount"
                                    },
                                    "dy": {
                                        "type": "integer",
                                        "description": "The vertical scroll amount"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "The text to type"
                                    },
                                    "key": {
                                        "type": "string",
                                        "description": "The key to press (e.g., 'Enter', 'Tab', 'ArrowDown')"
                                    },
                                    "ms": {
                                        "type": "integer",
                                        "description": "The number of milliseconds to wait"
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "The URL to navigate to"
                                    }
                                },
                                "required": ["type"]
                            }
                        }
                    }
                ]
            )
            
            return response
        except Exception as e:
            raise Exception(f"Error sending initial request to Computer Use Agent: {str(e)}")
    
    def send_screenshot(self, previous_response_id, call_id, screenshot_base64):
        """
        Send a screenshot to the Computer Use Agent as the result of a previous action.
        
        Args:
            previous_response_id (str): The ID of the previous response.
            call_id (str): The ID of the call that was executed.
            screenshot_base64 (str): The base64-encoded screenshot.
            
        Returns:
            object: The response from the API.
        """
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a computer use agent operating in a {self.environment} environment with dimensions {self.display_width}x{self.display_height}."
                    },
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": "browser_action",
                                    "arguments": "{}"  # This is just a placeholder, not actually used
                                }
                            }
                        ]
                    },
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "browser_action",
                            "description": "Perform an action in the browser",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["click", "double_click", "scroll", "type", "keypress", "wait", "navigate"],
                                        "description": "The type of action to perform"
                                    },
                                    "x": {
                                        "type": "integer",
                                        "description": "The x-coordinate for click actions"
                                    },
                                    "y": {
                                        "type": "integer",
                                        "description": "The y-coordinate for click actions"
                                    },
                                    "dx": {
                                        "type": "integer",
                                        "description": "The horizontal scroll amount"
                                    },
                                    "dy": {
                                        "type": "integer",
                                        "description": "The vertical scroll amount"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "The text to type"
                                    },
                                    "key": {
                                        "type": "string",
                                        "description": "The key to press (e.g., 'Enter', 'Tab', 'ArrowDown')"
                                    },
                                    "ms": {
                                        "type": "integer",
                                        "description": "The number of milliseconds to wait"
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "The URL to navigate to"
                                    }
                                },
                                "required": ["type"]
                            }
                        }
                    }
                ]
            )
            
            return response
        except Exception as e:
            raise Exception(f"Error sending screenshot to Computer Use Agent: {str(e)}")
    
    def acknowledge_safety_checks(self, previous_response_id, call_id, safety_checks):
        """
        Acknowledge safety checks from the Computer Use Agent.
        
        Args:
            previous_response_id (str): The ID of the previous response.
            call_id (str): The ID of the call that has safety checks.
            safety_checks (list): The list of safety checks to acknowledge.
            
        Returns:
            object: The response from the API.
        """
        # Note: The Computer Use API may include safety checks in the future
        # This method is a placeholder for that functionality
        pass