import os
import json
import time
import threading
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import uvicorn

from browser_automation import BrowserAutomation
from computer_use_agent import ComputerUseAgent
from utils import get_screenshot_as_base64
from session_manager import SessionManager

# Initialize FastAPI app
app = FastAPI(
    title="Computer Use Agent API",
    description="API for automating browser tasks using OpenAI's Computer Use Agent",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize session manager
session_manager = SessionManager()

# Store active agent sessions
active_sessions = {}

# Models for request/response
class TaskRequest(BaseModel):
    task: str
    environment: str = "browser"
    display_width: int = 1024
    display_height: int = 768
    headless: bool = True
    starting_url: str = "https://www.google.com"
    api_key: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    task_id: str
    status: str
    session_url: str

class StatusResponse(BaseModel):
    session_id: str
    task_id: str
    status: str
    logs: List[str]
    current_screenshot: Optional[str] = None

class SessionControlRequest(BaseModel):
    session_id: str
    task_id: str

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Helper function to add logs
def add_log(session_id, message):
    """Add a message to the logs and update session data"""
    timestamp = time.strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    
    # Update the session logs
    if session_id:
        session_manager.add_log(session_id, log_msg)
    
    return log_msg

# Function to run the agent loop
def agent_loop(session_id, task_id):
    """Main loop for the Computer Use Agent"""
    if session_id not in active_sessions:
        return
    
    session_data = active_sessions[session_id]
    session_data["status"] = "running"
    
    try:
        add_log(session_id, "Starting Computer Use Agent...")
        browser = session_data["browser"]
        agent = session_data["agent"]
        task = session_data["task"]
        
        # Take initial screenshot
        screenshot = get_screenshot_as_base64(browser)
        
        # Update the session with the initial screenshot
        session_manager.add_screenshot(session_id, screenshot)
        
        # Create initial request to Computer Use Agent
        response = agent.initial_request(task, screenshot)
        
        add_log(session_id, f"Received initial response from agent (ID: {response.id})")
        
        # Continue loop until stopped or no more actions
        while not session_data.get("stop_requested", False):
            # Check if paused
            if session_data.get("paused", False):
                time.sleep(1)
                continue
                
            # Find computer_call items in the response
            computer_calls = [item for item in response.output if item.type == "computer_call"]
            
            if not computer_calls:
                # Check if there's a text output we can log
                text_outputs = [item for item in response.output if item.type == "text"]
                if text_outputs:
                    add_log(session_id, f"Agent message: {text_outputs[0].text}")
                
                add_log(session_id, "Task completed. No more actions to perform.")
                break
                
            # Get the computer call
            computer_call = computer_calls[0]
            call_id = computer_call.call_id
            action = computer_call.action
            
            # Log the action
            add_log(session_id, f"Executing action: {action.type} (Call ID: {call_id})")
            
            # Check if safety checks need to be acknowledged
            if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                safety_checks = computer_call.pending_safety_checks
                add_log(session_id, f"Safety check required: {[sc.code for sc in safety_checks]}")
                
                # Here we auto-acknowledge all safety checks for simplicity
                # In a production system, you might want to ask the user for confirmation
                response = agent.acknowledge_safety_checks(
                    response.id, 
                    call_id,
                    safety_checks
                )
                continue
                
            # Execute the action
            try:
                browser.execute_action(action)
                add_log(session_id, f"Action executed successfully: {action.type}")
            except Exception as e:
                add_log(session_id, f"Error executing action: {str(e)}")
                # If action fails, we still continue with a new screenshot
            
            # Wait a moment for the action to take effect
            time.sleep(1)
            
            # Take a new screenshot
            screenshot = get_screenshot_as_base64(browser)
            
            # Update the session with the new screenshot
            session_manager.add_screenshot(session_id, screenshot)
            
            # Send the screenshot back to the agent
            try:
                response = agent.send_screenshot(
                    response.id,
                    call_id,
                    screenshot
                )
                add_log(session_id, f"Sent screenshot to agent (Response ID: {response.id})")
            except Exception as e:
                add_log(session_id, f"Error sending screenshot to agent: {str(e)}")
                break
            
        add_log(session_id, "Agent loop stopped")
        
        # Update session status
        session_manager.update_session(
            session_id,
            {"status": "completed" if not session_data.get("stop_requested", False) else "stopped"}
        )
        
        session_data["status"] = "completed" if not session_data.get("stop_requested", False) else "stopped"
        
    except Exception as e:
        error_message = f"Error in agent loop: {str(e)}"
        add_log(session_id, error_message)
        # Update session status on error
        session_manager.update_session(
            session_id,
            {"status": "error", "error": str(e)}
        )
        session_data["status"] = "error"
        session_data["error"] = str(e)
    finally:
        session_data["thread_running"] = False

# API endpoints
@app.post("/api/tasks", response_model=SessionResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks, request: Request):
    """Create a new task and start a browser automation session"""
    # Get API key from request or environment
    api_key = task_request.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key is required")
    
    # Create a new session
    browser_config = {
        "environment": task_request.environment,
        "display_width": task_request.display_width,
        "display_height": task_request.display_height,
        "headless": task_request.headless,
        "starting_url": task_request.starting_url
    }
    
    session_id = session_manager.create_session(
        task=task_request.task,
        environment=task_request.environment,
        browser_config=browser_config
    )
    
    task_id = str(uuid.uuid4())
    
    add_log(session_id, f"Created new session: {session_id} with task ID: {task_id}")
    
    # Initialize browser
    try:
        browser = BrowserAutomation(
            headless=task_request.headless,
            width=task_request.display_width,
            height=task_request.display_height,
            starting_url=task_request.starting_url
        )
        add_log(session_id, f"Browser started and navigated to {task_request.starting_url}")
    except Exception as e:
        error_message = f"Failed to start browser: {str(e)}"
        add_log(session_id, error_message)
        session_manager.update_session(
            session_id,
            {"status": "error", "error": error_message}
        )
        raise HTTPException(status_code=500, detail=error_message)
    
    # Initialize the Computer Use Agent
    agent = ComputerUseAgent(
        api_key=api_key,
        environment=task_request.environment,
        display_width=task_request.display_width,
        display_height=task_request.display_height
    )
    
    # Store session data
    active_sessions[session_id] = {
        "task_id": task_id,
        "task": task_request.task,
        "browser": browser,
        "agent": agent,
        "status": "starting",
        "thread_running": True,
        "stop_requested": False,
        "paused": False,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Start the agent loop in a background task
    background_tasks.add_task(agent_loop, session_id, task_id)
    
    # Get base URL from request or use default
    host = request.headers.get("host", "0.0.0.0:5000")
    base_url = f"http://{host}"
    
    # Generate session URL
    session_url = session_manager.get_session_link(session_id, base_url)
    
    return SessionResponse(
        session_id=session_id,
        task_id=task_id,
        status="starting",
        session_url=session_url
    )

@app.get("/api/sessions/{session_id}/status", response_model=StatusResponse)
async def get_session_status(session_id: str, task_id: str):
    """Get the status of a session"""
    # Verify session exists
    if session_id not in active_sessions:
        # Try to get from session manager
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Return session data from storage
        logs = [log["message"] for log in session_data.get("logs", [])]
        current_screenshot = None
        if session_data.get("screenshots") and len(session_data["screenshots"]) > 0:
            current_screenshot = session_data["screenshots"][-1]["data"]
            
        return StatusResponse(
            session_id=session_id,
            task_id="completed",  # This is a completed session, so we don't have the original task_id
            status=session_data.get("status", "unknown"),
            logs=logs,
            current_screenshot=current_screenshot
        )
    
    # Get session data from active sessions
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # Get session data from storage to get logs and screenshots
    stored_session = session_manager.get_session(session_id)
    logs = [log["message"] for log in stored_session.get("logs", [])]
    current_screenshot = None
    if stored_session.get("screenshots") and len(stored_session["screenshots"]) > 0:
        current_screenshot = stored_session["screenshots"][-1]["data"]
    
    return StatusResponse(
        session_id=session_id,
        task_id=task_id,
        status=session_data["status"],
        logs=logs,
        current_screenshot=current_screenshot
    )

@app.post("/api/sessions/{session_id}/stop", response_model=ApiResponse)
async def stop_session(session_id: str, request: SessionControlRequest):
    """Stop a running session"""
    # Verify session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session data
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != request.task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # Request stop
    session_data["stop_requested"] = True
    add_log(session_id, "Stop requested")
    
    return ApiResponse(
        success=True,
        message="Stop requested",
        data={"session_id": session_id, "status": "stopping"}
    )

@app.post("/api/sessions/{session_id}/pause", response_model=ApiResponse)
async def pause_session(session_id: str, request: SessionControlRequest):
    """Pause a running session"""
    # Verify session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session data
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != request.task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # Request pause
    session_data["paused"] = True
    add_log(session_id, "Session paused")
    
    return ApiResponse(
        success=True,
        message="Session paused",
        data={"session_id": session_id, "status": "paused"}
    )

@app.post("/api/sessions/{session_id}/resume", response_model=ApiResponse)
async def resume_session(session_id: str, request: SessionControlRequest):
    """Resume a paused session"""
    # Verify session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session data
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != request.task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # If not paused, return error
    if not session_data.get("paused", False):
        raise HTTPException(status_code=400, detail="Session is not paused")
    
    # Resume session
    session_data["paused"] = False
    add_log(session_id, "Session resumed")
    
    return ApiResponse(
        success=True,
        message="Session resumed",
        data={"session_id": session_id, "status": "running"}
    )

@app.post("/api/sessions/{session_id}/cleanup", response_model=ApiResponse)
async def cleanup_session(session_id: str, request: SessionControlRequest):
    """Clean up resources for a session"""
    # Verify session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found or already cleaned up")
    
    # Get session data
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != request.task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # Stop the session if still running
    if not session_data.get("stop_requested", False):
        session_data["stop_requested"] = True
        add_log(session_id, "Stop requested for cleanup")
    
    # Close the browser
    try:
        if "browser" in session_data and session_data["browser"]:
            session_data["browser"].close()
            add_log(session_id, "Browser closed for cleanup")
    except Exception as e:
        add_log(session_id, f"Error closing browser during cleanup: {str(e)}")
    
    # Remove from active sessions
    active_sessions.pop(session_id, None)
    
    return ApiResponse(
        success=True,
        message="Session cleaned up",
        data={"session_id": session_id, "status": "cleaned"}
    )

@app.get("/api/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    return ApiResponse(
        success=True,
        message="API is healthy",
        data={"status": "ok", "active_sessions": len(active_sessions)}
    )

# Run API server when this file is executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)