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
        Send the initial request to the Computer Use Agent using the Responses API.
        
        Args:
            task (str): The task to perform.
            screenshot_base64 (str): The base64-encoded screenshot.
            
        Returns:
            object: The response from the API.
        """
        try:
            # Using the computer-use-preview model from OpenAI's Responses API
            input_content = [
                {
                    "role": "user",
                    "content": task
                }
            ]
            
            # Include screenshot if provided
            if screenshot_base64:
                input_content.append({
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}"
                })
            
            response = self.client.responses.create(
                model="computer-use-preview",
                tools=[{
                    "type": "computer_use_preview",
                    "display_width": self.display_width,
                    "display_height": self.display_height,
                    "environment": self.environment
                }],
                input=input_content,
                truncation="auto"
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
            response = self.client.responses.create(
                model="computer-use-preview",
                previous_response_id=previous_response_id,
                tools=[{
                    "type": "computer_use_preview",
                    "display_width": self.display_width,
                    "display_height": self.display_height,
                    "environment": self.environment
                }],
                input=[
                    {
                        "call_id": call_id,
                        "type": "computer_call_output",
                        "output": {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ],
                truncation="auto"
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
        try:
            response = self.client.responses.create(
                model="computer-use-preview",
                previous_response_id=previous_response_id,
                tools=[{
                    "type": "computer_use_preview",
                    "display_width": self.display_width,
                    "display_height": self.display_height,
                    "environment": self.environment
                }],
                input=[
                    {
                        "type": "computer_call_output",
                        "call_id": call_id,
                        "acknowledged_safety_checks": [
                            {
                                "id": safety_check["id"]
                            } for safety_check in safety_checks
                        ]
                    }
                ],
                truncation="auto"
            )
            
            return response
        except Exception as e:
            raise Exception(f"Error acknowledging safety checks: {str(e)}")