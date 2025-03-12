import streamlit as st
import base64
import threading
import time
import io
import uuid
from PIL import Image
import os

# Import the reasoning capture module
from reasoning_capture import ReasoningCapture, extract_reasoning_data as rc_extract_reasoning_data, capture_after_screenshot
from reasoning_helper import process_screenshot_response, process_initial_response, process_safety_checks
from enhanced_agent import enhanced_agent_loop, enhanced_agent_loop_with_response

from browser_automation import BrowserAutomation
from mock_browser_automation import MockBrowserAutomation
from computer_use_agent import ComputerUseAgent
from utils import get_screenshot_as_base64
from session_manager import SessionManager
from setup_app import check_install_dependencies, get_browser_environment
import session_replay

# Check and install dependencies when app starts
check_install_dependencies()

# Set page configuration
st.set_page_config(
    page_title="Computer Use Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
# Use dict-like syntax for more reliable initialization across Python versions
if 'agent_running' not in st.session_state:
    st.session_state['agent_running'] = False
if 'agent' not in st.session_state:
    st.session_state['agent'] = None
if 'browser' not in st.session_state:
    st.session_state['browser'] = None
if 'logs' not in st.session_state:
    st.session_state['logs'] = []
if 'screenshot' not in st.session_state:
    st.session_state['screenshot'] = None
if 'stop_agent' not in st.session_state:
    st.session_state['stop_agent'] = False
if 'agent_thread' not in st.session_state:
    st.session_state['agent_thread'] = None
if 'session_manager' not in st.session_state:
    st.session_state['session_manager'] = SessionManager()
if 'current_session_id' not in st.session_state:
    st.session_state['current_session_id'] = None
if 'current_task_id' not in st.session_state:
    st.session_state['current_task_id'] = None
# Safety check related state variables
if 'pending_safety_checks' not in st.session_state:
    st.session_state['pending_safety_checks'] = None
if 'pending_safety_response_id' not in st.session_state:
    st.session_state['pending_safety_response_id'] = None
if 'pending_safety_call_id' not in st.session_state:
    st.session_state['pending_safety_call_id'] = None
if 'awaiting_safety_confirmation' not in st.session_state:
    st.session_state['awaiting_safety_confirmation'] = False

# Check for query parameters
query_params = st.query_params

# Check if we should show the dashboard
if 'show_dashboard' in query_params and query_params['show_dashboard'] == 'true':
    # Import dashboard functionality
    import dashboard
    dashboard.load_dashboard()
    # Stop further execution of the main app since we're showing the dashboard
    st.stop()

# Check if we should show the API documentation
if 'show_api_docs' in query_params and query_params['show_api_docs'] == 'true':
    # Import API documentation functionality
    import api_docs
    api_docs.load_api_docs()
    # Stop further execution of the main app since we're showing the API docs
    st.stop()
    
# Check if we should show the session replay
if 'replay_session' in query_params:
    # Load session replay view
    session_replay.load_session_replay(query_params['replay_session'], st.session_state.session_manager)
    # Stop further execution of the main app since we're showing the session replay
    st.stop()

# Check for session ID in URL query parameters    
if 'session' in query_params:
    session_id = query_params['session']
    if st.session_state.current_session_id != session_id:
        # Load the session data
        session_data = st.session_state.session_manager.get_session(session_id)
        if session_data:
            st.session_state.current_session_id = session_id
            # Load session configuration
            if 'browser_config' in session_data:
                config = session_data['browser_config']
                st.session_state.environment = config.get('environment', 'browser')
                st.session_state.display_width = config.get('display_width', 1024)
                st.session_state.display_height = config.get('display_height', 768)
                st.session_state.headless = config.get('headless', False)
                st.session_state.starting_url = config.get('starting_url', 'https://www.google.com')
            
            if 'task' in session_data:
                st.session_state.task = session_data['task']
                
            if 'logs' in session_data:
                # Convert to the format we use in the app
                st.session_state.logs = [log['message'] for log in session_data['logs']]
                
            if 'screenshots' in session_data and session_data['screenshots']:
                # Get the latest screenshot
                st.session_state.screenshot = session_data['screenshots'][-1]['data']

def add_log(message):
    """Add a message to the logs and update session data if available"""
    timestamp = time.strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    
    # Use dict-style access for more reliable operation across Python versions
    if 'logs' not in st.session_state:
        st.session_state['logs'] = []
    st.session_state['logs'].append(log_msg)
    
    # If we have an active session, update the session logs
    if 'current_session_id' in st.session_state and st.session_state['current_session_id']:
        if 'session_manager' not in st.session_state:
            st.session_state['session_manager'] = SessionManager()
        st.session_state['session_manager'].add_log(
            st.session_state['current_session_id'], 
            log_msg
        )
    
def extract_reasoning_data(response, action_type=None):
    """
    Extract reasoning data from an OpenAI response and save it to the session.
    
    Args:
        response: The OpenAI response object
        action_type: Optional action type that this reasoning is related to
        
    Returns:
        bool: True if reasoning data was extracted and saved
    """
    # Ensure session state variables exist with dict-style access
    if 'current_session_id' not in st.session_state or not st.session_state['current_session_id']:
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
    
    # Ensure session_manager exists
    if 'session_manager' not in st.session_state:
        st.session_state['session_manager'] = SessionManager()
    
    # Add the reasoning data to the session
    result = st.session_state['session_manager'].add_reasoning_data(
        st.session_state['current_session_id'],
        reasoning_content
    )
    
    if result:
        add_log("Captured reasoning data from agent")
        return True
    return False
    
def agent_loop():
    """Main loop for the Computer Use Agent"""
    try:
        add_log("Starting Computer Use Agent...")
        st.session_state.stop_agent = False
        
        # Initialize reasoning capture system
        reasoning_capture = create_reasoning_capture()
        
        # Take initial screenshot
        screenshot = get_screenshot_as_base64(st.session_state.browser)
        st.session_state.screenshot = screenshot
        
        # Update the session with the initial screenshot
        if st.session_state.current_session_id:
            st.session_state.session_manager.add_screenshot(
                st.session_state.current_session_id,
                screenshot
            )
        
        # Create initial request to Computer Use Agent
        response = st.session_state.agent.initial_request(
            st.session_state.task,
            screenshot
        )
        
        add_log(f"Received initial response from agent (ID: {response.id})")
        
        # Capture reasoning data for initial response
        reasoning_capture.capture_initial_reasoning(response)
        
        # Continue loop until stopped or no more actions
        while not st.session_state.stop_agent:
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
                
                # Store safety check details in session state for user confirmation
                st.session_state.pending_safety_checks = safety_checks
                st.session_state.pending_safety_response_id = response.id
                st.session_state.pending_safety_call_id = call_id
                st.session_state.awaiting_safety_confirmation = True
                
                # We'll let the agent loop exit and show confirmation UI to the user
                break
                
            # Execute the action
            try:
                st.session_state.browser.execute_action(action)
                add_log(f"Action executed successfully: {action.type}")
            except Exception as e:
                add_log(f"Error executing action: {str(e)}")
                # If action fails, we still continue with a new screenshot
            
            # Wait a moment for the action to take effect
            time.sleep(1)
            
            # Take a new screenshot
            screenshot = get_screenshot_as_base64(st.session_state.browser)
            st.session_state.screenshot = screenshot
            
            # Update the session with the new screenshot
            if st.session_state.current_session_id:
                st.session_state.session_manager.add_screenshot(
                    st.session_state.current_session_id,
                    screenshot
                )
            
            # Send the screenshot back to the agent
            try:
                response = st.session_state.agent.send_screenshot(
                    response.id,
                    call_id,
                    screenshot
                )
                add_log(f"Sent screenshot to agent (Response ID: {response.id})")
            except Exception as e:
                add_log(f"Error sending screenshot to agent: {str(e)}")
                break
            
        add_log("Agent loop stopped")
        
        # Update session status
        if st.session_state.current_session_id:
            st.session_state.session_manager.update_session(
                st.session_state.current_session_id,
                {"status": "completed"}
            )
    except Exception as e:
        add_log(f"Error in agent loop: {str(e)}")
        # Update session status on error
        if st.session_state.current_session_id:
            st.session_state.session_manager.update_session(
                st.session_state.current_session_id,
                {"status": "error", "error": str(e)}
            )
    finally:
        st.session_state.agent_running = False

def start_agent():
    """Start the Computer Use Agent in a separate thread"""
    if st.session_state.agent_running:
        st.warning("Agent is already running!")
        return
    
    # Get API key from environment or input
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and 'openai_api_key' in st.session_state:
        api_key = st.session_state.openai_api_key
    
    if not api_key:
        st.error("OpenAI API key is required")
        return
    
    # Create a new session
    browser_config = {
        "environment": st.session_state.environment,
        "display_width": st.session_state.display_width,
        "display_height": st.session_state.display_height,
        "headless": st.session_state.headless,
        "starting_url": st.session_state.starting_url
    }
    
    session_info = st.session_state.session_manager.create_session(
        task=st.session_state.task,
        environment=st.session_state.environment,
        browser_config=browser_config
    )
    
    session_id = session_info["session_id"]
    task_id = session_info["task_id"]
    
    st.session_state.current_session_id = session_id
    st.session_state.current_task_id = task_id
    add_log(f"Created new session: {session_id} (Task ID: {task_id})")
    
    # Initialize browser if not already running
    if not st.session_state.browser:
        try:
            # Check which browser automation to use
            browser_env = get_browser_environment()
            
            if browser_env == "mock":
                add_log("Using mock browser automation (Playwright not available in this environment)")
                st.session_state.browser = MockBrowserAutomation(
                    headless=st.session_state.headless,
                    width=st.session_state.display_width,
                    height=st.session_state.display_height,
                    starting_url=st.session_state.starting_url
                )
            else:
                add_log("Using real browser automation with Playwright")
                st.session_state.browser = BrowserAutomation(
                    headless=st.session_state.headless,
                    width=st.session_state.display_width,
                    height=st.session_state.display_height,
                    starting_url=st.session_state.starting_url
                )
                
            add_log(f"Browser started and navigated to {st.session_state.starting_url}")
        except Exception as e:
            error_message = f"Failed to start browser: {str(e)}"
            add_log(error_message)
            
            # Try with mock browser as fallback
            try:
                add_log("Trying with mock browser as fallback...")
                st.session_state.browser = MockBrowserAutomation(
                    headless=st.session_state.headless,
                    width=st.session_state.display_width,
                    height=st.session_state.display_height,
                    starting_url=st.session_state.starting_url
                )
                add_log("Mock browser started successfully as fallback")
            except Exception as e2:
                error_message = f"Failed to start browser even with fallback: {str(e)} -> {str(e2)}"
                add_log(error_message)
                st.error(error_message)
                return
    
    # Initialize the Computer Use Agent
    st.session_state.agent = ComputerUseAgent(
        api_key=api_key,
        environment=st.session_state.environment,
        display_width=st.session_state.display_width,
        display_height=st.session_state.display_height
    )
    
    # Define the enhanced agent loop wrapper function
    def enhanced_agent_wrapper():
        try:
            # Ensure all session state variables exist with dict-style access
            if 'session_manager' not in st.session_state:
                st.session_state['session_manager'] = SessionManager()
                
            # Call the enhanced agent loop with safe session state access
            result = enhanced_agent_loop(
                session_manager=st.session_state['session_manager'],
                session_id=st.session_state['current_session_id'],
                task_id=st.session_state['current_task_id'],
                browser=st.session_state['browser'],
                agent=st.session_state['agent'],
                task=st.session_state['task'],
                add_log=add_log,
                stop_signal_getter=lambda: st.session_state.get('stop_agent', False)
            )
            
            # Handle safety checks if needed
            if result and result.get("status") == "safety_check":
                st.session_state['pending_safety_checks'] = result.get("safety_checks")
                st.session_state['pending_safety_response_id'] = result.get("response_id")
                st.session_state['pending_safety_call_id'] = result.get("call_id")
                st.session_state['awaiting_safety_confirmation'] = True
                
        except Exception as e:
            add_log(f"Error in enhanced agent wrapper: {str(e)}")
        finally:
            # Safely set the agent_running flag to False
            st.session_state['agent_running'] = False
    
    # Start the agent loop in a separate thread
    st.session_state.agent_running = True
    st.session_state.agent_thread = threading.Thread(target=enhanced_agent_wrapper)
    st.session_state.agent_thread.daemon = True
    st.session_state.agent_thread.start()

def stop_agent():
    """Stop the Computer Use Agent"""
    if not st.session_state.agent_running:
        st.warning("Agent is not running!")
        return
    
    st.session_state.stop_agent = True
    add_log("Stopping agent...")

def close_browser():
    """Close the browser"""
    if st.session_state.browser:
        st.session_state.browser.close()
        st.session_state.browser = None
        add_log("Browser closed")
        
def create_reasoning_capture():
    """Create a reasoning capture instance for the current session"""
    # Ensure session_manager exists before accessing it
    if 'session_manager' not in st.session_state:
        st.session_state['session_manager'] = SessionManager()
        
    return ReasoningCapture(
        session_manager=st.session_state['session_manager'],
        session_id=st.session_state.get('current_session_id'),
        add_log_func=add_log
    )
        
def confirm_safety_checks():
    """Acknowledge the pending safety checks and continue the agent execution"""
    if not st.session_state.pending_safety_checks:
        return
    
    try:
        # Define the enhanced agent continuation function
        def enhanced_continuation_wrapper():
            try:
                # Ensure all session state variables exist with dict-style access
                if 'session_manager' not in st.session_state:
                    st.session_state['session_manager'] = SessionManager()
                
                # Continue the agent loop with the initial response after safety check
                result = enhanced_agent_loop_with_response(
                    session_manager=st.session_state['session_manager'],
                    session_id=st.session_state['current_session_id'],
                    task_id=st.session_state['current_task_id'],
                    browser=st.session_state['browser'],
                    agent=st.session_state['agent'],
                    initial_response=st.session_state['pending_safety_response_id'],
                    initial_call_id=st.session_state['pending_safety_call_id'],
                    safety_checks=st.session_state['pending_safety_checks'],
                    add_log=add_log,
                    stop_signal_getter=lambda: st.session_state.get('stop_agent', False)
                )
                
                # Handle safety checks if needed
                if result and result.get("status") == "safety_check":
                    st.session_state['pending_safety_checks'] = result.get("safety_checks")
                    st.session_state['pending_safety_response_id'] = result.get("response_id")
                    st.session_state['pending_safety_call_id'] = result.get("call_id")
                    st.session_state['awaiting_safety_confirmation'] = True
                    
            except Exception as e:
                add_log(f"Error in enhanced continuation wrapper: {str(e)}")
            finally:
                st.session_state['agent_running'] = False
        
        add_log("Safety checks acknowledged by user. Continuing task execution.")
        
        # Reset safety check state
        st.session_state.awaiting_safety_confirmation = False
        
        # Continue agent execution
        st.session_state.agent_running = True
        st.session_state.agent_thread = threading.Thread(target=enhanced_continuation_wrapper)
        st.session_state.agent_thread.daemon = True
        st.session_state.agent_thread.start()
    except Exception as e:
        add_log(f"Error acknowledging safety checks: {str(e)}")
        st.error(f"Error acknowledging safety checks: {str(e)}")
        
def reject_safety_checks():
    """Reject the pending safety checks and stop the agent execution"""
    add_log("Safety checks rejected by user. Stopping task execution.")
    
    # Reset safety check state
    st.session_state.awaiting_safety_confirmation = False
    st.session_state.pending_safety_checks = None
    st.session_state.pending_safety_response_id = None
    st.session_state.pending_safety_call_id = None
    
    # Update session status
    if st.session_state.current_session_id:
        st.session_state.session_manager.update_session(
            st.session_state.current_session_id,
            {"status": "stopped", "reason": "safety_check_rejected"}
        )
        
def agent_loop_with_response(initial_response):
    """Agent loop that starts with an initial response"""
    try:
        add_log("Continuing agent execution after safety check confirmation...")
        st.session_state.stop_agent = False
        
        response = initial_response
        add_log(f"Continuing with response (ID: {response.id})")
        
        # Continue loop until stopped or no more actions
        while not st.session_state.stop_agent:
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
                
                # Store safety check details in session state for user confirmation
                st.session_state.pending_safety_checks = safety_checks
                st.session_state.pending_safety_response_id = response.id
                st.session_state.pending_safety_call_id = call_id
                st.session_state.awaiting_safety_confirmation = True
                
                # We'll let the agent loop exit and show confirmation UI to the user
                break
                
            # Execute the action
            try:
                st.session_state.browser.execute_action(action)
                add_log(f"Action executed successfully: {action.type}")
            except Exception as e:
                add_log(f"Error executing action: {str(e)}")
                # If action fails, we still continue with a new screenshot
            
            # Wait a moment for the action to take effect
            time.sleep(1)
            
            # Take a new screenshot
            screenshot = get_screenshot_as_base64(st.session_state.browser)
            st.session_state.screenshot = screenshot
            
            # Update the session with the new screenshot
            if st.session_state.current_session_id:
                st.session_state.session_manager.add_screenshot(
                    st.session_state.current_session_id,
                    screenshot
                )
            
            # Send the screenshot back to the agent
            try:
                response = st.session_state.agent.send_screenshot(
                    response.id,
                    call_id,
                    screenshot
                )
                add_log(f"Sent screenshot to agent (Response ID: {response.id})")
            except Exception as e:
                add_log(f"Error sending screenshot to agent: {str(e)}")
                break
            
        add_log("Agent loop stopped")
        
        # Update session status
        if st.session_state.current_session_id:
            st.session_state.session_manager.update_session(
                st.session_state.current_session_id,
                {"status": "completed"}
            )
    except Exception as e:
        add_log(f"Error in agent loop: {str(e)}")
        # Update session status on error
        if st.session_state.current_session_id:
            st.session_state.session_manager.update_session(
                st.session_state.current_session_id,
                {"status": "error", "error": str(e)}
            )
    finally:
        st.session_state.agent_running = False

# Main UI
st.title("🤖 Computer Use Agent")
st.markdown("""
This application allows you to automate browser tasks using OpenAI's Computer Use Agent API.
The agent will take screenshots of the browser, decide what actions to take, and execute them automatically.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # OpenAI API Key
    if not os.environ.get("OPENAI_API_KEY"):
        api_key = st.text_input("OpenAI API Key", type="password")
        if api_key:
            st.session_state.openai_api_key = api_key
    
    st.session_state.environment = st.selectbox(
        "Environment",
        options=["browser", "mac", "windows", "ubuntu"],
        index=0
    )
    
    st.session_state.display_width = st.number_input(
        "Display Width",
        min_value=800,
        max_value=1920,
        value=1024
    )
    
    st.session_state.display_height = st.number_input(
        "Display Height",
        min_value=600,
        max_value=1080,
        value=768
    )
    
    st.session_state.headless = st.checkbox("Headless Browser", value=True)
    
    st.session_state.starting_url = st.text_input(
        "Starting URL",
        value="https://www.google.com"
    )
    
    # Actions
    st.header("Actions")
    col1, col2 = st.columns(2)
    start_button = col1.button("Start Agent", on_click=start_agent)
    stop_button = col2.button("Stop Agent", on_click=stop_agent)
    
    close_button = st.button("Close Browser", on_click=close_browser)
    
    # Dashboard and API docs links
    st.header("Analytics & Documentation")
    
    def open_dashboard():
        """Function to navigate to the dashboard"""
        # Store current state in session
        st.session_state.view_dashboard = True
        # Set query params to show dashboard
        st.query_params["show_dashboard"] = "true"
    
    def open_api_docs():
        """Function to navigate to the API documentation"""
        # Store current state in session
        st.session_state.view_api_docs = True
        # Set query params to show API docs
        st.query_params["show_api_docs"] = "true"
    
    col1, col2 = st.columns(2)
    if col1.button("📊 View Session Dashboard", use_container_width=True, type="primary"):
        open_dashboard()
        
    if col2.button("🔌 API Documentation", use_container_width=True):
        open_api_docs()
    
    # Session history info
    session_count = len(st.session_state.session_manager.list_sessions())
    st.info(f"You have {session_count} stored sessions. View them in the dashboard.")

# Task input
st.header("Task Description")
st.session_state.task = st.text_area(
    "Describe the task you want the agent to perform",
    height=100,
    placeholder="Example: Search for the latest news about OpenAI on Google"
)

# Main content area - split into two columns
col1, col2 = st.columns([3, 2])

# Left column - Screenshot
with col1:
    st.header("Browser View")
    screenshot_placeholder = st.empty()
    
    # Display the current screenshot if available
    if st.session_state.screenshot:
        try:
            image_data = base64.b64decode(st.session_state.screenshot)
            image = Image.open(io.BytesIO(image_data))
            screenshot_placeholder.image(image, use_column_width=True)
        except Exception as e:
            screenshot_placeholder.error(f"Failed to display screenshot: {str(e)}")
    else:
        screenshot_placeholder.info("No screenshot available yet. Start the agent to see the browser.")

# Right column - Logs
with col2:
    st.header("Agent Logs")
    logs_placeholder = st.empty()
    
    # Display logs in reverse order (newest first)
    logs_text = "\n".join(reversed(st.session_state.logs))
    logs_placeholder.text_area("Logs", value=logs_text, height=400, key="logs_display", label_visibility="collapsed")

# Status indicator
if st.session_state.awaiting_safety_confirmation:
    status_text = "Agent paused - Safety check required"
    status_color = "orange"
else:
    status_text = "Agent is running" if st.session_state.agent_running else "Agent is stopped"
    status_color = "green" if st.session_state.agent_running else "red"
st.markdown(f"<h4 style='color: {status_color};'>Status: {status_text}</h4>", unsafe_allow_html=True)

# Safety check confirmation UI
if st.session_state.awaiting_safety_confirmation and st.session_state.pending_safety_checks:
    st.warning("⚠️ Safety Check Required")
    
    # Display safety check details
    st.subheader("The agent encountered a safety check")
    st.markdown("OpenAI's Computer Use Agent has detected a potential safety issue that requires your approval to continue.")
    
    for safety_check in st.session_state.pending_safety_checks:
        st.markdown(f"**Safety Check Type:** {safety_check.code}")
        st.markdown(f"**Message:** {safety_check.message}")
    
    st.markdown("""
    ### What does this mean?
    
    - **Malicious Instructions:** The agent detected instructions that may cause unauthorized actions
    - **Irrelevant Domain:** The current website may not be relevant to your task
    - **Sensitive Domain:** You're on a website that may contain sensitive information
    
    Review the current screenshot carefully to verify the agent's actions.
    """)
    
    # Confirmation buttons
    col1, col2 = st.columns(2)
    with col1:
        st.button("✅ Approve and Continue", on_click=confirm_safety_checks, type="primary")
    with col2:
        st.button("❌ Reject and Stop", on_click=reject_safety_checks, type="secondary")

# Display session information
if st.session_state.current_session_id:
    st.header("Session Information")
    
    # Display session details
    col1, col2 = st.columns([2, 1])
    
    with col1:
        session_link = st.session_state.session_manager.get_session_link(
            st.session_state.current_session_id,
            base_url="http://0.0.0.0:5000"
        )
        st.markdown(f"**Session ID:** {st.session_state.current_session_id}")
        st.markdown(f"**Shareable Link:** [Open Session]({session_link})")
        st.text_input(
            "Copy Session Link",
            value=session_link,
            key="session_link_input",
            disabled=True
        )
    
    with col2:
        # Add the replay button
        st.markdown("#### Session Actions")
        session_replay.add_replay_button_to_session(st.session_state.current_session_id, st, "main_view")
        
        # Add quick metrics about the session
        session_data = st.session_state.session_manager.get_session(st.session_state.current_session_id)
        if session_data:
            screenshots_count = len(session_data.get('screenshots', []))
            actions_count = len(session_data.get('actions', []))
            st.markdown(f"**Screenshots:** {screenshots_count}")
            st.markdown(f"**Actions:** {actions_count}")

# Display previous sessions
st.header("Previous Sessions")
sessions = st.session_state.session_manager.list_sessions(limit=5)
if sessions:    
    for session in sessions:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**{session['task'][:50] + '...' if len(session['task']) > 50 else session['task']}**")
            st.caption(f"Created: {session['created_at'][:16]} | Environment: {session['environment']} | Status: {session['status']}")
            
            # Display metrics about screenshots and actions
            screenshots_count = len(session.get('screenshots', []))
            actions_count = len(session.get('actions', []))
            st.caption(f"📸 Screenshots: {screenshots_count} | 🔄 Actions: {actions_count}")
            
        with col2:
            session_link = st.session_state.session_manager.get_session_link(
                session['id'],
                base_url="http://0.0.0.0:5000"
            )
            
            def open_session(session_id):
                st.query_params.update({"session": session_id})
                
            st.button(
                "View Session",
                key=f"view_session_{session['id']}",
                on_click=lambda s=session['id']: open_session(s)
            )
            
        with col3:
            # Add replay button for each session
            session_replay.add_replay_button_to_session(
                session['id'],
                st,
                f"list_view_{sessions.index(session)}"
            )
            
        st.divider()
else:
    st.info("No previous sessions found. Start a new session to see it here.")

# Auto-refresh the UI every 2 seconds while the agent is running
if st.session_state.agent_running:
    st.rerun()
