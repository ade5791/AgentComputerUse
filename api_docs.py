import streamlit as st
import pandas as pd
import requests
import os
import json

def load_api_docs():
    """
    Load the API documentation page
    """
    st.title("🔌 Computer Use Agent API Documentation")
    st.markdown("""
    Welcome to the API documentation for the Computer Use Agent. This page provides information 
    about the available API endpoints, request formats, and response structures.
    
    The API allows you to:
    - Create and manage browser automation sessions
    - Monitor real-time status of running tasks
    - Control execution (pause, resume, stop)
    - Access session history and results
    """)
    
    # API Connection Information
    st.header("API Connection Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Base URL:** http://localhost:5001/api")
        
    with col2:
        api_key = st.text_input("Your API Key (Optional)", type="password")
        if api_key:
            st.session_state.api_key = api_key
            st.success("API Key saved for testing")
    
    # Test API Connection
    st.subheader("Test API Connection")
    
    if st.button("Test Connection"):
        try:
            response = requests.get("http://localhost:5001/api/health")
            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ API is online - {data['message']}")
                
                # Show API details
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", data["data"]["status"])
                col2.metric("Active Sessions", data["data"]["active_sessions"])
                col3.metric("Version", data["data"]["version"])
                
                # Show environment info
                st.info(f"Browser Environment: {data['data']['browser_environment']}")
            else:
                st.error(f"❌ API returned error status: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Could not connect to API: {str(e)}")
    
    # API Endpoints Documentation
    st.header("API Endpoints")
    
    # Tabs for different endpoint categories
    tab1, tab2, tab3, tab4 = st.tabs(["Session Management", "Session Control", "Status & Monitoring", "Utility"])
    
    with tab1:
        st.subheader("Session Management Endpoints")
        
        endpoints = [
            {
                "Method": "POST",
                "Endpoint": "/tasks",
                "Description": "Create a new browser automation session",
                "Sample": """
```json
{
  "task": "Search for the best pizza in New York",
  "environment": "browser",
  "display_width": 1024,
  "display_height": 768,
  "headless": true,
  "starting_url": "https://www.google.com",
  "user_id": "user123",
  "session_name": "Pizza Search",
  "tags": ["food", "search"],
  "priority": "normal"
}
```"""
            },
            {
                "Method": "GET",
                "Endpoint": "/sessions",
                "Description": "List all sessions with filtering options",
                "Sample": "?limit=10&sort_field=created_at&sort_direction=desc&status=completed"
            },
            {
                "Method": "POST",
                "Endpoint": "/sessions/batch",
                "Description": "Advanced session filtering and sorting",
                "Sample": """
```json
{
  "limit": 100,
  "filter_by": {
    "created_after": "2025-03-01T00:00:00Z",
    "created_before": "2025-03-10T23:59:59Z"
  },
  "sort_field": "duration",
  "sort_direction": "asc",
  "tags": ["search"]
}
```"""
            },
            {
                "Method": "GET",
                "Endpoint": "/sessions/{session_id}/details",
                "Description": "Get detailed information about a specific session",
                "Sample": "/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890/details"
            },
            {
                "Method": "PUT",
                "Endpoint": "/sessions/{session_id}",
                "Description": "Update session metadata",
                "Sample": """
```json
{
  "name": "Updated Session Name",
  "tags": ["new-tag", "updated"],
  "priority": "high"
}
```"""
            },
            {
                "Method": "POST",
                "Endpoint": "/sessions/cleanup",
                "Description": "Clean up sessions older than specified days",
                "Sample": "?days_old=7"
            }
        ]
        
        # Create a DataFrame
        df = pd.DataFrame(endpoints)
        st.table(df)
        
        # Test API for Session Management
        st.subheader("Test List Sessions")
        
        if st.button("List Recent Sessions"):
            try:
                response = requests.get("http://localhost:5001/api/sessions?limit=5")
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Retrieved {len(data['data']['sessions'])} sessions")
                    
                    # Create a dataframe for the sessions
                    sessions = []
                    for session in data['data']['sessions']:
                        sessions.append({
                            "Session ID": session.get("id", "")[:8] + "...",
                            "Task": session.get("task", "No task")[:30] + "..." if len(session.get("task", "")) > 30 else session.get("task", "No task"),
                            "Status": session.get("status", "Unknown"),
                            "Created": session.get("created_at", "Unknown")
                        })
                    
                    if sessions:
                        st.dataframe(pd.DataFrame(sessions))
                    else:
                        st.info("No sessions found")
                else:
                    st.error(f"❌ API returned error status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Could not connect to API: {str(e)}")
                
    with tab2:
        st.subheader("Session Control Endpoints")
        
        endpoints = [
            {
                "Method": "POST",
                "Endpoint": "/stop/{session_id}",
                "Description": "Stop a running session",
                "Sample": """
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "t1234567"
}
```"""
            },
            {
                "Method": "POST",
                "Endpoint": "/pause/{session_id}",
                "Description": "Pause a running session",
                "Sample": """
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "t1234567"
}
```"""
            },
            {
                "Method": "POST",
                "Endpoint": "/resume/{session_id}",
                "Description": "Resume a paused session",
                "Sample": """
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "t1234567"
}
```"""
            },
            {
                "Method": "POST",
                "Endpoint": "/confirm_safety_check/{session_id}",
                "Description": "Acknowledge safety checks",
                "Sample": """
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "t1234567",
  "confirm": true
}
```"""
            },
            {
                "Method": "POST",
                "Endpoint": "/cleanup_session/{session_id}",
                "Description": "Clean up resources for a completed session",
                "Sample": """
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "t1234567"
}
```"""
            }
        ]
        
        # Create a DataFrame
        df = pd.DataFrame(endpoints)
        st.table(df)
        
    with tab3:
        st.subheader("Status & Monitoring Endpoints")
        
        endpoints = [
            {
                "Method": "GET",
                "Endpoint": "/status/{session_id}/{task_id}",
                "Description": "Get the current status of a session",
                "Sample": "/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890/t1234567"
            },
            {
                "Method": "GET",
                "Endpoint": "/sessions/active",
                "Description": "Get all currently active sessions",
                "Sample": "/sessions/active"
            }
        ]
        
        # Create a DataFrame
        df = pd.DataFrame(endpoints)
        st.table(df)
        
        # Test API for Status Monitoring
        st.subheader("Test Active Sessions")
        
        if st.button("Check Active Sessions"):
            try:
                response = requests.get("http://localhost:5001/api/sessions/active")
                if response.status_code == 200:
                    data = response.json()
                    active_count = len(data['data']['active_sessions'])
                    st.success(f"✅ Found {active_count} active sessions")
                    
                    if active_count > 0:
                        sessions = []
                        for session in data['data']['active_sessions']:
                            sessions.append({
                                "Session ID": session.get("id", "")[:8] + "...",
                                "Name": session.get("name", "Unnamed session"),
                                "Task": session.get("task", "No task")[:30] + "..." if len(session.get("task", "")) > 30 else session.get("task", "No task"),
                                "Status": session.get("status", "Unknown")
                            })
                        
                        st.dataframe(pd.DataFrame(sessions))
                    else:
                        st.info("No active sessions found")
                else:
                    st.error(f"❌ API returned error status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Could not connect to API: {str(e)}")
        
    with tab4:
        st.subheader("Utility Endpoints")
        
        endpoints = [
            {
                "Method": "GET",
                "Endpoint": "/health",
                "Description": "Check the health status of the API",
                "Sample": "/health"
            }
        ]
        
        # Create a DataFrame
        df = pd.DataFrame(endpoints)
        st.table(df)
    
    # API Response Structures
    st.header("API Response Structures")
    
    st.subheader("Standard Response Format")
    st.code("""
{
  "success": true,
  "message": "Human-readable message about the operation",
  "data": {
    // Operation-specific data
  }
}
""", language="json")

    st.subheader("Error Response Format")
    st.code("""
{
  "success": false,
  "message": "Error message",
  "data": {
    "error": "Detailed error information"
  }
}
""", language="json")

    # API Usage Examples
    st.header("Usage Examples")
    
    with st.expander("Python Example - Create a New Session"):
        st.code("""
import requests
import json

# Configuration
API_URL = "http://localhost:5001/api"
API_KEY = "your-api-key"  # Optional

# Create a new session
def create_session(task):
    url = f"{API_URL}/tasks"
    
    data = {
        "task": task,
        "environment": "browser",
        "display_width": 1024,
        "display_height": 768,
        "headless": True,
        "starting_url": "https://www.google.com",
        "api_key": API_KEY,
        "session_name": f"Session for: {task[:20]}..."
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Session created successfully: {result['data']['session_id']}")
        print(f"Session URL: {result['data']['session_url']}")
        return result['data']['session_id'], result['data']['task_id']
    else:
        print(f"Error creating session: {response.status_code}")
        print(response.text)
        return None, None

# Usage
session_id, task_id = create_session("Search for information about OpenAI")
""", language="python")
    
    with st.expander("JavaScript Example - Monitor Session Status"):
        st.code("""
// Monitor session status with JavaScript
async function monitorSession(sessionId, taskId) {
  const apiUrl = 'http://localhost:5001/api';
  
  try {
    const response = await fetch(`${apiUrl}/status/${sessionId}/${taskId}`);
    const data = await response.json();
    
    if (data.success) {
      console.log(`Session status: ${data.data.status}`);
      
      if (data.data.current_screenshot) {
        // Display the screenshot
        document.getElementById('screenshot').src = 
          `data:image/png;base64,${data.data.current_screenshot}`;
      }
      
      // Display logs
      const logElement = document.getElementById('logs');
      logElement.innerHTML = '';
      data.data.logs.forEach(log => {
        const logItem = document.createElement('div');
        logItem.textContent = log;
        logElement.appendChild(logItem);
      });
      
      // Check if we need to handle safety checks
      if (data.data.pending_safety_checks && data.data.pending_safety_checks.length > 0) {
        console.log('Safety checks pending, user confirmation required');
        // Show safety check UI
        showSafetyChecks(data.data.pending_safety_checks);
      }
      
      // Continue monitoring if session is still active
      if (data.data.status === 'running' || data.data.status === 'paused') {
        setTimeout(() => monitorSession(sessionId, taskId), 2000);
      }
    } else {
      console.error(`Error: ${data.message}`);
    }
  } catch (error) {
    console.error(`Failed to monitor session: ${error}`);
  }
}
""", language="javascript")
    
    with st.expander("cURL Example - List Active Sessions"):
        st.code("""
curl -X GET http://localhost:5001/api/sessions/active
""", language="bash")

    # SDK Information
    st.header("Client SDKs")
    
    st.warning("Official client SDKs are under development. In the meantime, you can use the API directly with the examples above.")
    
    # Rate Limiting and Authentication
    st.header("Rate Limiting and Authentication")
    
    st.info("""
    - **Rate Limiting**: The API implements rate limiting to prevent abuse. If you exceed the rate limit, you will receive a `429 Too Many Requests` response.
    - **Authentication**: Authentication is handled through API keys. Include your API key in the request body for endpoints that require authentication.
    """)
    
    # Footer
    st.divider()
    st.markdown("*For more detailed information, refer to the [API_DOCUMENTATION.md](https://github.com/yourusername/computer-use-agent/blob/main/API_DOCUMENTATION.md) file in the repository.*")