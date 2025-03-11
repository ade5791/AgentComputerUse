import uuid
import json
import os
from datetime import datetime
import streamlit as st

class SessionManager:
    """
    A class to manage browser automation sessions and generate shareable links.
    """
    
    def __init__(self, session_dir="sessions"):
        """
        Initialize the session manager.
        
        Args:
            session_dir (str): Directory to store session information.
        """
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)
        
    def create_session(self, task, environment, browser_config):
        """
        Create a new session for browser automation.
        
        Args:
            task (str): The task description for the agent.
            environment (str): The environment type (browser, mac, windows, ubuntu).
            browser_config (dict): Configuration for the browser.
            
        Returns:
            str: The session ID.
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        session_data = {
            "id": session_id,
            "created_at": timestamp,
            "task": task,
            "environment": environment,
            "browser_config": browser_config,
            "status": "created",
            "logs": [],
            "screenshots": []
        }
        
        self._save_session(session_id, session_data)
        return session_id
    
    def update_session(self, session_id, updates):
        """
        Update a session with new data.
        
        Args:
            session_id (str): The session ID.
            updates (dict): Updates to apply to the session.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Update session data with new values
        session_data.update(updates)
        
        # Update timestamp
        session_data["updated_at"] = datetime.now().isoformat()
        
        self._save_session(session_id, session_data)
        return True
    
    def add_log(self, session_id, message):
        """
        Add a log message to a session.
        
        Args:
            session_id (str): The session ID.
            message (str): The log message.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        timestamp = datetime.now().isoformat()
        log_entry = {"timestamp": timestamp, "message": message}
        
        if "logs" not in session_data:
            session_data["logs"] = []
            
        session_data["logs"].append(log_entry)
        
        self._save_session(session_id, session_data)
        return True
    
    def add_screenshot(self, session_id, screenshot_base64):
        """
        Add a screenshot to a session.
        
        Args:
            session_id (str): The session ID.
            screenshot_base64 (str): The base64-encoded screenshot.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        timestamp = datetime.now().isoformat()
        screenshot_entry = {"timestamp": timestamp, "data": screenshot_base64}
        
        if "screenshots" not in session_data:
            session_data["screenshots"] = []
            
        # Keep only the last 5 screenshots to save space
        session_data["screenshots"].append(screenshot_entry)
        if len(session_data["screenshots"]) > 5:
            session_data["screenshots"] = session_data["screenshots"][-5:]
        
        self._save_session(session_id, session_data)
        return True
    
    def get_session(self, session_id):
        """
        Get session data by ID.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            dict: The session data or None if not found.
        """
        session_path = os.path.join(self.session_dir, f"{session_id}.json")
        
        if not os.path.exists(session_path):
            return None
        
        try:
            with open(session_path, "r") as f:
                return json.load(f)
        except Exception:
            return None
    
    def get_session_link(self, session_id, base_url=None):
        """
        Generate a shareable link for a session.
        
        Args:
            session_id (str): The session ID.
            base_url (str): The base URL for the application.
            
        Returns:
            str: The shareable link.
        """
        if not base_url:
            # Default to localhost if no base URL is provided
            base_url = "http://localhost:5000"
        
        return f"{base_url}?session={session_id}"
    
    def list_sessions(self, limit=10):
        """
        List recent sessions.
        
        Args:
            limit (int): The maximum number of sessions to return.
            
        Returns:
            list: List of session summaries.
        """
        sessions = []
        
        if os.path.exists(self.session_dir):
            for filename in os.listdir(self.session_dir):
                if filename.endswith(".json"):
                    try:
                        session_path = os.path.join(self.session_dir, filename)
                        with open(session_path, "r") as f:
                            session_data = json.load(f)
                            
                            # Create a summary with just the essential info
                            summary = {
                                "id": session_data.get("id", ""),
                                "created_at": session_data.get("created_at", ""),
                                "task": session_data.get("task", ""),
                                "environment": session_data.get("environment", ""),
                                "status": session_data.get("status", "unknown")
                            }
                            
                            sessions.append(summary)
                    except Exception:
                        continue
        
        # Sort by created_at timestamp (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Limit the number of results
        return sessions[:limit]
    
    def _save_session(self, session_id, session_data):
        """
        Save session data to a file.
        
        Args:
            session_id (str): The session ID.
            session_data (dict): The session data to save.
        """
        session_path = os.path.join(self.session_dir, f"{session_id}.json")
        
        with open(session_path, "w") as f:
            json.dump(session_data, f, indent=2)