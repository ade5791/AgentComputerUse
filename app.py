import streamlit as st
import base64
import threading
import time
import io
import uuid
from PIL import Image
import os

from browser_automation import BrowserAutomation
from computer_use_agent import ComputerUseAgent
from utils import get_screenshot_as_base64
from session_manager import SessionManager

# Set page configuration
st.set_page_config(
    page_title="Computer Use Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables if they don't exist
if 'agent_running' not in st.session_state:
    st.session_state.agent_running = False
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'browser' not in st.session_state:
    st.session_state.browser = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'screenshot' not in st.session_state:
    st.session_state.screenshot = None
if 'stop_agent' not in st.session_state:
    st.session_state.stop_agent = False
if 'agent_thread' not in st.session_state:
    st.session_state.agent_thread = None
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None

# Check for session ID in URL query parameters
query_params = st.query_params
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
    st.session_state.logs.append(log_msg)
    
    # If we have an active session, update the session logs
    if st.session_state.current_session_id:
        st.session_state.session_manager.add_log(
            st.session_state.current_session_id, 
            log_msg
        )
    
def agent_loop():
    """Main loop for the Computer Use Agent"""
    try:
        add_log("Starting Computer Use Agent...")
        st.session_state.stop_agent = False
        
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
                add_log(f"Safety check required: {[sc.code for sc in safety_checks]}")
                
                # Here we auto-acknowledge all safety checks for simplicity
                # In a production system, you might want to ask the user for confirmation
                response = st.session_state.agent.acknowledge_safety_checks(
                    response.id, 
                    call_id,
                    safety_checks
                )
                continue
                
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
    
    session_id = st.session_state.session_manager.create_session(
        task=st.session_state.task,
        environment=st.session_state.environment,
        browser_config=browser_config
    )
    
    st.session_state.current_session_id = session_id
    add_log(f"Created new session: {session_id}")
    
    # Initialize browser if not already running
    if not st.session_state.browser:
        try:
            st.session_state.browser = BrowserAutomation(
                headless=st.session_state.headless,
                width=st.session_state.display_width,
                height=st.session_state.display_height,
                starting_url=st.session_state.starting_url
            )
            add_log(f"Browser started and navigated to {st.session_state.starting_url}")
        except Exception as e:
            st.error(f"Failed to start browser: {str(e)}")
            return
    
    # Initialize the Computer Use Agent
    st.session_state.agent = ComputerUseAgent(
        api_key=api_key,
        environment=st.session_state.environment,
        display_width=st.session_state.display_width,
        display_height=st.session_state.display_height
    )
    
    # Start the agent loop in a separate thread
    st.session_state.agent_running = True
    st.session_state.agent_thread = threading.Thread(target=agent_loop)
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
status_text = "Agent is running" if st.session_state.agent_running else "Agent is stopped"
status_color = "green" if st.session_state.agent_running else "red"
st.markdown(f"<h4 style='color: {status_color};'>Status: {status_text}</h4>", unsafe_allow_html=True)

# Display session information
if st.session_state.current_session_id:
    st.header("Session Information")
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

# Display previous sessions
st.header("Previous Sessions")
sessions = st.session_state.session_manager.list_sessions(limit=5)
if sessions:
    for session in sessions:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{session['task'][:50] + '...' if len(session['task']) > 50 else session['task']}**")
            st.caption(f"Created: {session['created_at'][:16]} | Environment: {session['environment']} | Status: {session['status']}")
        with col2:
            session_link = st.session_state.session_manager.get_session_link(
                session['id'],
                base_url="http://0.0.0.0:5000"
            )
            st.button(
                "View Session",
                key=f"view_session_{session['id']}",
                on_click=lambda s=session_link: st.query_params.update({"session": s})
            )
        st.divider()
else:
    st.info("No previous sessions found. Start a new session to see it here.")

# Auto-refresh the UI every 2 seconds while the agent is running
if st.session_state.agent_running:
    st.rerun()
