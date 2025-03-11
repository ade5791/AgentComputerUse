"""
Session Replay Component for Computer Use Agent

This module implements a feature that allows users to replay recorded sessions
with animated display of actions, screenshots, and decision points.
"""

import streamlit as st
import time
import base64
from PIL import Image
import io
import json
from datetime import datetime
import pandas as pd

def load_session_replay(session_id, session_manager):
    """
    Load the session replay UI for a specific session.
    
    Args:
        session_id (str): The ID of the session to replay
        session_manager: Instance of the SessionManager class
    """
    # Get session data
    session_data = session_manager.get_session(session_id)
    if not session_data:
        st.error(f"Session with ID {session_id} not found")
        return
    
    st.title("🎬 Session Replay")
    st.markdown(f"**Task:** {session_data.get('task', 'No task specified')}")
    
    # Display session metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Environment", session_data.get('environment', 'unknown'))
    with col2:
        status = session_data.get('status', 'unknown')
        st.metric("Status", status)
    with col3:
        created_at = session_data.get('created_at', 'unknown')
        if isinstance(created_at, str) and len(created_at) > 16:
            created_at = created_at[:16]  # Truncate to make it fit better
        st.metric("Created", created_at)
    
    # Prepare data for replay
    screenshots = session_data.get('screenshots', [])
    actions_history = session_data.get('actions_history', [])
    reasoning_data = session_data.get('reasoning_data', [])
    
    # Process actions from actions_history
    actions = []
    for action_record in actions_history:
        if isinstance(action_record, dict) and 'action' in action_record:
            action_data = action_record['action']
            timestamp = action_record.get('timestamp', '')
            
            # Add timestamp to action for proper sequencing
            if isinstance(action_data, dict):
                action_data['timestamp'] = timestamp
                actions.append(action_data)
    
    if not screenshots:
        st.warning("No screenshots available for replay")
        return
    
    # Create placeholders for replay content
    screenshot_placeholder = st.empty()
    action_placeholder = st.empty()
    reasoning_placeholder = st.empty()
    
    # Replay controls
    st.subheader("Replay Controls")
    
    col1, col2, col3 = st.columns(3)
    
    # Set default replay speed (seconds per step)
    if 'replay_speed' not in st.session_state:
        st.session_state.replay_speed = 1.0
    
    # Store replay state
    if 'replay_active' not in st.session_state:
        st.session_state.replay_active = False
    if 'replay_frame' not in st.session_state:
        st.session_state.replay_frame = 0
    
    # Replay speed control
    st.session_state.replay_speed = col1.slider(
        "Replay Speed", 
        min_value=0.1, 
        max_value=3.0, 
        value=st.session_state.replay_speed,
        step=0.1,
        help="Adjust the replay speed (lower is slower)"
    )
    
    # Function to start the replay
    def start_replay():
        st.session_state.replay_active = True
        st.session_state.replay_frame = 0
    
    # Function to stop the replay
    def stop_replay():
        st.session_state.replay_active = False
    
    # Function to step forward in the replay
    def step_forward():
        if st.session_state.replay_frame < len(screenshots) - 1:
            st.session_state.replay_frame += 1
            update_display(st.session_state.replay_frame)
    
    # Function to step backward in the replay
    def step_backward():
        if st.session_state.replay_frame > 0:
            st.session_state.replay_frame -= 1
            update_display(st.session_state.replay_frame)
    
    # Control buttons
    col1, col2, col3, col4 = st.columns(4)
    
    if st.session_state.replay_active:
        col1.button("⏹️ Stop", on_click=stop_replay, use_container_width=True)
    else:
        col1.button("▶️ Play", on_click=start_replay, use_container_width=True, type="primary")
    
    col2.button("⏮️ Previous", on_click=step_backward, use_container_width=True)
    col3.button("⏭️ Next", on_click=step_forward, use_container_width=True)
    
    # Jump to frame control
    st.session_state.replay_frame = col4.number_input(
        "Frame", 
        min_value=0, 
        max_value=len(screenshots) - 1, 
        value=st.session_state.replay_frame,
        step=1
    )
    
    # Utility function to parse timestamp to datetime
    def parse_timestamp(ts):
        """Convert string timestamp to datetime object"""
        if not ts:
            return None
            
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return None
        return ts
    
    # Function to find the action closest to a screenshot
    def find_action_for_screenshot(screenshot_index):
        if not actions or screenshot_index >= len(screenshots):
            return None
            
        screenshot = screenshots[screenshot_index]
        screenshot_timestamp = None
        
        # Extract timestamp from screenshot data
        if isinstance(screenshot, dict):
            if 'timestamp' in screenshot:
                screenshot_timestamp = parse_timestamp(screenshot['timestamp'])
            elif 'created_at' in screenshot:
                screenshot_timestamp = parse_timestamp(screenshot['created_at'])
                
        if screenshot_timestamp is None:
            return None
        
        # Find the action that happened just before or at the same time as the screenshot
        closest_action = None
        min_diff = float('inf')
        
        for action in actions:
            if not isinstance(action, dict):
                continue
                
            action_timestamp = parse_timestamp(action.get('timestamp', None))
            if action_timestamp is None:
                continue
            
            # Calculate time difference
            try:
                if isinstance(screenshot_timestamp, datetime) and isinstance(action_timestamp, datetime):
                    diff = abs((screenshot_timestamp - action_timestamp).total_seconds())
                    
                    # Action should happen before or very close to the screenshot
                    if diff < min_diff:
                        min_diff = diff
                        closest_action = action
            except (TypeError, AttributeError):
                continue
                
        return closest_action
    
    # Function to find reasoning data for a screenshot
    def find_reasoning_for_screenshot(screenshot_index):
        if not reasoning_data or screenshot_index >= len(screenshots):
            return None
            
        screenshot = screenshots[screenshot_index]
        screenshot_timestamp = None
        
        # Extract timestamp from screenshot data
        if isinstance(screenshot, dict):
            if 'timestamp' in screenshot:
                screenshot_timestamp = parse_timestamp(screenshot['timestamp'])
            elif 'created_at' in screenshot:
                screenshot_timestamp = parse_timestamp(screenshot['created_at'])
                
        if screenshot_timestamp is None:
            return None
        
        # Find reasoning data that happened close to the screenshot timestamp
        closest_reasoning = None
        min_diff = float('inf')
        
        for reasoning in reasoning_data:
            if not isinstance(reasoning, dict):
                continue
                
            reasoning_timestamp = parse_timestamp(reasoning.get('timestamp', None))
            if reasoning_timestamp is None:
                continue
            
            # Calculate time difference
            try:
                if isinstance(screenshot_timestamp, datetime) and isinstance(reasoning_timestamp, datetime):
                    diff = abs((screenshot_timestamp - reasoning_timestamp).total_seconds())
                    
                    # Find the closest reasoning data in time
                    if diff < min_diff:
                        min_diff = diff
                        closest_reasoning = reasoning
            except (TypeError, AttributeError):
                continue
                
        return closest_reasoning
    
    # Function to update the display based on the current frame
    def update_display(frame_index):
        # Display the screenshot
        if frame_index < len(screenshots):
            try:
                screenshot_data = screenshots[frame_index].get('data', '')
                image_data = base64.b64decode(screenshot_data)
                image = Image.open(io.BytesIO(image_data))
                screenshot_placeholder.image(image, use_column_width=True)
            except Exception as e:
                screenshot_placeholder.error(f"Failed to display screenshot: {str(e)}")
        
        # Find and display the corresponding action
        action = find_action_for_screenshot(frame_index)
        action_placeholder.markdown("### Current Action")
        if action:
            action_type = action.get('type', 'unknown')
            details = action.get('details', {})
            
            # Format action details nicely
            action_placeholder.markdown(f"**Type:** {action_type}")
            if action_type == "click" and "position" in details:
                position = details.get("position", {})
                x = position.get("x", 0)
                y = position.get("y", 0)
                action_placeholder.markdown(f"**Position:** x={x}, y={y}")
            elif action_type == "type" and "text" in details:
                text = details.get("text", "")
                action_placeholder.markdown(f"**Text:** {text}")
            elif action_type == "navigate" and "url" in details:
                url = details.get("url", "")
                action_placeholder.markdown(f"**URL:** {url}")
        else:
            action_placeholder.info("No action associated with this screenshot")
        
        # Find and display the reasoning data
        reasoning = find_reasoning_for_screenshot(frame_index)
        reasoning_placeholder.markdown("### Agent Reasoning")
        if reasoning:
            agent_reasoning = reasoning.get('agent_reasoning', 'No reasoning available')
            action_performed = reasoning.get('action_performed', 'None')
            reasoning_placeholder.markdown(f"**For action:** {action_performed}")
            reasoning_placeholder.text_area("Reasoning", agent_reasoning, height=150, label_visibility="collapsed")
        else:
            reasoning_placeholder.info("No reasoning data available for this frame")
    
    # Update the display for the current frame
    update_display(st.session_state.replay_frame)
    
    # Auto-play the replay if active
    if st.session_state.replay_active:
        # Get the time to wait based on speed
        wait_time = 1 / st.session_state.replay_speed
        
        # Wait for the specified time
        time.sleep(wait_time)
        
        # Move to the next frame
        if st.session_state.replay_frame < len(screenshots) - 1:
            st.session_state.replay_frame += 1
            # Force a rerun to update the display
            st.rerun()
        else:
            # End of replay
            st.session_state.replay_active = False
            st.info("Replay complete!")
            
    # Add a progress bar to show replay progress
    progress_percentage = st.session_state.replay_frame / (len(screenshots) - 1) if len(screenshots) > 1 else 0
    st.progress(progress_percentage)
    
    # Display session summary statistics
    st.subheader("Session Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Screenshots", len(screenshots))
    col2.metric("Total Actions", len(actions))
    col3.metric("Reasoning Events", len(reasoning_data))
    
    # Calculate session duration if timestamps are available
    if screenshots and len(screenshots) >= 2:
        try:
            start_time_str = screenshots[0].get('timestamp', None)
            end_time_str = screenshots[-1].get('timestamp', None)
            
            start_time = parse_timestamp(start_time_str)
            end_time = parse_timestamp(end_time_str)
            
            if start_time and end_time and isinstance(start_time, datetime) and isinstance(end_time, datetime):
                duration_seconds = (end_time - start_time).total_seconds()
                duration_formatted = f"{duration_seconds:.1f}s"
                col4.metric("Duration", duration_formatted)
            else:
                col4.metric("Duration", "Unknown")
        except (IndexError, KeyError, TypeError, AttributeError):
            col4.metric("Duration", "Unknown")
    else:
        col4.metric("Duration", "Unknown")
    
    # Add download buttons for session data
    st.subheader("Export Session Data")
    
    col1, col2 = st.columns(2)
    
    # JSON export
    session_json = json.dumps(session_data, indent=2)
    col1.download_button(
        label="Download JSON",
        data=session_json,
        file_name=f"session_{session_id}.json",
        mime="application/json"
    )
    
    # CSV export of actions
    if actions:
        try:
            # Convert actions to DataFrame
            actions_df = pd.DataFrame(actions)
            csv_buffer = io.StringIO()
            actions_df.to_csv(csv_buffer, index=False)
            
            col2.download_button(
                label="Download Actions CSV",
                data=csv_buffer.getvalue(),
                file_name=f"session_{session_id}_actions.csv",
                mime="text/csv"
            )
        except Exception as e:
            col2.error(f"Failed to generate CSV: {str(e)}")
    else:
        col2.button("Download Actions CSV", disabled=True)
    
    # Button to return to main app
    st.button("← Back to Main Application", on_click=lambda: st.query_params.clear())

def add_replay_button_to_session(session_id, container=None):
    """
    Add a replay button to a session in the UI.
    
    Args:
        session_id (str): The ID of the session
        container (st.container, optional): Container to place the button in
    
    Returns:
        bool: True if button is pressed, False otherwise
    """
    if container is None:
        container = st
    
    def start_replay():
        # Set query parameters to show replay view
        st.query_params["replay_session"] = session_id
    
    # Create the button
    if container.button("🎬 Replay", key=f"replay_{session_id}", help="Replay this session"):
        start_replay()
        return True
    
    return False