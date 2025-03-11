import streamlit as st
import base64
import io
import time
import os
import json
from datetime import datetime
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt

from session_manager import SessionManager

def load_dashboard():
    """
    Load the session visualization dashboard
    """
    # Initialize session state variables if they don't exist
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()
    
    # Display the navigation bar
    navigation_bar()
    
    st.markdown("""
    This dashboard provides a visual history of browser automation sessions. 
    View session details, action breakdowns, and performance metrics to understand agent behavior.
    """)
    
    # Get all sessions from the session manager
    sessions = st.session_state.session_manager.list_sessions(limit=20)
    
    if not sessions:
        st.info("No sessions found. Create a new session to see visualization data.")
        return
    
    # Session selector
    session_options = {f"{s['id']} - {s['task'][:30]}...": s['id'] for s in sessions}
    selected_session_name = st.selectbox(
        "Select a session to visualize",
        options=list(session_options.keys()),
        index=0
    )
    selected_session_id = session_options[selected_session_name]
    
    # Load detailed session data
    session_data = st.session_state.session_manager.get_session(selected_session_id)
    
    if not session_data:
        st.error(f"Failed to load session data for ID: {selected_session_id}")
        return
    
    # Display session overview
    st.header("Session Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Status", session_data.get("status", "unknown"))
    with col2:
        created_at = session_data.get("created_at", "Unknown")
        st.metric("Created", created_at)
    with col3:
        # Calculate duration if we have time data
        if "logs" in session_data and len(session_data["logs"]) >= 2:
            try:
                first_log_time = datetime.strptime(session_data["logs"][0].get("timestamp", "00:00:00"), "%H:%M:%S")
                last_log_time = datetime.strptime(session_data["logs"][-1].get("timestamp", "00:00:00"), "%H:%M:%S")
                duration = last_log_time - first_log_time
                duration_str = f"{duration.seconds // 60}m {duration.seconds % 60}s"
            except:
                duration_str = "Unknown"
        else:
            duration_str = "Unknown"
        st.metric("Duration", duration_str)
    
    # Task description
    st.subheader("Task")
    st.info(session_data.get("task", "No task description available"))
    
    # Tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Action Timeline", "Screenshots", "Logs", "Performance"])
    
    # Tab 1: Action Timeline
    with tab1:
        st.subheader("Agent Action Timeline")
        
        # Extract actions from logs
        actions = []
        timestamps = []
        
        for log in session_data.get("logs", []):
            message = log.get("message", "")
            if "Executing action:" in message:
                # Extract action type from log message
                try:
                    action_type = message.split("Executing action:")[1].split("(Call ID")[0].strip()
                    timestamp = log.get("timestamp", "00:00:00")
                    actions.append(action_type)
                    timestamps.append(timestamp)
                except:
                    pass
        
        if actions:
            # Create a DataFrame for visualization
            action_data = pd.DataFrame({
                "Timestamp": timestamps,
                "Action": actions
            })
            
            # Count action types
            action_counts = action_data["Action"].value_counts().reset_index()
            action_counts.columns = ["Action", "Count"]
            
            # Display action counts as a bar chart
            st.bar_chart(action_counts.set_index("Action"))
            
            # Display action timeline
            chart = alt.Chart(action_data).mark_circle(size=100).encode(
                x=alt.X("Timestamp:N", title="Time"),
                y=alt.Y("Action:N", title="Action Type"),
                color="Action:N",
                tooltip=["Timestamp", "Action"]
            ).properties(
                width=700,
                height=300,
                title="Action Timeline"
            )
            
            st.altair_chart(chart, use_container_width=True)
            
            # Display action data as a table
            st.dataframe(action_data)
        else:
            st.info("No actions found in this session.")
    
    # Tab 2: Screenshots
    with tab2:
        st.subheader("Screenshot Timeline")
        
        screenshots = session_data.get("screenshots", [])
        if screenshots:
            # Show slider to select screenshots by timestamp
            if len(screenshots) > 1:
                screenshot_index = st.slider(
                    "Screenshot Timeline", 
                    0, len(screenshots) - 1, 
                    step=1,
                    format="%d"
                )
            else:
                screenshot_index = 0
                
            # Display selected screenshot
            selected_screenshot = screenshots[screenshot_index]
            screenshot_time = selected_screenshot.get("timestamp", "unknown")
            
            st.caption(f"Screenshot at {screenshot_time} (#{screenshot_index + 1} of {len(screenshots)})")
            
            try:
                image_data = base64.b64decode(selected_screenshot.get("data", ""))
                image = Image.open(io.BytesIO(image_data))
                st.image(image, use_column_width=True)
                
                # Add download button for the screenshot
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                st.download_button(
                    label="Download Screenshot",
                    data=buffer.getvalue(),
                    file_name=f"screenshot_{screenshot_time.replace(':', '-')}.png",
                    mime="image/png"
                )
            except Exception as e:
                st.error(f"Failed to display screenshot: {str(e)}")
        else:
            st.info("No screenshots available for this session.")
    
    # Tab 3: Logs
    with tab3:
        st.subheader("Session Logs")
        
        logs = session_data.get("logs", [])
        if logs:
            # Filter options
            filter_option = st.selectbox(
                "Filter logs by type:",
                options=["All", "Actions", "Safety Checks", "Errors", "Agent Messages"]
            )
            
            filtered_logs = []
            for log in logs:
                message = log.get("message", "")
                timestamp = log.get("timestamp", "00:00:00")
                
                if filter_option == "All":
                    filtered_logs.append(f"[{timestamp}] {message}")
                elif filter_option == "Actions" and "Executing action:" in message:
                    filtered_logs.append(f"[{timestamp}] {message}")
                elif filter_option == "Safety Checks" and "Safety check" in message:
                    filtered_logs.append(f"[{timestamp}] {message}")
                elif filter_option == "Errors" and "Error" in message:
                    filtered_logs.append(f"[{timestamp}] {message}")
                elif filter_option == "Agent Messages" and "Agent message:" in message:
                    filtered_logs.append(f"[{timestamp}] {message}")
            
            if filtered_logs:
                logs_text = "\n".join(filtered_logs)
                st.text_area("Filtered Logs", value=logs_text, height=400, key="logs_display", label_visibility="collapsed")
                
                # Add download button for logs
                st.download_button(
                    label="Download Logs",
                    data=logs_text,
                    file_name=f"session_logs_{selected_session_id[:8]}.txt",
                    mime="text/plain"
                )
            else:
                st.info(f"No logs matching the '{filter_option}' filter.")
        else:
            st.info("No logs available for this session.")
    
    # Tab 4: Performance
    with tab4:
        st.subheader("Session Performance Metrics")
        
        logs = session_data.get("logs", [])
        if logs:
            # Action execution times
            action_times = []
            action_types = []
            
            for i in range(len(logs) - 1):
                message = logs[i].get("message", "")
                if "Executing action:" in message:
                    try:
                        # Get action type
                        action_type = message.split("Executing action:")[1].split("(Call ID")[0].strip()
                        
                        # Get timestamps
                        current_time = datetime.strptime(logs[i].get("timestamp", "00:00:00"), "%H:%M:%S")
                        next_time = datetime.strptime(logs[i+1].get("timestamp", "00:00:00"), "%H:%M:%S")
                        
                        # Calculate duration in seconds
                        duration = (next_time - current_time).total_seconds()
                        
                        if 0 < duration < 60:  # Sanity check: ignore invalid times
                            action_times.append(duration)
                            action_types.append(action_type)
                    except:
                        pass
            
            if action_times:
                # Create dataframe
                performance_data = pd.DataFrame({
                    "Action Type": action_types,
                    "Duration (seconds)": action_times
                })
                
                # Average execution time by action type
                avg_times = performance_data.groupby("Action Type")["Duration (seconds)"].mean().reset_index()
                
                # Display chart
                chart = alt.Chart(avg_times).mark_bar().encode(
                    x=alt.X("Action Type:N", title="Action Type"),
                    y=alt.Y("Duration (seconds):Q", title="Average Duration (seconds)"),
                    color="Action Type:N",
                    tooltip=["Action Type", "Duration (seconds)"]
                ).properties(
                    width=700,
                    height=400,
                    title="Average Action Execution Time"
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                # Overall stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Action Time", f"{sum(action_times)/len(action_times):.2f}s")
                with col2:
                    st.metric("Fastest Action", f"{min(action_times):.2f}s")
                with col3:
                    st.metric("Slowest Action", f"{max(action_times):.2f}s")
                
                # Display raw data
                st.dataframe(performance_data)
            else:
                st.info("Not enough action data to calculate performance metrics.")
        else:
            st.info("No logs available for performance analysis.")
    
    # Bottom section: Session management
    st.header("Session Management")
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate session link
        session_link = st.session_state.session_manager.get_session_link(
            selected_session_id,
            base_url="http://0.0.0.0:5000"
        )
        st.text_input(
            "Session Link",
            value=session_link,
            key="dashboard_session_link",
            disabled=True
        )
    
    with col2:
        # Return to main app button
        if st.button("Return to Main App", use_container_width=True):
            # Redirect back to the main app
            st.markdown("""
            <meta http-equiv="refresh" content="0;URL='/'" />
            """, unsafe_allow_html=True)
            st.info("Redirecting to main app...")
            st.stop()

# Add a navigation bar at the top
def navigation_bar():
    """Display a navigation bar at the top of the dashboard"""
    col1, col2 = st.columns([7, 3])
    with col1:
        st.markdown("### 📊 Session Visualization Dashboard")
    with col2:
        if st.button("🏠 Back to Main App", type="primary", use_container_width=True):
            # Redirect back to the main app
            st.markdown("""
            <meta http-equiv="refresh" content="0;URL='/'" />
            """, unsafe_allow_html=True)
            st.info("Redirecting to main app...")
            st.stop()
    st.divider()

if __name__ == "__main__":
    load_dashboard()