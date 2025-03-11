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
import session_replay

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
    
    # Add replay button for session
    col1, col2 = st.columns([1, 3])
    with col1:
        # Add animated replay button using session_replay
        session_replay.add_replay_button_to_session(selected_session_id)
    
    with col2:
        st.write("Click 'Replay' to watch a detailed, animated playback of this session with all actions and reasoning.")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
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
    with col4:
        # Display the count of reasoning data entries
        reasoning_count = len(session_data.get("reasoning_data", []))
        st.metric("Reasoning Data", f"{reasoning_count} entries")
    
    # Task description
    st.subheader("Task")
    st.info(session_data.get("task", "No task description available"))
    
    # Tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Action Timeline", "Screenshots", "Logs", "Reasoning", "Performance"])
    
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
            # Add replay button at the top of screenshot view
            st.info("For a detailed playback with animation and reasoning data, use the 'Replay' button below:")
            session_replay.add_replay_button_to_session(selected_session_id)
            
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
    
    # Tab 4: Reasoning Data
    with tab4:
        st.subheader("Agent Reasoning Data")
        
        reasoning_data = session_data.get("reasoning_data", [])
        if reasoning_data:
            # Add replay button for better reasoning visualization
            st.info("For animated playback with synchronized reasoning visualization, use the 'Replay' button:")
            session_replay.add_replay_button_to_session(selected_session_id)
            
            # Show number of reasoning entries and metrics
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric("Total Reasoning Events", len(reasoning_data))
            
            # Calculate average reasoning data size
            avg_size = sum([len(json.dumps(item.get("content", {}))) for item in reasoning_data]) / len(reasoning_data)
            with metrics_col2:
                st.metric("Avg Content Size", f"{avg_size:.0f} chars")
            
            # Calculate time span of reasoning data
            try:
                timestamps = [datetime.fromisoformat(item.get("timestamp")) for item in reasoning_data 
                             if item.get("timestamp") and "T" in item.get("timestamp")]
                if timestamps:
                    time_span = max(timestamps) - min(timestamps)
                    with metrics_col3:
                        st.metric("Time Span", f"{time_span.total_seconds():.1f} sec")
            except:
                with metrics_col3:
                    st.metric("Time Span", "Unknown")
            
            # Add search functionality for reasoning data
            search_query = st.text_input("Search reasoning data content:", 
                                        placeholder="Enter keywords to search...")
            
            # Filter reasoning data based on search
            filtered_reasoning_data = reasoning_data
            if search_query:
                filtered_reasoning_data = []
                for item in reasoning_data:
                    content_str = json.dumps(item.get("content", {})).lower()
                    if search_query.lower() in content_str:
                        filtered_reasoning_data.append(item)
                
                st.info(f"Found {len(filtered_reasoning_data)} matching reasoning events")
            
            # Create a dataframe for visualizing reasoning data
            if filtered_reasoning_data:
                reasoning_df = pd.DataFrame({
                    "Timestamp": [item.get("timestamp", "unknown") for item in filtered_reasoning_data],
                    "ID": [item.get("id", "unknown") for item in filtered_reasoning_data],
                    "Content Size": [len(json.dumps(item.get("content", {}))) for item in filtered_reasoning_data]
                })
                
                # Add a timeline visualization to show when reasoning occurred
                timeline_chart = alt.Chart(reasoning_df).mark_circle().encode(
                    x=alt.X("Timestamp:N", title="Time"),
                    y=alt.Y("index:O", title="Reasoning Event", axis=None),
                    size=alt.Size("Content Size:Q", scale=alt.Scale(range=[50, 200])),
                    color=alt.Color("Content Size:Q", scale=alt.Scale(scheme="viridis")),
                    tooltip=["Timestamp", "ID", "Content Size"]
                ).properties(
                    width=700,
                    height=100,
                    title="Reasoning Event Timeline"
                )
                
                st.altair_chart(timeline_chart, use_container_width=True)
                
                # Create tabs for different reasoning visualizations
                reason_viz_tab1, reason_viz_tab2 = st.tabs(["Detail View", "Relationship View"])
                
                # Tab 1: Detail View - shows individual reasoning entries
                with reason_viz_tab1:
                    # Create a dropdown to select reasoning data by timestamp
                    reasoning_timestamps = [item.get("timestamp", "unknown") for item in filtered_reasoning_data]
                    selected_timestamp = st.selectbox(
                        "Select reasoning data by timestamp:",
                        options=reasoning_timestamps,
                        index=0
                    )
                    
                    # Get the selected reasoning data
                    selected_data = None
                    for item in filtered_reasoning_data:
                        if item.get("timestamp") == selected_timestamp:
                            selected_data = item
                            break
                    
                    if selected_data:
                        st.subheader("Detailed Reasoning")
                        
                        # Display reasoning content
                        reasoning_id = selected_data.get("id", "Unknown ID")
                        st.caption(f"Reasoning ID: {reasoning_id}")
                        
                        content = selected_data.get("content", {})
                        if content:
                            # Create expandable sections for different content parts
                            with st.expander("Reasoning Content", expanded=True):
                                # Convert to formatted JSON for better readability
                                st.json(content)
                            
                            # Extract decision points and rationale if available
                            if isinstance(content, dict):
                                if "decision_points" in content:
                                    with st.expander("Decision Points"):
                                        for i, decision in enumerate(content.get("decision_points", [])):
                                            st.markdown(f"**Decision {i+1}:** {decision}")
                                
                                if "rationale" in content:
                                    with st.expander("Rationale"):
                                        st.markdown(content.get("rationale", ""))
                                        
                                if "alternatives_considered" in content:
                                    with st.expander("Alternatives Considered"):
                                        for i, alternative in enumerate(content.get("alternatives_considered", [])):
                                            st.markdown(f"**Alternative {i+1}:** {alternative}")
                            
                            # Add download button for the reasoning data
                            json_data = json.dumps(content, indent=2)
                            st.download_button(
                                label="Download Reasoning Data",
                                data=json_data,
                                file_name=f"reasoning_{reasoning_id}.json",
                                mime="application/json"
                            )
                        else:
                            st.warning("This reasoning entry has no content data.")
                    else:
                        st.error("Failed to find the selected reasoning data.")
                
                # Tab 2: Relationship View - shows relationship between actions and reasoning
                with reason_viz_tab2:
                    st.subheader("Action-Reasoning Relationship")
                    
                    # Extract actions and timestamps from logs
                    actions = []
                    action_timestamps = []
                    
                    for log in session_data.get("logs", []):
                        message = log.get("message", "")
                        if "Executing action:" in message:
                            try:
                                action_type = message.split("Executing action:")[1].split("(Call ID")[0].strip()
                                timestamp = log.get("timestamp", "00:00:00")
                                actions.append(action_type)
                                action_timestamps.append(timestamp)
                            except:
                                pass
                    
                    if actions and action_timestamps:
                        # Create combined timeline with both actions and reasoning
                        action_df = pd.DataFrame({
                            "Timestamp": action_timestamps,
                            "Event": actions,
                            "Type": ["Action"] * len(actions)
                        })
                        
                        reasoning_timeline_df = pd.DataFrame({
                            "Timestamp": [item.get("timestamp", "unknown") for item in filtered_reasoning_data],
                            "Event": [f"Reasoning {i+1}" for i in range(len(filtered_reasoning_data))],
                            "Type": ["Reasoning"] * len(filtered_reasoning_data)
                        })
                        
                        # Combine the dataframes
                        combined_df = pd.concat([action_df, reasoning_timeline_df])
                        
                        # Create the chart
                        combined_chart = alt.Chart(combined_df).mark_circle(size=100).encode(
                            x=alt.X("Timestamp:N", title="Timeline"),
                            y=alt.Y("Event:N", title="Event"),
                            color=alt.Color("Type:N", scale=alt.Scale(domain=["Action", "Reasoning"], 
                                                                     range=["#5470c6", "#91cc75"])),
                            tooltip=["Timestamp", "Event", "Type"]
                        ).properties(
                            width=700,
                            height=400,
                            title="Actions and Reasoning Timeline"
                        )
                        
                        st.altair_chart(combined_chart, use_container_width=True)
                        
                        # Add explanation
                        st.info("This visualization shows the relationship between agent actions and reasoning events. " +
                               "It helps understand how reasoning decisions translate into specific actions.")
                    else:
                        st.info("Not enough action data to create a relationship visualization.")
            else:
                st.warning("No reasoning data matches your search criteria.")
        else:
            st.info("No reasoning data available for this session.")
    
    # Tab 5: Performance
    with tab5:
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