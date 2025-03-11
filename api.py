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
from mock_browser_automation import MockBrowserAutomation
from computer_use_agent import ComputerUseAgent
from utils import get_screenshot_as_base64
from session_manager import SessionManager
from setup_app import check_install_dependencies, get_browser_environment
from reasoning_capture import ReasoningCapture, capture_after_screenshot

# Check and install dependencies when API starts
check_install_dependencies()

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
    user_id: Optional[str] = None
    session_name: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: str = "normal"
    timeout_seconds: Optional[int] = None
    max_actions: Optional[int] = None

class SessionResponse(BaseModel):
    session_id: str
    task_id: str
    status: str
    session_url: str
    name: Optional[str] = None
    created_at: Optional[str] = None

class SessionListRequest(BaseModel):
    limit: int = 50
    filter_by: Optional[Dict[str, Any]] = None
    sort_field: str = "created_at"
    sort_direction: str = "desc"
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    
class SessionUpdateRequest(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[str] = None
    user_id: Optional[str] = None

class SafetyCheck(BaseModel):
    id: str
    code: str
    message: str
    
class ReasoningItem(BaseModel):
    id: str
    content: List[Dict[str, Any]] = []
    
class StatusResponse(BaseModel):
    session_id: str
    task_id: str
    status: str
    logs: List[str]
    current_screenshot: Optional[str] = None
    pending_safety_checks: Optional[List[SafetyCheck]] = None
    reasoning: Optional[List[ReasoningItem]] = None

class SessionControlRequest(BaseModel):
    session_id: str
    task_id: str

class SafetyCheckConfirmationRequest(BaseModel):
    session_id: str
    task_id: str
    confirm: bool = True

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

# Function to continue the agent loop with a response
def continue_agent_loop_with_response(session_id, response):
    """Continue agent loop with a response (e.g., after safety check confirmation)"""
    if session_id not in active_sessions:
        return
    
    session_data = active_sessions[session_id]
    
    try:
        browser = session_data["browser"]
        agent = session_data["agent"]
        
        add_log(session_id, f"Continuing agent loop with response (ID: {response.id})")
        
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
                safety_codes = [sc.code for sc in safety_checks]
                add_log(session_id, f"Safety check required: {safety_codes}")
                
                # Store safety checks in session data so they can be displayed to user
                session_data["pending_safety_checks"] = safety_checks
                session_data["pending_safety_response_id"] = response.id
                session_data["pending_safety_call_id"] = call_id
                session_data["awaiting_safety_confirmation"] = True
                session_data["paused"] = True  # Pause while waiting for confirmation
                
                # Update session status
                session_manager.update_session(
                    session_id,
                    {"status": "awaiting_safety_confirmation", "safety_checks": safety_codes}
                )
                
                add_log(session_id, "Session paused waiting for safety check confirmation")
                break
                
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
        
        # Store the response for access to reasoning data
        session_data["last_response"] = response
        
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
                safety_codes = [sc.code for sc in safety_checks]
                add_log(session_id, f"Safety check required: {safety_codes}")
                
                # Store safety checks in session data so they can be displayed to user
                session_data["pending_safety_checks"] = safety_checks
                session_data["pending_safety_response_id"] = response.id
                session_data["pending_safety_call_id"] = call_id
                session_data["awaiting_safety_confirmation"] = True
                session_data["paused"] = True  # Pause while waiting for confirmation
                
                # Update session status
                session_manager.update_session(
                    session_id,
                    {"status": "awaiting_safety_confirmation", "safety_checks": safety_codes}
                )
                
                add_log(session_id, "Session paused waiting for safety check confirmation")
                break
                
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
    
    # Initialize browser based on environment
    try:
        # Check which browser automation to use
        browser_env = get_browser_environment()
        
        if browser_env == "mock":
            add_log(session_id, "Using mock browser automation (Playwright not available in this environment)")
            browser = MockBrowserAutomation(
                headless=task_request.headless,
                width=task_request.display_width,
                height=task_request.display_height,
                starting_url=task_request.starting_url
            )
        else:
            add_log(session_id, "Using real browser automation with Playwright")
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
        # Try with mock browser as fallback
        try:
            add_log(session_id, "Trying with mock browser as fallback...")
            browser = MockBrowserAutomation(
                headless=task_request.headless,
                width=task_request.display_width,
                height=task_request.display_height,
                starting_url=task_request.starting_url
            )
            add_log(session_id, f"Mock browser started successfully as fallback")
            session_manager.update_session(
                session_id,
                {"status": "starting", "is_mock": True}
            )
        except Exception as e2:
            error_message = f"Failed to start browser even with fallback: {str(e)} -> {str(e2)}"
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
        
        # Get reasoning data from stored session
        reasoning_items = None
        if session_data.get("reasoning_data"):
            reasoning_items = []
            for item in session_data.get("reasoning_data", []):
                reasoning_items.append(ReasoningItem(
                    id=item.get("id", str(uuid.uuid4())),
                    content=item.get("content", [])
                ))
            
        return StatusResponse(
            session_id=session_id,
            task_id="completed",  # This is a completed session, so we don't have the original task_id
            status=session_data.get("status", "unknown"),
            logs=logs,
            current_screenshot=current_screenshot,
            reasoning=reasoning_items
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
    
    # Check if there are pending safety checks to include in the response
    pending_safety_checks = None
    if session_data.get("awaiting_safety_confirmation", False) and session_data.get("pending_safety_checks"):
        # Convert safety checks to API response format
        pending_safety_checks = []
        for sc in session_data["pending_safety_checks"]:
            pending_safety_checks.append(SafetyCheck(
                id=sc.id,
                code=sc.code,
                message=sc.message
            ))
    
    # Extract reasoning items from the latest agent response if available
    reasoning_items = None
    if hasattr(session_data.get("last_response", {}), 'output'):
        # Find all reasoning items in the response output
        reasoning = [
            ReasoningItem(
                id=item.id,
                content=item.content if hasattr(item, 'content') else []
            )
            for item in session_data["last_response"].output 
            if hasattr(item, 'type') and item.type == "reasoning"
        ]
        
        if reasoning:
            reasoning_items = reasoning
    
    return StatusResponse(
        session_id=session_id,
        task_id=task_id,
        status=session_data["status"],
        logs=logs,
        current_screenshot=current_screenshot,
        pending_safety_checks=pending_safety_checks,
        reasoning=reasoning_items
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

@app.post("/api/sessions/{session_id}/confirm-safety-check", response_model=ApiResponse)
async def confirm_safety_check(session_id: str, request: SafetyCheckConfirmationRequest, background_tasks: BackgroundTasks):
    """Confirm or reject safety checks for a session"""
    # Verify session exists
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session data
    session_data = active_sessions[session_id]
    
    # Verify task ID
    if session_data["task_id"] != request.task_id:
        raise HTTPException(status_code=403, detail="Invalid task ID")
    
    # Check if there are pending safety checks
    if not session_data.get("awaiting_safety_confirmation", False) or not session_data.get("pending_safety_checks"):
        raise HTTPException(status_code=400, detail="No pending safety checks to confirm")
    
    if request.confirm:
        # User approved safety checks, acknowledge them
        try:
            # Get required data for acknowledgment
            agent = session_data["agent"]
            response_id = session_data["pending_safety_response_id"]
            call_id = session_data["pending_safety_call_id"]
            safety_checks = session_data["pending_safety_checks"]
            
            # Acknowledge safety checks
            add_log(session_id, "User approved safety checks")
            
            # Call the OpenAI API to acknowledge safety checks
            response = agent.acknowledge_safety_checks(
                response_id,
                call_id,
                safety_checks
            )
            
            # Reset safety check flags
            session_data["awaiting_safety_confirmation"] = False
            session_data["pending_safety_checks"] = None
            session_data["pending_safety_response_id"] = None
            session_data["pending_safety_call_id"] = None
            session_data["paused"] = False
            session_data["status"] = "running"
            
            # Update session status
            session_manager.update_session(
                session_id,
                {"status": "running"}
            )
            
            # Continue processing in background
            background_tasks.add_task(continue_agent_loop_with_response, session_id, response)
            
            return ApiResponse(
                success=True,
                message="Safety checks confirmed, processing continues",
                data={"session_id": session_id, "status": "running"}
            )
        except Exception as e:
            error_message = f"Error acknowledging safety checks: {str(e)}"
            add_log(session_id, error_message)
            
            return ApiResponse(
                success=False,
                message=error_message,
                data={"session_id": session_id, "status": "error"}
            )
    else:
        # User rejected safety checks, stop the agent
        add_log(session_id, "User rejected safety checks, stopping agent")
        
        # Update session data
        session_data["awaiting_safety_confirmation"] = False
        session_data["pending_safety_checks"] = None
        session_data["pending_safety_response_id"] = None
        session_data["pending_safety_call_id"] = None
        session_data["stop_requested"] = True
        session_data["status"] = "stopped"
        
        # Update session status
        session_manager.update_session(
            session_id,
            {"status": "stopped", "reason": "safety_check_rejected"}
        )
        
        return ApiResponse(
            success=True,
            message="Safety checks rejected, agent stopped",
            data={"session_id": session_id, "status": "stopped"}
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

@app.get("/api/sessions", response_model=ApiResponse)
async def list_sessions(
    limit: int = 50,
    sort_field: str = "created_at",
    sort_direction: str = "desc",
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None
):
    """List all sessions with filtering options"""
    tags = [tag] if tag else None
    
    sessions = session_manager.list_sessions(
        limit=limit,
        sort_field=sort_field,
        sort_direction=sort_direction,
        user_id=user_id,
        tags=tags,
        status=status
    )
    
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(sessions)} sessions",
        data={"sessions": sessions}
    )

@app.post("/api/sessions/batch", response_model=ApiResponse)
async def list_sessions_with_filters(request: SessionListRequest):
    """List sessions with advanced filtering options"""
    sessions = session_manager.list_sessions(
        limit=request.limit,
        filter_by=request.filter_by,
        sort_field=request.sort_field,
        sort_direction=request.sort_direction,
        user_id=request.user_id,
        tags=request.tags,
        status=request.status
    )
    
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(sessions)} sessions",
        data={"sessions": sessions}
    )

@app.get("/api/sessions/active", response_model=ApiResponse)
async def get_active_sessions():
    """Get all currently active sessions"""
    active_count = session_manager.get_active_sessions_count()
    active_sessions_list = []
    
    for session_id, thread_info in session_manager.active_threads.items():
        if thread_info["thread"].is_alive():
            session_data = session_manager.get_session(session_id)
            if session_data:
                active_sessions_list.append({
                    "id": session_id,
                    "task_id": thread_info.get("task_id"),
                    "started_at": thread_info.get("started_at"),
                    "status": session_data.get("status", "running"),
                    "name": session_data.get("name", f"Session {session_id[:8]}"),
                    "task": session_data.get("task", "")
                })
    
    return ApiResponse(
        success=True,
        message=f"Found {active_count} active sessions",
        data={"active_sessions": active_sessions_list}
    )

@app.get("/api/sessions/{session_id}/details", response_model=ApiResponse)
async def get_session_details(session_id: str):
    """Get detailed information about a specific session"""
    session_data = session_manager.get_session(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Check if session has an active thread
    is_active = session_manager.is_session_active(session_id)
    
    # Get the latest screenshot if available
    latest_screenshot = None
    if "screenshots" in session_data and session_data["screenshots"]:
        latest_screenshot = session_data["screenshots"][-1]["data"]
    
    result = {
        "session": session_data,
        "is_active": is_active,
        "latest_screenshot": latest_screenshot,
        "logs_count": len(session_data.get("logs", [])),
        "screenshots_count": len(session_data.get("screenshots", []))
    }
    
    return ApiResponse(
        success=True,
        message=f"Retrieved details for session {session_id}",
        data=result
    )

@app.put("/api/sessions/{session_id}", response_model=ApiResponse)
async def update_session_details(session_id: str, request: SessionUpdateRequest):
    """Update session metadata"""
    session_data = session_manager.get_session(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Build updates dictionary with only provided fields
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.priority is not None:
        updates["priority"] = request.priority
    if request.user_id is not None:
        updates["user_id"] = request.user_id
    
    # Update the session
    success = session_manager.update_session(session_id, updates)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update session {session_id}")
    
    return ApiResponse(
        success=True,
        message=f"Session {session_id} updated successfully",
        data={"session_id": session_id, "updates": updates}
    )

@app.post("/api/sessions/cleanup", response_model=ApiResponse)
async def cleanup_old_sessions(days_old: int = 7):
    """Clean up sessions older than specified days"""
    if days_old < 1:
        raise HTTPException(status_code=400, detail="Days parameter must be at least 1")
    
    cleaned_count = session_manager.cleanup_old_sessions(days_old=days_old)
    
    return ApiResponse(
        success=True,
        message=f"Cleaned up {cleaned_count} sessions older than {days_old} days",
        data={"cleaned_count": cleaned_count}
    )

@app.get("/api/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    active_count = session_manager.get_active_sessions_count()
    
    return ApiResponse(
        success=True,
        message="API is healthy",
        data={
            "status": "ok", 
            "active_sessions": active_count,
            "version": "1.0.0",
            "browser_environment": get_browser_environment()
        }
    )

# Run API server when this file is executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)