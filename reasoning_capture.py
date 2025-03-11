"""
Reasoning data capture module for the Computer Use Agent
"""
import time

def extract_reasoning_data(response, action_type=None, session_manager=None, session_id=None):
    """
    Extract reasoning data from an OpenAI response and save it to the session.
    
    Args:
        response: The OpenAI response object
        action_type: Optional action type that this reasoning is related to
        session_manager: The session manager instance
        session_id: The current session ID
        
    Returns:
        bool: True if reasoning data was extracted and saved
    """
    if not session_id or not session_manager:
        return False
        
    # Extract text content from the response
    text_outputs = [item for item in response.output if item.type == "text"]
    if not text_outputs:
        return False
        
    # Create reasoning data structure
    reasoning_content = {
        "agent_reasoning": text_outputs[0].text,
        "timestamp": time.time(),
        "action_performed": action_type,
        "decision_points": [],
        "alternatives_considered": []
    }
    
    # Add the reasoning data to the session
    result = session_manager.add_reasoning_data(
        session_id,
        reasoning_content
    )
    
    return result

def capture_after_screenshot(response, action_type, session_manager, session_id, add_log_func=None):
    """
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
    result = extract_reasoning_data(
        response,
        action_type=action_type,
        session_manager=session_manager,
        session_id=session_id
    )
    
    if result and add_log_func:
        add_log_func("Captured reasoning data after screenshot processing")
    
    return result