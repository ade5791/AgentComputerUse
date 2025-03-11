"""
Enhanced agent loop with integrated reasoning capture

This module provides an enhanced version of the agent loop with
built-in reasoning capture functionality.
"""

import time
import threading
from reasoning_helper import (
    process_screenshot_response,
    process_initial_response,
    process_safety_checks,
    create_agent_reasoning_capture
)

def enhanced_agent_loop(
    session_manager,
    session_id,
    task_id,
    browser,
    agent,
    task,
    add_log,
    stop_signal_getter
):
    """
    Enhanced agent loop with integrated reasoning capture.
    
    Args:
        session_manager: The session manager instance
        session_id: The current session ID
        task_id: The current task ID
        browser: The browser automation instance
        agent: The Computer Use Agent instance
        task: The task description
        add_log: Function to add logs
        stop_signal_getter: Function that returns True if the agent should stop
    """
    try:
        add_log("Starting enhanced Computer Use Agent...")
        
        # Initialize reasoning capture system
        reasoning_capture = create_agent_reasoning_capture(
            session_manager=session_manager,
            session_id=session_id,
            add_log_func=add_log
        )
        
        # Take initial screenshot
        screenshot = get_screenshot_as_base64(browser)
        
        # Update the session with the initial screenshot
        if session_id:
            session_manager.add_screenshot(
                session_id,
                screenshot
            )
        
        # Create initial request to Computer Use Agent
        response = agent.initial_request(
            task,
            screenshot
        )
        
        add_log(f"Received initial response from agent (ID: {response.id})")
        
        # Capture reasoning data for initial response
        process_initial_response(response, reasoning_capture)
        
        # Continue loop until stopped or no more actions
        while not stop_signal_getter():
            # Find computer_call items in the response
            computer_calls = [item for item in response.output if item.type == "computer_call"]
            
            if not computer_calls:
                # Check if there's a text output we can log
                text_outputs = [item for item in response.output if item.type == "text"]
                if text_outputs:
                    add_log(f"Agent message: {text_outputs[0].text}")
                
                add_log("Task completed. No more actions to perform.")
                break
                
            # Get the computer call
            computer_call = computer_calls[0]
            call_id = computer_call.call_id
            action = computer_call.action
            
            # Log the action
            add_log(f"Executing action: {action.type} (Call ID: {call_id})")
            
            # Check if safety checks need to be acknowledged
            if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                safety_checks = computer_call.pending_safety_checks
                
                # Log the safety checks
                safety_codes = [sc.code for sc in safety_checks]
                safety_messages = [sc.message for sc in safety_checks]
                add_log(f"Safety check required: {safety_codes}")
                
                # Process safety checks and capture reasoning data
                process_safety_checks(response, safety_checks, reasoning_capture)
                
                # Store and return safety check details to main app
                return {
                    "status": "safety_check",
                    "safety_checks": safety_checks,
                    "response_id": response.id,
                    "call_id": call_id
                }
                
            # Execute the action
            try:
                browser.execute_action(action)
                add_log(f"Action executed successfully: {action.type}")
                
                # Save the action in session history
                if session_id:
                    session_manager.add_action(
                        session_id,
                        {
                            "type": action.type,
                            "details": action.dict(),
                            "timestamp": time.time()
                        }
                    )
            except Exception as e:
                add_log(f"Error executing action: {str(e)}")
                # If action fails, we still continue with a new screenshot
            
            # Wait a moment for the action to take effect
            time.sleep(1)
            
            # Take a new screenshot
            screenshot = get_screenshot_as_base64(browser)
            
            # Update the session with the new screenshot
            if session_id:
                session_manager.add_screenshot(
                    session_id,
                    screenshot
                )
            
            # Send the screenshot back to the agent
            try:
                response = agent.send_screenshot(
                    response.id,
                    call_id,
                    screenshot
                )
                add_log(f"Sent screenshot to agent (Response ID: {response.id})")
                
                # Process screenshot response to capture reasoning data
                process_screenshot_response(response, action.type, reasoning_capture)
            except Exception as e:
                add_log(f"Error sending screenshot to agent: {str(e)}")
                break
            
        add_log("Agent loop completed successfully")
        
        # Update session status
        if session_id:
            session_manager.update_session(
                session_id,
                {"status": "completed"}
            )
            
        return {"status": "completed"}
    except Exception as e:
        add_log(f"Error in enhanced agent loop: {str(e)}")
        # Update session status on error
        if session_id:
            session_manager.update_session(
                session_id,
                {"status": "error", "error": str(e)}
            )
        return {"status": "error", "error": str(e)}

def enhanced_agent_loop_with_response(
    session_manager,
    session_id,
    task_id,
    browser,
    agent,
    initial_response,
    initial_call_id,
    safety_checks,
    add_log,
    stop_signal_getter
):
    """
    Continue the agent loop with an initial response (e.g., after safety check confirmation).
    
    Args:
        session_manager: The session manager instance
        session_id: The current session ID
        task_id: The current task ID
        browser: The browser automation instance
        agent: The Computer Use Agent instance
        initial_response: The initial response ID to continue from
        initial_call_id: The call ID to acknowledge
        safety_checks: The safety checks to acknowledge
        add_log: Function to add logs
        stop_signal_getter: Function that returns True if the agent should stop
    """
    try:
        add_log("Continuing agent execution after safety check confirmation...")
        
        # Initialize reasoning capture system
        reasoning_capture = create_agent_reasoning_capture(
            session_manager=session_manager,
            session_id=session_id,
            add_log_func=add_log
        )
        
        # Acknowledge safety checks
        response = agent.acknowledge_safety_checks(
            initial_response,
            initial_call_id,
            safety_checks
        )
        
        add_log(f"Safety checks acknowledged, continuing execution (Response ID: {response.id})")
        
        # Continue with regular loop
        while not stop_signal_getter():
            # Find computer_call items in the response
            computer_calls = [item for item in response.output if item.type == "computer_call"]
            
            if not computer_calls:
                # Check if there's a text output we can log
                text_outputs = [item for item in response.output if item.type == "text"]
                if text_outputs:
                    add_log(f"Agent message: {text_outputs[0].text}")
                
                add_log("Task completed. No more actions to perform.")
                break
                
            # Get the computer call
            computer_call = computer_calls[0]
            call_id = computer_call.call_id
            action = computer_call.action
            
            # Log the action
            add_log(f"Executing action: {action.type} (Call ID: {call_id})")
            
            # Check if safety checks need to be acknowledged
            if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                safety_checks = computer_call.pending_safety_checks
                
                # Log the safety checks
                safety_codes = [sc.code for sc in safety_checks]
                safety_messages = [sc.message for sc in safety_checks]
                add_log(f"Safety check required: {safety_codes}")
                
                # Process safety checks and capture reasoning data
                process_safety_checks(response, safety_checks, reasoning_capture)
                
                # Store and return safety check details to main app
                return {
                    "status": "safety_check",
                    "safety_checks": safety_checks,
                    "response_id": response.id,
                    "call_id": call_id
                }
                
            # Execute the action
            try:
                browser.execute_action(action)
                add_log(f"Action executed successfully: {action.type}")
                
                # Save the action in session history
                if session_id:
                    session_manager.add_action(
                        session_id,
                        {
                            "type": action.type,
                            "details": action.dict(),
                            "timestamp": time.time()
                        }
                    )
            except Exception as e:
                add_log(f"Error executing action: {str(e)}")
                # If action fails, we still continue with a new screenshot
            
            # Wait a moment for the action to take effect
            time.sleep(1)
            
            # Take a new screenshot
            screenshot = get_screenshot_as_base64(browser)
            
            # Update the session with the new screenshot
            if session_id:
                session_manager.add_screenshot(
                    session_id,
                    screenshot
                )
            
            # Send the screenshot back to the agent
            try:
                response = agent.send_screenshot(
                    response.id,
                    call_id,
                    screenshot
                )
                add_log(f"Sent screenshot to agent (Response ID: {response.id})")
                
                # Process screenshot response to capture reasoning data
                process_screenshot_response(response, action.type, reasoning_capture)
            except Exception as e:
                add_log(f"Error sending screenshot to agent: {str(e)}")
                break
            
        add_log("Agent loop completed successfully")
        
        # Update session status
        if session_id:
            session_manager.update_session(
                session_id,
                {"status": "completed"}
            )
            
        return {"status": "completed"}
    except Exception as e:
        add_log(f"Error in enhanced agent loop with response: {str(e)}")
        # Update session status on error
        if session_id:
            session_manager.update_session(
                session_id,
                {"status": "error", "error": str(e)}
            )
        return {"status": "error", "error": str(e)}
        
# Helper function to get screenshot as base64
def get_screenshot_as_base64(browser):
    """Get screenshot from browser and encode as base64"""
    from utils import get_screenshot_as_base64 as get_screenshot
    return get_screenshot(browser)