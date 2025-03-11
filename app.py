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

# Add clean, minimal styling that works reliably
st.markdown("""
<style>
    /* Main styling */
    .block-container {
        padding: 2rem 1rem;
        max-width: 928px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer {
        display: none !important;
    }
    
    /* Input styling */
    .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        font-size: 15px;
        padding: 12px;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }
    
    /* Primary button styling */
    [data-testid="baseButton-primary"] {
        background-color: #10a37f !important;
        color: white !important;
    }
    
    /* Title styling */
    .main-title {
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 8px;
        text-align: center;
    }
    
    /* Subtitle styling */
    .subtitle {
        font-size: 16px;
        color: #666;
        margin-bottom: 30px;
        text-align: center;
    }
    
    /* Recent items styling */
    .recent-item {
        padding: 12px;
        border-radius: 6px;
        background-color: #f5f5f5;
        margin-bottom: 8px;
        cursor: pointer;
        border-left: 3px solid #10a37f;
    }
    
    .recent-item:hover {
        background-color: #e9e9e9;
    }
    
    /* Browser container */
    .browser-container {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e0e0e0;
        margin: 20px 0;
    }
    
    /* Center column */
    .center-col {
        max-width: 800px;
        margin: 0 auto;
        padding-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Check and install dependencies
check_install_dependencies()

# Initialize session state
if "session_manager" not in st.session_state:
    st.session_state.session_manager = SessionManager()

if "browser" not in st.session_state:
    st.session_state.browser = None

if "logs" not in st.session_state:
    st.session_state.logs = []

if "agent_running" not in st.session_state:
    st.session_state.agent_running = False

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "task" not in st.session_state:
    st.session_state.task = ""

if "screenshot" not in st.session_state:
    st.session_state.screenshot = None

if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = os.environ.get("OPENAI_API_KEY", "")

if "environment" not in st.session_state:
    st.session_state.environment = "browser"

if "display_width" not in st.session_state:
    st.session_state.display_width = 1024

if "display_height" not in st.session_state:
    st.session_state.display_height = 768

if "headless" not in st.session_state:
    st.session_state.headless = True

if "starting_url" not in st.session_state:
    st.session_state.starting_url = "https://www.google.com"

if "awaiting_safety_confirmation" not in st.session_state:
    st.session_state.awaiting_safety_confirmation = False

if "pending_safety_checks" not in st.session_state:
    st.session_state.pending_safety_checks = []

if "view_dashboard" not in st.session_state:
    st.session_state.view_dashboard = False

if "view_api_docs" not in st.session_state:
    st.session_state.view_api_docs = False

if "show_support" not in st.session_state:
    st.session_state.show_support = False

# Check for routing query parameters
query_params = st.query_params
if query_params.get("session"):
    st.session_state.current_session_id = query_params.get("session")
    
    # Get the session data and populate session state
    session_data = st.session_state.session_manager.get_session(st.session_state.current_session_id)
    if session_data:
        st.session_state.task = session_data.get("task", "")
        st.session_state.logs = session_data.get("logs", [])
        st.session_state.screenshot = session_data.get("current_screenshot")
        st.session_state.agent_running = session_data.get("status") == "running"

if query_params.get("show_dashboard") == "true":
    st.session_state.view_dashboard = True

if query_params.get("show_api_docs") == "true":
    st.session_state.view_api_docs = True

# Log function
def add_log(message):
    """Add a message to the logs and update session data if available"""
    st.session_state.logs.append(f"{time.strftime('%H:%M:%S')} - {message}")
    
    # If we're in a session, update the session data too
    if st.session_state.current_session_id:
        st.session_state.session_manager.add_log(st.session_state.current_session_id, message)

# Agent loop function
def agent_loop():
    """Main loop for the Computer Use Agent"""
    try:
        add_log("Starting agent loop...")
        add_log(f"Task: {st.session_state.task}")
        add_log(f"Environment: {st.session_state.environment}")
        add_log(f"Starting URL: {st.session_state.starting_url}")
        
        # Create the agent
        agent = ComputerUseAgent(
            api_key=st.session_state.openai_api_key,
            environment=st.session_state.environment,
            display_width=st.session_state.display_width,
            display_height=st.session_state.display_height
        )
        
        # Browser environment
        browser_env = get_browser_environment()
        add_log(f"Browser environment: {browser_env}")
        
        # Create browser automation
        if browser_env == "real":
            add_log("Using real browser automation")
            browser = BrowserAutomation(
                headless=st.session_state.headless,
                width=st.session_state.display_width,
                height=st.session_state.display_height,
                starting_url=st.session_state.starting_url
            )
        else:
            add_log("Using mock browser automation")
            browser = MockBrowserAutomation(
                headless=st.session_state.headless,
                width=st.session_state.display_width,
                height=st.session_state.display_height,
                starting_url=st.session_state.starting_url
            )
            
        st.session_state.browser = browser
        
        # Create or get a session
        if not st.session_state.current_session_id:
            session_info = st.session_state.session_manager.create_session(
                task=st.session_state.task,
                environment=st.session_state.environment,
                browser_config={
                    "headless": st.session_state.headless,
                    "width": st.session_state.display_width,
                    "height": st.session_state.display_height,
                    "starting_url": st.session_state.starting_url
                }
            )
            st.session_state.current_session_id = session_info["session_id"]
            
        # Register the thread with the session manager
        st.session_state.session_manager.register_thread(
            st.session_state.current_session_id,
            threading.current_thread(),
            None
        )
            
        # Get initial screenshot
        screenshot_base64 = get_screenshot_as_base64(browser)
        st.session_state.screenshot = screenshot_base64
        
        # Update the session with the initial screenshot
        st.session_state.session_manager.add_screenshot(
            st.session_state.current_session_id,
            screenshot_base64
        )
        
        # Initial agent request
        add_log("Sending initial request to Computer Use agent...")
        response = agent.initial_request(st.session_state.task, screenshot_base64)
        
        # Save the reasoning data to the session
        for item in response.choices[0].message.tool_calls:
            if item.function.name == "computer_use":
                reasoning_data = item.function.arguments.get("reasoning", [])
                st.session_state.session_manager.add_reasoning_data(
                    st.session_state.current_session_id,
                    {"id": item.id, "content": reasoning_data}
                )
        
        # Main loop - process actions until done or stopped
        response_id = response.id
        while st.session_state.agent_running:
            # Check if we have any tool calls in the response
            if not response.choices[0].message.tool_calls:
                add_log("No tool calls in response - agent is done")
                break
                
            # Find the computer_use tool call
            computer_use_call = None
            for tool_call in response.choices[0].message.tool_calls:
                if tool_call.function.name == "computer_use":
                    computer_use_call = tool_call
                    break
                    
            if not computer_use_call:
                add_log("No computer_use tool call found - agent is done")
                break
                
            # Parse the actions from the tool call
            call_args = computer_use_call.function.arguments
            actions = call_args.get("actions", [])
            
            # Check if we have any safety checks
            safety_checks = call_args.get("safety_checks", [])
            if safety_checks:
                add_log(f"Safety checks detected: {len(safety_checks)}")
                
                # Save safety checks to session
                for check in safety_checks:
                    st.session_state.session_manager.add_safety_check(
                        st.session_state.current_session_id,
                        check
                    )
                    
                # Set the awaiting confirmation flag
                st.session_state.awaiting_safety_confirmation = True
                st.session_state.pending_safety_checks = safety_checks
                
                # Wait for confirmation
                while st.session_state.awaiting_safety_confirmation and st.session_state.agent_running:
                    time.sleep(0.5)
                    
                # If the agent is no longer running, break out of the loop
                if not st.session_state.agent_running:
                    add_log("Agent stopped during safety check")
                    break
                    
                # If the safety checks were confirmed, continue with acknowledgement
                add_log("Safety checks confirmed - continuing")
                response = agent.acknowledge_safety_checks(
                    response_id,
                    computer_use_call.id,
                    safety_checks
                )
                response_id = response.id
                continue
                
            # Process actions
            for i, action in enumerate(actions):
                if not st.session_state.agent_running:
                    add_log("Agent stopped during action execution")
                    break
                    
                action_type = action.get("type")
                add_log(f"Executing action {i+1}/{len(actions)}: {action_type}")
                
                # Add action to session history
                st.session_state.session_manager.add_action(
                    st.session_state.current_session_id,
                    action
                )
                
                # Execute the action
                try:
                    browser.execute_action(action)
                    add_log(f"Action executed successfully")
                except Exception as e:
                    add_log(f"Error executing action: {str(e)}")
                    
                # If this is a navigate action, wait a bit longer
                if action_type == "navigate":
                    time.sleep(1)
                    
            # Get updated screenshot
            screenshot_base64 = get_screenshot_as_base64(browser)
            st.session_state.screenshot = screenshot_base64
            
            # Update the session with the new screenshot
            st.session_state.session_manager.add_screenshot(
                st.session_state.current_session_id,
                screenshot_base64
            )
            
            # Send the screenshot back to the agent
            add_log("Sending updated screenshot to agent...")
            response = agent.send_screenshot(
                response_id,
                computer_use_call.id,
                screenshot_base64
            )
            response_id = response.id
            
            # Save the reasoning data to the session
            for item in response.choices[0].message.tool_calls:
                if item.function.name == "computer_use":
                    reasoning_data = item.function.arguments.get("reasoning", [])
                    st.session_state.session_manager.add_reasoning_data(
                        st.session_state.current_session_id,
                        {"id": item.id, "content": reasoning_data}
                    )
                    
            # Check if the agent is done
            if not response.choices[0].message.tool_calls:
                add_log("Agent has completed the task")
                break
                
        add_log("Agent loop finished")
        
        # Complete the session
        if st.session_state.current_session_id:
            st.session_state.session_manager.complete_session(
                st.session_state.current_session_id,
                success=True
            )
            
        # Update UI
        time.sleep(1)
    except Exception as e:
        add_log(f"Error in agent loop: {str(e)}")
        if st.session_state.current_session_id:
            st.session_state.session_manager.complete_session(
                st.session_state.current_session_id,
                success=False,
                error=str(e)
            )
    finally:
        st.session_state.agent_running = False

def start_agent():
    """Start the Computer Use Agent in a separate thread"""
    if st.session_state.agent_running:
        add_log("Agent is already running")
        return
        
    # Check if we have an API key
    if not st.session_state.openai_api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            add_log("Missing OpenAI API key")
            return
        st.session_state.openai_api_key = api_key
            
    # Check if we have a task
    if not st.session_state.task:
        add_log("No task specified")
        return
        
    # Set agent as running
    st.session_state.agent_running = True
    
    # Start the agent in a separate thread
    thread = threading.Thread(target=agent_loop)
    thread.daemon = True
    thread.start()
    
    # Add a log message
    add_log("Agent started in background thread")

def stop_agent():
    """Stop the Computer Use Agent"""
    if not st.session_state.agent_running:
        add_log("Agent is not running")
        return
        
    add_log("Stopping agent...")
    st.session_state.agent_running = False
    
    # Complete the session
    if st.session_state.current_session_id:
        st.session_state.session_manager.complete_session(
            st.session_state.current_session_id,
            success=False,
            error="Stopped by user"
        )
        
    # Close the browser
    close_browser()

def close_browser():
    """Close the browser"""
    if st.session_state.browser:
        add_log("Closing browser...")
        try:
            st.session_state.browser.close()
        except Exception as e:
            add_log(f"Error closing browser: {str(e)}")
        st.session_state.browser = None

def confirm_safety_checks():
    """Acknowledge the pending safety checks and continue the agent execution"""
    st.session_state.awaiting_safety_confirmation = False
    add_log("Safety checks acknowledged")

def reject_safety_checks():
    """Reject the pending safety checks and stop the agent execution"""
    st.session_state.awaiting_safety_confirmation = False
    st.session_state.agent_running = False
    add_log("Safety checks rejected - agent stopped")
    
    # Complete the session
    if st.session_state.current_session_id:
        st.session_state.session_manager.complete_session(
            st.session_state.current_session_id,
            success=False,
            error="Safety checks rejected by user"
        )

def agent_loop_with_response(initial_response):
    """Agent loop that starts with an initial response"""
    st.session_state.agent_running = True
    add_log("Continuing agent loop with response")
    
    # Start a new thread
    thread = threading.Thread(target=lambda: agent_loop())
    thread.daemon = True
    thread.start()

# Define navigation functions
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
    logs_placeholder.text_area("Logs", value=logs_text, height=200, key="logs_display", label_visibility="collapsed")

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

# Auto-refresh the UI every 2 seconds while the agent is running
if st.session_state.agent_running:
    st.rerun()