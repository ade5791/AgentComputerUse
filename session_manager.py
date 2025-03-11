import uuid
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import streamlit as st

class SessionManager:
    """
    A class to manage browser automation sessions and generate shareable links.
    Supports multiple concurrent sessions with thread-safe operations.
    """
    
    def __init__(self, session_dir="sessions"):
        """
        Initialize the session manager.
        
        Args:
            session_dir (str): Directory to store session information.
        """
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Thread lock for session operations to ensure thread safety
        self.session_locks: Dict[str, threading.Lock] = {}
        
        # Active session threads for tracking running sessions
        self.active_threads: Dict[str, Dict[str, Any]] = {}
        
        # Cache frequently accessed sessions to reduce disk I/O
        self.session_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = threading.Lock()
        
        # Session inactivity timeout (5 minutes = 300 seconds)
        self.inactivity_timeout = 300
        
        # Start the timeout monitor thread
        self.timeout_monitor_running = True
        self.timeout_monitor = threading.Thread(target=self._monitor_session_timeouts)
        self.timeout_monitor.daemon = True
        self.timeout_monitor.start()
        
    def create_session(self, task, environment, browser_config, user_id=None, name=None, tags=None, priority="normal"):
        """
        Create a new session for browser automation.
        
        Args:
            task (str): The task description for the agent.
            environment (str): The environment type (browser, mac, windows, ubuntu).
            browser_config (dict): Configuration for the browser.
            user_id (str, optional): ID of the user who created the session.
            name (str, optional): Human-readable name for the session.
            tags (list, optional): List of tags for categorizing sessions.
            priority (str, optional): Session priority level ('low', 'normal', 'high').
            
        Returns:
            dict: Session information including ID and task ID.
        """
        session_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Create a lock for this session
        self.session_locks[session_id] = threading.Lock()
        
        session_data = {
            "id": session_id,
            "task_id": task_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "task": task,
            "environment": environment,
            "browser_config": browser_config,
            "status": "created",
            "user_id": user_id,
            "name": name or f"Session {session_id[:8]}",
            "tags": tags or [],
            "priority": priority,
            "logs": [],
            "screenshots": [],
            "safety_checks": [],
            "actions_history": [],
            "current_url": browser_config.get("starting_url", ""),
            "is_paused": False,
            "is_completed": False,
            "completion_time": None,
            "error": None,
            "reasoning_data": []
        }
        
        self._save_session(session_id, session_data)
        
        # Cache the new session
        with self.cache_lock:
            self.session_cache[session_id] = session_data
            
        return {
            "session_id": session_id,
            "task_id": task_id
        }
    
    def update_session(self, session_id, updates):
        """
        Update a session with new data. Thread-safe operation.
        
        Args:
            session_id (str): The session ID.
            updates (dict): Updates to apply to the session.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            # Update session data with new values
            session_data.update(updates)
            
            # Update timestamp
            session_data["updated_at"] = datetime.now().isoformat()
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def add_log(self, session_id, message):
        """
        Add a log message to a session. Thread-safe operation.
        
        Args:
            session_id (str): The session ID.
            message (str): The log message.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            # Check cache first for performance
            with self.cache_lock:
                if session_id in self.session_cache:
                    session_data = self.session_cache[session_id]
                else:
                    session_data = self.get_session(session_id)
                    if session_data:
                        self.session_cache[session_id] = session_data
            
            if not session_data:
                return False
            
            # Store both ISO format (for precise sorting) and a human-readable time format (for display)
            now = datetime.now()
            timestamp_iso = now.isoformat()
            timestamp_display = now.strftime("%H:%M:%S")
            
            log_entry = {
                "timestamp": timestamp_display,  # For dashboard display
                "timestamp_iso": timestamp_iso,  # For precise sorting
                "message": message
            }
            
            if "logs" not in session_data:
                session_data["logs"] = []
                
            session_data["logs"].append(log_entry)
            
            # Update session data for auto cleanup and limiting
            if len(session_data["logs"]) > 1000:  # Limit log entries to prevent file growth
                session_data["logs"] = session_data["logs"][-1000:]
                
            # Update the last updated timestamp
            session_data["updated_at"] = timestamp_iso
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def add_screenshot(self, session_id, screenshot_base64):
        """
        Add a screenshot to a session. Thread-safe operation.
        
        Args:
            session_id (str): The session ID.
            screenshot_base64 (str): The base64-encoded screenshot.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            # Check cache first for performance
            with self.cache_lock:
                if session_id in self.session_cache:
                    session_data = self.session_cache[session_id]
                else:
                    session_data = self.get_session(session_id)
                    if session_data:
                        self.session_cache[session_id] = session_data
                        
            if not session_data:
                return False
            
            # Store both ISO format (for precise sorting) and a human-readable time format (for display)
            now = datetime.now()
            timestamp_iso = now.isoformat()
            timestamp_display = now.strftime("%H:%M:%S")
            
            screenshot_entry = {
                "timestamp": timestamp_display,  # For dashboard display
                "timestamp_iso": timestamp_iso,  # For precise sorting
                "data": screenshot_base64
            }
            
            if "screenshots" not in session_data:
                session_data["screenshots"] = []
                
            # Store the last 10 screenshots to provide history for visualization while limiting file size
            session_data["screenshots"].append(screenshot_entry)
            if len(session_data["screenshots"]) > 10:
                session_data["screenshots"] = session_data["screenshots"][-10:]
                
            # Update the last updated timestamp
            session_data["updated_at"] = timestamp_iso
            
            # Save the current screenshot as the latest for quick access
            session_data["current_screenshot"] = screenshot_base64
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def get_session(self, session_id):
        """
        Get session data by ID. Uses caching for performance.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            dict: The session data or None if not found.
        """
        # Check cache first
        with self.cache_lock:
            if session_id in self.session_cache:
                return self.session_cache[session_id]
                
        # Not in cache, read from disk
        session_path = os.path.join(self.session_dir, f"{session_id}.json")
        
        if not os.path.exists(session_path):
            return None
        
        try:
            with open(session_path, "r") as f:
                session_data = json.load(f)
                
            # Cache the session data for future use
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return session_data
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
    
    def list_sessions(self, limit=50, filter_by=None, sort_field="created_at", sort_direction="desc", user_id=None, tags=None, status=None):
        """
        List sessions with flexible filtering and sorting options.
        
        Args:
            limit (int): The maximum number of sessions to return.
            filter_by (dict, optional): Filtering criteria as key-value pairs.
            sort_field (str, optional): Field to sort by (default: "created_at").
            sort_direction (str, optional): Sort direction ("asc" or "desc").
            user_id (str, optional): Filter by user ID.
            tags (list, optional): Filter by tags.
            status (str, optional): Filter by session status.
            
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
                            
                            # Apply filters
                            if filter_by:
                                skip = False
                                for key, value in filter_by.items():
                                    if key in session_data and session_data[key] != value:
                                        skip = True
                                        break
                                if skip:
                                    continue
                                    
                            # Apply user filter
                            if user_id and session_data.get("user_id") != user_id:
                                continue
                                
                            # Apply tags filter
                            if tags:
                                session_tags = session_data.get("tags", [])
                                if not any(tag in session_tags for tag in tags):
                                    continue
                                    
                            # Apply status filter
                            if status and session_data.get("status") != status:
                                continue
                            
                            # Create an enhanced summary with more info
                            summary = {
                                "id": session_data.get("id", ""),
                                "task_id": session_data.get("task_id", ""),
                                "created_at": session_data.get("created_at", ""),
                                "updated_at": session_data.get("updated_at", ""),
                                "name": session_data.get("name", ""),
                                "task": session_data.get("task", ""),
                                "environment": session_data.get("environment", ""),
                                "status": session_data.get("status", "unknown"),
                                "is_paused": session_data.get("is_paused", False),
                                "is_completed": session_data.get("is_completed", False),
                                "user_id": session_data.get("user_id", None),
                                "tags": session_data.get("tags", []),
                                "priority": session_data.get("priority", "normal"),
                                "logs_count": len(session_data.get("logs", [])),
                                "screenshots_count": len(session_data.get("screenshots", [])),
                                "reasoning_data_count": len(session_data.get("reasoning_data", [])),
                                "current_url": session_data.get("current_url", ""),
                                "has_error": bool(session_data.get("error", False)),
                                "has_reasoning_data": len(session_data.get("reasoning_data", [])) > 0
                            }
                            
                            sessions.append(summary)
                    except Exception:
                        continue
        
        # Sort the sessions
        reverse_sort = sort_direction.lower() == "desc"
        sessions.sort(key=lambda x: x.get(sort_field, ""), reverse=reverse_sort)
        
        # Limit the number of results
        return sessions[:limit]
    
    def register_thread(self, session_id, thread_obj, task_id=None):
        """
        Register a thread for a session to track active sessions.
        
        Args:
            session_id (str): The session ID.
            thread_obj: The thread object handling this session.
            task_id (str, optional): The task ID.
            
        Returns:
            bool: True if registration was successful.
        """
        thread_info = {
            "thread": thread_obj,
            "started_at": datetime.now().isoformat(),
            "task_id": task_id
        }
        
        self.active_threads[session_id] = thread_info
        return True
    
    def unregister_thread(self, session_id):
        """
        Unregister a thread for a finished session.
        Also cleans up any browser resources associated with the session.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            bool: True if unregistration was successful.
        """
        try:
            # Try to get active thread info for this session
            if session_id in self.active_threads:
                # Log the unregistration
                self.add_log(session_id, "Unregistering session thread and cleaning up resources")
                
                # Reference to thread info before removing it
                thread_info = self.active_threads[session_id]
                
                # Remove from active threads
                del self.active_threads[session_id]
                
                # Check if session data has browser reference to clean up
                session_data = self.get_session(session_id)
                if session_data and "browser" in session_data:
                    try:
                        # Try to close the browser if it's still open
                        browser = session_data["browser"]
                        if browser and hasattr(browser, "close"):
                            browser.close()
                    except Exception as e:
                        # Log but continue with cleanup
                        print(f"Error closing browser for session {session_id}: {str(e)}")
                
                return True
        except Exception as e:
            print(f"Error unregistering thread for session {session_id}: {str(e)}")
        
        return False
    
    def is_session_active(self, session_id):
        """
        Check if a session has an active thread.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            bool: True if the session is active.
        """
        return session_id in self.active_threads and self.active_threads[session_id]["thread"].is_alive()
    
    def get_active_sessions_count(self):
        """
        Get the count of active sessions.
        
        Returns:
            int: The number of active sessions.
        """
        # Clean up inactive threads first
        self._cleanup_inactive_threads()
        return len(self.active_threads)
    
    def _cleanup_inactive_threads(self):
        """
        Clean up inactive thread references.
        """
        to_remove = []
        for session_id, thread_info in self.active_threads.items():
            if not thread_info["thread"].is_alive():
                to_remove.append(session_id)
                
        for session_id in to_remove:
            self.unregister_thread(session_id)
    
    def add_action(self, session_id, action):
        """
        Add a browser action to the session history.
        
        Args:
            session_id (str): The session ID.
            action (dict): The action data.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            # Check cache first for performance
            with self.cache_lock:
                if session_id in self.session_cache:
                    session_data = self.session_cache[session_id]
                else:
                    session_data = self.get_session(session_id)
                    if session_data:
                        self.session_cache[session_id] = session_data
                        
            if not session_data:
                return False
                
            # Record the action with timestamp
            now = datetime.now()
            timestamp_iso = now.isoformat()
            
            action_record = {
                "timestamp": timestamp_iso,
                "action": action
            }
            
            if "actions_history" not in session_data:
                session_data["actions_history"] = []
                
            session_data["actions_history"].append(action_record)
            
            # Limit history to prevent file growth
            if len(session_data["actions_history"]) > 100:
                session_data["actions_history"] = session_data["actions_history"][-100:]
                
            # Update the last updated timestamp
            session_data["updated_at"] = timestamp_iso
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def pause_session(self, session_id):
        """
        Pause a running session.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        return self.update_session(session_id, {"is_paused": True, "status": "paused"})
    
    def resume_session(self, session_id):
        """
        Resume a paused session.
        
        Args:
            session_id (str): The session ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        return self.update_session(session_id, {"is_paused": False, "status": "running"})
    
    def complete_session(self, session_id, success=True, error=None):
        """
        Mark a session as completed.
        
        Args:
            session_id (str): The session ID.
            success (bool): Whether the session completed successfully.
            error (str, optional): Error message if failed.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        updates = {
            "is_completed": True,
            "completion_time": datetime.now().isoformat(),
            "status": "completed" if success else "failed"
        }
        
        if error:
            updates["error"] = error
            
        return self.update_session(session_id, updates)
    
    def add_reasoning_data(self, session_id, reasoning_data):
        """
        Add reasoning data from the model to a session.
        
        Args:
            session_id (str): The session ID.
            reasoning_data (dict): The reasoning data to add.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            # Check cache first for performance
            with self.cache_lock:
                if session_id in self.session_cache:
                    session_data = self.session_cache[session_id]
                else:
                    session_data = self.get_session(session_id)
                    if session_data:
                        self.session_cache[session_id] = session_data
                        
            if not session_data:
                return False
                
            # Add timestamp to reasoning data
            now = datetime.now()
            timestamp_iso = now.isoformat()
            
            reasoning_item = {
                "id": str(uuid.uuid4()),
                "timestamp": timestamp_iso,
                "content": reasoning_data
            }
            
            if "reasoning_data" not in session_data:
                session_data["reasoning_data"] = []
                
            session_data["reasoning_data"].append(reasoning_item)
            
            # Limit the number of reasoning items to prevent file size growth
            if len(session_data["reasoning_data"]) > 50:
                session_data["reasoning_data"] = session_data["reasoning_data"][-50:]
                
            # Update the last updated timestamp
            session_data["updated_at"] = timestamp_iso
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def add_safety_check(self, session_id, safety_check_data):
        """
        Add a safety check to a session.
        
        Args:
            session_id (str): The session ID.
            safety_check_data (dict): The safety check data.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Ensure we have a lock for this session
        if session_id not in self.session_locks:
            self.session_locks[session_id] = threading.Lock()
            
        # Acquire the lock before updating
        with self.session_locks[session_id]:
            # Check cache first for performance
            with self.cache_lock:
                if session_id in self.session_cache:
                    session_data = self.session_cache[session_id]
                else:
                    session_data = self.get_session(session_id)
                    if session_data:
                        self.session_cache[session_id] = session_data
                        
            if not session_data:
                return False
                
            # Add the safety check
            if "safety_checks" not in session_data:
                session_data["safety_checks"] = []
                
            session_data["safety_checks"].append(safety_check_data)
            
            # Update status to indicate waiting for confirmation
            session_data["status"] = "waiting_for_confirmation"
            
            self._save_session(session_id, session_data)
            
            # Update cache
            with self.cache_lock:
                self.session_cache[session_id] = session_data
                
            return True
    
    def cleanup_old_sessions(self, days_old=7):
        """
        Clean up old session files to save disk space.
        
        Args:
            days_old (int): Age in days of sessions to clean up.
            
        Returns:
            int: Number of sessions cleaned up.
        """
        if not os.path.exists(self.session_dir):
            return 0
            
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        for filename in os.listdir(self.session_dir):
            if not filename.endswith(".json"):
                continue
                
            try:
                session_path = os.path.join(self.session_dir, filename)
                file_stat = os.stat(session_path)
                
                # Check if the file is older than the cutoff
                if file_stat.st_mtime < cutoff_time:
                    # Remove from cache if present
                    session_id = filename.replace(".json", "")
                    with self.cache_lock:
                        if session_id in self.session_cache:
                            del self.session_cache[session_id]
                            
                    # Delete the file
                    os.remove(session_path)
                    cleaned_count += 1
            except Exception:
                continue
                
        return cleaned_count
    
    def _monitor_session_timeouts(self):
        """
        Monitor active sessions for inactivity and automatically end them after timeout period.
        Runs continuously in a separate thread.
        """
        while self.timeout_monitor_running:
            try:
                # Get all active sessions
                active_session_ids = list(self.active_threads.keys())
                
                for session_id in active_session_ids:
                    try:
                        # Skip sessions that are already stopped or completed
                        session_data = self.get_session(session_id)
                        if not session_data or session_data.get("status") in ["completed", "stopped", "error", "timeout"]:
                            continue
                            
                        # Check if session is paused - paused sessions don't timeout
                        if session_data.get("is_paused", False):
                            continue
                            
                        # Calculate time since last activity
                        last_update = session_data.get("updated_at")
                        if not last_update:
                            continue
                            
                        try:
                            last_update_time = datetime.fromisoformat(last_update)
                            elapsed_seconds = (datetime.now() - last_update_time).total_seconds()
                            
                            # Check if session exceeded timeout period
                            if elapsed_seconds > self.inactivity_timeout:
                                # Log the timeout
                                self.add_log(session_id, f"Session automatically terminated due to {self.inactivity_timeout} seconds of inactivity")
                                
                                # End the session with timeout status
                                self.update_session(session_id, {
                                    "status": "timeout",
                                    "is_completed": True,
                                    "completion_time": datetime.now().isoformat()
                                })
                                
                                # Clean up resources
                                self.unregister_thread(session_id)
                        except Exception as e:
                            # Skip sessions with invalid timestamp format
                            continue
                    except Exception as e:
                        # Skip problematic sessions
                        continue
                        
            except Exception as e:
                # Log but continue monitoring
                print(f"Error in session timeout monitor: {str(e)}")
                
            # Check every 30 seconds to avoid excessive CPU usage
            time.sleep(30)
    
    def _save_session(self, session_id, session_data):
        """
        Save session data to a file.
        
        Args:
            session_id (str): The session ID.
            session_data (dict): The session data to save.
        """
        session_path = os.path.join(self.session_dir, f"{session_id}.json")
        
        try:
            with open(session_path, "w") as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            print(f"Error saving session {session_id}: {str(e)}")
            # Try to save to a temporary file if main save fails
            temp_path = os.path.join(self.session_dir, f"{session_id}_temp.json")
            try:
                with open(temp_path, "w") as f:
                    json.dump(session_data, f, indent=2)
            except Exception:
                pass