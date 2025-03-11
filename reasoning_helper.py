"""
Reasoning capture integration helper for app.py

This module provides helper functions to integrate reasoning capture
in the main application.
"""
from reasoning_capture import ReasoningCapture, capture_after_screenshot

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