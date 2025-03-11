# Computer Use Agent API Documentation

## Overview

This document provides information about the REST API endpoints available in the Computer Use Agent application. The API allows for creating and managing browser automation sessions, monitoring their status, and controlling their execution.

## Base URL

When running locally, the API is available at:
```
http://localhost:5001/api
```

## Authentication

Authentication is handled through API keys. Include your API key in the request body for endpoints that require authentication.

## Session Management Endpoints

### Create a New Session

Creates a new browser automation session and starts executing the specified task.

- **URL**: `/tasks`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "task": "Search for the best pizza in New York",
    "environment": "browser",
    "display_width": 1024,
    "display_height": 768,
    "headless": true,
    "starting_url": "https://www.google.com",
    "api_key": "your-api-key",
    "user_id": "user123",
    "session_name": "Pizza Search",
    "tags": ["food", "search"],
    "priority": "normal",
    "timeout_seconds": 300,
    "max_actions": 50
  }
  ```
- **Required Fields**:
  - `task`: The description of the task to perform
- **Optional Fields**:
  - `environment`: The environment to use (default: "browser")
  - `display_width`: Width of the browser window (default: 1024)
  - `display_height`: Height of the browser window (default: 768)
  - `headless`: Whether to run the browser in headless mode (default: true)
  - `starting_url`: The URL to navigate to when starting (default: "https://www.google.com")
  - `api_key`: Your API key for authentication
  - `user_id`: User identifier for session tracking
  - `session_name`: Human-readable name for the session
  - `tags`: List of tags for categorizing the session
  - `priority`: Session priority ("low", "normal", "high")
  - `timeout_seconds`: Maximum time in seconds for the session
  - `max_actions`: Maximum number of actions to perform
- **Response**:
  ```json
  {
    "success": true,
    "message": "Task started successfully",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "task_id": "t1234567",
      "status": "running",
      "session_url": "http://localhost:5000/sessions/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
  }
  ```

### Get Session Status

Retrieves the current status of a session, including logs and screenshots.

- **URL**: `/status/{session_id}/{task_id}`
- **Method**: `GET`
- **URL Parameters**:
  - `session_id`: The ID of the session
  - `task_id`: The ID of the task
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session status retrieved",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "task_id": "t1234567",
      "status": "running",
      "logs": ["Starting browser", "Navigating to Google", "Typing search query"],
      "current_screenshot": "base64-encoded-image",
      "pending_safety_checks": null,
      "reasoning": [
        {
          "id": "reason_1",
          "content": [
            {
              "type": "text",
              "text": "I'll start by navigating to Google's homepage and search for 'best pizza in New York'"
            }
          ]
        },
        {
          "id": "reason_2",
          "content": [
            {
              "type": "text",
              "text": "I notice there are several review sites in the results. I'll click on the Yelp link to see their rankings."
            }
          ]
        }
      ]
    }
  }
  ```

### List All Sessions

Retrieves a list of sessions with filtering options.

- **URL**: `/sessions`
- **Method**: `GET`
- **Query Parameters**:
  - `limit`: Maximum number of sessions to return (default: 50)
  - `sort_field`: Field to sort by (default: "created_at")
  - `sort_direction`: Sort direction ("asc" or "desc", default: "desc")
  - `user_id`: Filter by user ID
  - `status`: Filter by session status
  - `tag`: Filter by tag
- **Response**:
  ```json
  {
    "success": true,
    "message": "Retrieved 25 sessions",
    "data": {
      "sessions": [
        {
          "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "name": "Pizza Search",
          "task": "Search for the best pizza in New York",
          "status": "completed",
          "created_at": "2025-03-11T10:15:30Z",
          "completed_at": "2025-03-11T10:18:45Z",
          "user_id": "user123",
          "tags": ["food", "search"]
        },
        ...
      ]
    }
  }
  ```

### Advanced Session Filtering

Lists sessions with advanced filtering options.

- **URL**: `/sessions/batch`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "limit": 100,
    "filter_by": {
      "created_after": "2025-03-01T00:00:00Z",
      "created_before": "2025-03-10T23:59:59Z",
      "duration_less_than": 300,
      "has_errors": false
    },
    "sort_field": "duration",
    "sort_direction": "asc",
    "user_id": "user123",
    "tags": ["search"],
    "status": "completed"
  }
  ```
- **Response**: Similar to List All Sessions

### Get Active Sessions

Retrieves information about all currently active sessions.

- **URL**: `/sessions/active`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "success": true,
    "message": "Found 3 active sessions",
    "data": {
      "active_sessions": [
        {
          "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "task_id": "t1234567",
          "started_at": "2025-03-11T10:15:30Z",
          "status": "running",
          "name": "Pizza Search",
          "task": "Search for the best pizza in New York"
        },
        ...
      ]
    }
  }
  ```

### Get Session Details

Retrieves detailed information about a specific session.

- **URL**: `/sessions/{session_id}/details`
- **Method**: `GET`
- **URL Parameters**:
  - `session_id`: The ID of the session
- **Response**:
  ```json
  {
    "success": true,
    "message": "Retrieved details for session a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "data": {
      "session": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "Pizza Search",
        "task": "Search for the best pizza in New York",
        "status": "completed",
        "created_at": "2025-03-11T10:15:30Z",
        "completed_at": "2025-03-11T10:18:45Z",
        "user_id": "user123",
        "tags": ["food", "search"],
        "environment": "browser",
        "browser_config": {
          "display_width": 1024,
          "display_height": 768,
          "headless": true,
          "starting_url": "https://www.google.com"
        },
        "logs": ["Starting browser", "Navigating to Google", "Typing search query"],
        "actions": [
          {
            "type": "navigate",
            "url": "https://www.google.com",
            "timestamp": "2025-03-11T10:15:35Z"
          },
          ...
        ],
        "reasoning_data": [
          {
            "id": "reason_1",
            "timestamp": "2025-03-11T10:15:32Z",
            "content": [
              {
                "type": "text",
                "text": "I'll search for pizza restaurants in New York to find the highest-rated options."
              }
            ]
          },
          {
            "id": "reason_2",
            "timestamp": "2025-03-11T10:16:05Z",
            "content": [
              {
                "type": "text",
                "text": "I'll now click on the Yelp link to see their curated list of top pizza places."
              }
            ]
          }
        ]
      },
      "is_active": false,
      "latest_screenshot": "base64-encoded-image",
      "logs_count": 25,
      "screenshots_count": 8
    }
  }
  ```

### Update Session Details

Updates metadata for a specific session.

- **URL**: `/sessions/{session_id}`
- **Method**: `PUT`
- **URL Parameters**:
  - `session_id`: The ID of the session
- **Request Body**:
  ```json
  {
    "name": "Updated Session Name",
    "tags": ["new-tag", "updated"],
    "priority": "high",
    "user_id": "user456"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session a1b2c3d4-e5f6-7890-abcd-ef1234567890 updated successfully",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "updates": {
        "name": "Updated Session Name",
        "tags": ["new-tag", "updated"],
        "priority": "high",
        "user_id": "user456"
      }
    }
  }
  ```

### Clean Up Old Sessions

Removes sessions older than a specified number of days.

- **URL**: `/sessions/cleanup`
- **Method**: `POST`
- **Query Parameters**:
  - `days_old`: Age in days of sessions to clean up (default: 7)
- **Response**:
  ```json
  {
    "success": true,
    "message": "Cleaned up 15 sessions older than 7 days",
    "data": {
      "cleaned_count": 15
    }
  }
  ```

## Session Control Endpoints

### Stop a Session

Stops a running session.

- **URL**: `/stop/{session_id}`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_id": "t1234567"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session stopped",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "stopped"
    }
  }
  ```

### Pause a Session

Pauses a running session.

- **URL**: `/pause/{session_id}`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_id": "t1234567"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session paused",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "paused"
    }
  }
  ```

### Resume a Session

Resumes a paused session.

- **URL**: `/resume/{session_id}`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_id": "t1234567"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session resumed",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "running"
    }
  }
  ```

### Confirm Safety Checks

Acknowledges safety checks to allow the session to continue.

- **URL**: `/confirm_safety_check/{session_id}`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_id": "t1234567",
    "confirm": true
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Safety checks confirmed",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "running"
    }
  }
  ```

### Clean Up Session Resources

Cleans up resources for a completed session.

- **URL**: `/cleanup_session/{session_id}`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_id": "t1234567"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Session cleaned up",
    "data": {
      "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "cleaned"
    }
  }
  ```

## Utility Endpoints

### Health Check

Checks the health status of the API.

- **URL**: `/health`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "success": true,
    "message": "API is healthy",
    "data": {
      "status": "ok",
      "active_sessions": 3,
      "version": "1.0.0",
      "browser_environment": "mock"
    }
  }
  ```

## Error Responses

When an error occurs, the API will respond with an appropriate HTTP status code and an error message.

Example error response:
```json
{
  "success": false,
  "message": "Session not found",
  "data": {
    "error": "Session with ID a1b2c3d4-e5f6-7890-abcd-ef1234567890 does not exist"
  }
}
```

Common HTTP status codes:
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Rate Limiting

The API implements rate limiting to prevent abuse. If you exceed the rate limit, you will receive a `429 Too Many Requests` response.

## Automatic Session Timeout

For resource optimization and security, sessions automatically end after 5 minutes of inactivity. This feature:

- Prevents abandoned sessions from consuming resources
- Increases security by limiting the exposure window of active sessions
- Improves overall system performance

When a session times out:
- Its status is set to "timeout"
- Browser resources are automatically cleaned up
- A log entry is added to document the timeout event

You can restart a timed-out session by creating a new session with the same task.