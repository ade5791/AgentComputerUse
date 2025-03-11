"""
Reasoning capture integration helper for app.py

This module provides helper functions to integrate reasoning capture
in the main application. These helper functions can be called 
directly from app.py to avoid having to modify the core application code.
"""
import time
from reasoning_capture import ReasoningCapture, capture_after_screenshot

# Global reasoning capture instance 
_reasoning_capture_instance = None

def process_screenshot_response(response, action_type, reasoning_capture):
    """
    Process a screenshot response from the agent and capture reasoning data.
    
    Args:
        response: The agent's response after sending a screenshot
        action_type: The type of action that was performed before the screenshot
        reasoning_capture: The ReasoningCapture instance
        
    Returns:
        bool: True if reasoning data was captured successfully
    """
    # Capture reasoning data after screenshot processing
    return reasoning_capture.capture_after_screenshot(response, action_type=action_type)

def process_initial_response(response, reasoning_capture):
    """
    Process the initial response from the agent and capture reasoning data.
    
    Args:
        response: The agent's initial response
        reasoning_capture: The ReasoningCapture instance
        
    Returns:
        bool: True if reasoning data was captured successfully
    """
    return reasoning_capture.capture_initial_reasoning(response)

def process_safety_checks(response, safety_checks, reasoning_capture):
    """
    Process safety checks from the agent and capture reasoning data.
    
    Args:
        response: The agent's response that triggered safety checks
        safety_checks: The list of safety checks
        reasoning_capture: The ReasoningCapture instance
        
    Returns:
        bool: True if reasoning data was captured successfully
    """
    return reasoning_capture.capture_safety_check(response, safety_checks)
    
def create_agent_reasoning_capture(session_manager, session_id, add_log_func=None):
    """
    Create and configure a ReasoningCapture instance for agent use.
    Stores the instance globally for easy access from other functions.
    
    Args:
        session_manager: The session manager instance
        session_id: The current session ID
        add_log_func: Optional function to use for logging
        
    Returns:
        ReasoningCapture: The configured reasoning capture instance
    """
    global _reasoning_capture_instance
    _reasoning_capture_instance = ReasoningCapture(
        session_manager=session_manager,
        session_id=session_id,
        add_log_func=add_log_func
    )
    return _reasoning_capture_instance
    
def get_reasoning_capture():
    """
    Get the current global reasoning capture instance.
    
    Returns:
        ReasoningCapture: The current reasoning capture instance or None if not initialized
    """
    return _reasoning_capture_instance