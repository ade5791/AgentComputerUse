"""
Reasoning data capture module for the Computer Use Agent.
This module handles capturing and storing reasoning data from agent responses.
"""
import time
import json
from datetime import datetime

class ReasoningCapture:
    """
    Reasoning data capture class that can be integrated with various parts
    of the Computer Use Agent application.
    """
    
    def __init__(self, session_manager=None, session_id=None, add_log_func=None):
        """
        Initialize the reasoning capture system.
        
        Args:
            session_manager: The session manager instance for storing data
            session_id: The ID of the current session
            add_log_func: Function to use for logging messages
        """
        self.session_manager = session_manager
        self.session_id = session_id
        self.add_log = add_log_func
        self.capture_count = 0
    
    def log(self, message):
        """Add a log message using the provided log function if available"""
        if self.add_log:
            self.add_log(message)
    
    def extract_from_response(self, response, action_type=None, event_type="agent_response"):
        """
        Extract reasoning data from an agent response and save it to the session.
        
        Args:
            response: The OpenAI response object
            action_type: Optional action type that this reasoning is related to
            event_type: Type of event that triggered this reasoning capture
            
        Returns:
            bool: True if reasoning data was extracted and saved
        """
        if not self.session_id or not self.session_manager:
            return False
            
        # Extract text content from the response
        text_outputs = [item for item in response.output if item.type == "text"]
        if not text_outputs:
            return False
            
        # Create reasoning data structure with detailed metadata
        reasoning_content = {
            "id": f"reason_{int(time.time())}_{self.capture_count}",
            "agent_reasoning": text_outputs[0].text,
            "timestamp": datetime.now().isoformat(),
            "action_performed": action_type,
            "event_type": event_type,
            "decision_points": [],
            "alternatives_considered": [],
            "content": {
                "text": text_outputs[0].text,
                "response_id": getattr(response, 'id', 'unknown')
            }
        }
        
        # Add the reasoning data to the session
        result = self.session_manager.add_reasoning_data(
            self.session_id,
            reasoning_content
        )
        
        if result:
            self.capture_count += 1
            self.log(f"Captured reasoning data ({event_type})")
            
        return result
    
    def capture_initial_reasoning(self, response):
        """
        Capture reasoning data from the initial agent response.
        
        Args:
            response: The OpenAI response object
            
        Returns:
            bool: True if reasoning data was captured successfully
        """
        return self.extract_from_response(
            response, 
            action_type="initial_assessment",
            event_type="initial_response"
        )
    
    def capture_after_action(self, response, action_type):
        """
        Capture reasoning data after an action is executed.
        
        Args:
            response: The OpenAI response object
            action_type: The type of action that was performed
            
        Returns:
            bool: True if reasoning data was captured successfully
        """
        return self.extract_from_response(
            response,
            action_type=action_type,
            event_type="post_action"
        )
    
    def capture_after_screenshot(self, response, action_type):
        """
        Capture reasoning data after a screenshot is processed.
        
        Args:
            response: The OpenAI response object
            action_type: The type of action that was performed
            
        Returns:
            bool: True if reasoning data was captured successfully
        """
        return self.extract_from_response(
            response,
            action_type=action_type,
            event_type="post_screenshot"
        )
    
    def capture_safety_check(self, response, safety_checks):
        """
        Capture reasoning data related to safety checks.
        
        Args:
            response: The OpenAI response object
            safety_checks: List of safety check objects
            
        Returns:
            bool: True if reasoning data was captured successfully
        """
        if not self.session_id or not self.session_manager:
            return False
            
        # Create safety check reasoning content
        reasoning_content = {
            "id": f"safety_{int(time.time())}_{self.capture_count}",
            "timestamp": datetime.now().isoformat(),
            "event_type": "safety_check",
            "content": {
                "safety_checks": [
                    {"code": sc.code, "message": sc.message}
                    for sc in safety_checks
                ],
                "response_id": getattr(response, 'id', 'unknown')
            }
        }
        
        # Add the reasoning data to the session
        result = self.session_manager.add_reasoning_data(
            self.session_id,
            reasoning_content
        )
        
        if result:
            self.capture_count += 1
            self.log("Captured safety check reasoning data")
            
        return result

# Backward compatibility functions
def extract_reasoning_data(response, action_type=None, session_manager=None, session_id=None):
    """
    Legacy function for backward compatibility.
    Extract reasoning data from an OpenAI response and save it to the session.
    
    Args:
        response: The OpenAI response object
        action_type: Optional action type that this reasoning is related to
        session_manager: The session manager instance
        session_id: The current session ID
        
    Returns:
        bool: True if reasoning data was extracted and saved
    """
    capture = ReasoningCapture(session_manager, session_id)
    return capture.extract_from_response(response, action_type)

def capture_after_screenshot(response, action_type, session_manager, session_id, add_log_func=None):
    """
    Legacy function for backward compatibility.
    Helper function to capture reasoning data after a screenshot is processed.
    
    Args:
        response: The OpenAI response object 
        action_type: The type of action that was performed
        session_manager: The session manager instance
        session_id: The current session ID
        add_log_func: Optional function to log messages
        
    Returns:
        bool: True if reasoning data was captured successfully
    """
    capture = ReasoningCapture(session_manager, session_id, add_log_func)
    return capture.capture_after_screenshot(response, action_type)