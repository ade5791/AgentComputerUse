import streamlit as st
import base64
import threading
import time
import io
import uuid
from PIL import Image
import os

from browser_automation import BrowserAutomation
from mock_browser_automation import MockBrowserAutomation
from computer_use_agent import ComputerUseAgent
from utils import get_screenshot_as_base64
from session_manager import SessionManager
from setup_app import check_install_dependencies, get_browser_environment

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
# Safety check related state variables
if 'pending_safety_checks' not in st.session_state:
    st.session_state.pending_safety_checks = None
if 'pending_safety_response_id' not in st.session_state:
    st.session_state.pending_safety_response_id = None
if 'pending_safety_call_id' not in st.session_state:
    st.session_state.pending_safety_call_id = None
if 'awaiting_safety_confirmation' not in st.session_state:
    st.session_state.awaiting_safety_confirmation = False

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
        
def confirm_safety_checks():
    """Acknowledge the pending safety checks and continue the agent execution"""
    if not st.session_state.pending_safety_checks:
        return
    
    try:
        # Acknowledge the safety checks
        response = st.session_state.agent.acknowledge_safety_checks(
            st.session_state.pending_safety_response_id,
            st.session_state.pending_safety_call_id,
            st.session_state.pending_safety_checks
        )
        
        add_log("Safety checks acknowledged by user. Continuing task execution.")
        
        # Reset safety check state
        st.session_state.awaiting_safety_confirmation = False
        st.session_state.pending_safety_checks = None
        st.session_state.pending_safety_response_id = None
        st.session_state.pending_safety_call_id = None
        
        # Continue agent execution
        st.session_state.agent_running = True
        st.session_state.agent_thread = threading.Thread(target=lambda: agent_loop_with_response(response))
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

# Add CSS to match the OpenAI Computer Use interface style
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: white;
        padding: 0 !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f7f7f8;
        border-right: 1px solid #e5e5e5;
    }
    
    /* Header styling */
    .stApp header {
        background-color: white;
        border-bottom: 1px solid #e5e5e5;
    }
    
    /* Input field styling */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        background-color: #ffffff;
        padding: 10px;
        font-size: 16px;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 14px;
        border: 1px solid #e5e5e5;
        background-color: #f7f7f8;
    }
    
    /* Primary button styling */
    .stButton > button[data-baseweb="button"]:first-child {
        background-color: #10a37f;
        color: white;
        border: none;
    }
    
    /* Recent prompts styling */
    .recent-item {
        padding: 8px 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        background-color: #f7f7f8;
        cursor: pointer;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .recent-item:hover {
        background-color: #e5e5e5;
    }
    
    /* Task response area */
    .task-response {
        border-radius: 8px;
        border: 1px solid #e5e5e5;
        padding: 15px;
        margin-top: 15px;
        background-color: #f7f7f8;
    }
    
    /* Center content block */
    .center-col {
        max-width: 800px;
        margin: 0 auto;
        padding-top: 60px;
    }
    
    /* Main title */
    .main-title {
        font-size: 32px;
        font-weight: 600;
        text-align: center;
        margin-bottom: 10px;
    }
    
    /* Subtitle */
    .subtitle {
        font-size: 16px;
        text-align: center;
        color: #6e6e80;
        margin-bottom: 30px;
    }
    
    /* Recent prompt label */
    .recent-label {
        font-size: 14px;
        font-weight: 600;
        color: #6e6e80;
        margin-bottom: 10px;
    }
    
    /* Browser view container */
    .browser-container {
        border: 1px solid #e5e5e5;
        border-radius: 8px;
        overflow: hidden;
        margin-top: 20px;
    }
    
    /* Bottom task bar */
    .task-bar {
        background-color: #f7f7f8;
        border-top: 1px solid #e5e5e5;
        padding: 10px 15px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    /* Example buttons */
    .example-button {
        display: inline-block;
        padding: 8px 12px;
        margin-right: 10px;
        background-color: #f7f7f8;
        border: 1px solid #e5e5e5;
        border-radius: 6px;
        font-size: 14px;
        cursor: pointer;
    }
    
    .example-button:hover {
        background-color: #e5e5e5;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with recent tasks and history
with st.sidebar:
    # Logo or title
    st.markdown("# Recents")
    
    # Get recent sessions
    recent_sessions = st.session_state.session_manager.list_sessions(limit=10)
    
    # Show recent sessions as clickable items
    for session in recent_sessions:
        task_text = session.get('task', 'Unknown task')
        if len(task_text) > 50:
            task_text = task_text[:47] + "..."
        
        st.markdown(f"""
        <div class="recent-item" onclick="window.location.href='?session={session['id']}'">
            {task_text}
        </div>
        """, unsafe_allow_html=True)
    
    if not recent_sessions:
        st.markdown("No recent sessions")
    
    st.markdown(f"<div style='font-size: 12px; color: #6e6e80; margin-top: 10px;'>View all {len(st.session_state.session_manager.list_sessions())} sessions</div>", unsafe_allow_html=True)
    
    # Add History, API, and Support links at bottom
    st.markdown("<div style='position: absolute; bottom: 20px; left: 20px;'>", unsafe_allow_html=True)
    
    if st.button("📊 History", key="history_btn"):
        open_dashboard()
    
    if st.button("🔌 API", key="api_btn"):
        open_api_docs()
    
    if st.button("📞 Support", key="support_btn"):
        st.session_state.show_support = True
    
    st.markdown("</div>", unsafe_allow_html=True)

# Main content
main_col1, main_col2, main_col3 = st.columns([1, 3, 1])

with main_col2:
    # Store functions for navigation
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

    # Check if we are in a session or showing the main input screen
    if st.session_state.current_session_id and st.session_state.screenshot:
        # We're in a session - show the browser view and agent status
        
        # Get session data
        session_data = st.session_state.session_manager.get_session(st.session_state.current_session_id)
        task_text = session_data.get('task', 'Unknown task')
        
        # Show the task description
        st.markdown(f"<div style='margin-bottom: 20px;'><strong>Task:</strong> {task_text}</div>", unsafe_allow_html=True)
        
        # Browser container
        st.markdown("<div class='browser-container'>", unsafe_allow_html=True)
        
        # Display the current screenshot
        try:
            image_data = base64.b64decode(st.session_state.screenshot)
            image = Image.open(io.BytesIO(image_data))
            st.image(image, use_column_width=True)
        except Exception as e:
            st.error(f"Failed to display screenshot: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Action buttons below the browser view
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⏹️ Stop Agent", use_container_width=True, on_click=stop_agent):
                pass
        with col2:
            if st.button("🏠 New Task", use_container_width=True):
                # Reset session state and refresh page
                st.session_state.current_session_id = None
                st.session_state.screenshot = None
                st.session_state.browser = None
                st.experimental_rerun()
        
        # Log container
        with st.expander("Show Agent Logs", expanded=False):
            log_text = "\n".join(st.session_state.logs)
            st.text_area("Logs", value=log_text, height=300, disabled=True)
        
        # Safety check confirmation UI if needed
        if st.session_state.awaiting_safety_confirmation:
            st.warning("OpenAI's Computer Use Agent has detected a potential safety issue that requires your approval to continue.")
            
            # Display each safety check
            for safety_check in st.session_state.pending_safety_checks:
                st.markdown(f"**Safety Check Type:** {safety_check.code}")
                st.markdown(f"**Message:** {safety_check.message}")
                
            st.markdown("""
            Please review the safety concerns above and decide whether to allow the agent to proceed.
            Confirming will allow the agent to continue with the requested action. Rejecting will stop the agent.
            """)
            
            # Confirmation buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm & Continue", use_container_width=True, on_click=confirm_safety_checks):
                    pass
            with col2:
                if st.button("❌ Reject & Stop", use_container_width=True, on_click=reject_safety_checks):
                    pass
    else:
        # Show the main input screen
        st.markdown("<div class='center-col'>", unsafe_allow_html=True)
        
        st.markdown("<h1 class='main-title'>What do you want done?</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Prompt, run, and let agent do the rest.</p>", unsafe_allow_html=True)
        
        # Task input field
        st.session_state.task = st.text_area(
            "Enter a task for the agent to perform",
            height=120,
            label_visibility="collapsed",
            placeholder="Example: Search for the latest news about OpenAI on Google"
        )
        
        # Add a "Send" button to start agent
        if st.button("Send", key="send_button", type="primary", use_container_width=False):
            start_agent()
        
        # Examples section
        st.markdown("<div style='margin-top: 20px; text-align: center;'>", unsafe_allow_html=True)
        
        # Example tasks
        example_tasks = [
            "Extract SheetJS",
            "Combine Wikipedia pages",
            "Message to founders",
            "DE Obama website"
        ]
        
        for task in example_tasks:
            if st.button(task, key=f"example_{task}", use_container_width=False):
                st.session_state.task = task
                start_agent()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Advanced configuration (hidden by default)
        with st.expander("Advanced Configuration", expanded=False):
            # Configuration fields
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
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.display_width = st.number_input(
                    "Display Width",
                    min_value=800,
                    max_value=1920,
                    value=1024
                )
            
            with col2:
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
        
        st.markdown("</div>", unsafe_allow_html=True)
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
