import os
import base64
import time
from PIL import Image, ImageDraw, ImageFont
import io

class MockBrowserAutomation:
    """
    A mock browser automation class for environments where Playwright can't be installed.
    This provides a simulated browser experience for testing the application UI.
    """
    
    def __init__(self, headless=True, width=1024, height=768, starting_url="https://www.google.com"):
        """
        Initialize the mock browser automation.
        
        Args:
            headless (bool): Not used in mock version.
            width (int): The width of the browser window.
            height (int): The height of the browser window.
            starting_url (str): The URL to navigate to when starting the browser.
        """
        self.width = width
        self.height = height
        self.current_url = starting_url
        self.clicked_points = []
        self.typed_text = ""
        self.last_action = None
        
        # Create an initial screenshot
        self._generate_screenshot()
    
    def _generate_screenshot(self):
        """
        Generate a mock screenshot with some visual information.
        """
        # Create a blank image
        self.image = Image.new('RGB', (self.width, self.height), color=(255, 255, 255))
        draw = ImageDraw.Draw(self.image)
        
        # Add URL bar
        draw.rectangle(((0, 0), (self.width, 40)), fill=(240, 240, 240))
        draw.text((10, 10), f"URL: {self.current_url}", fill=(0, 0, 0))
        
        # Add page content
        draw.rectangle(((0, 40), (self.width, 80)), fill=(230, 230, 230))
        draw.text((10, 50), "Mock Browser - Simulated Content", fill=(0, 0, 0))
        
        # Add info about the current state
        y_pos = 100
        draw.text((10, y_pos), "Recent Actions:", fill=(0, 0, 0))
        y_pos += 30
        
        if self.last_action:
            draw.text((20, y_pos), f"Action: {self.last_action}", fill=(0, 0, 0))
            y_pos += 20
        
        if self.typed_text:
            draw.text((20, y_pos), f"Typed: {self.typed_text}", fill=(0, 0, 100))
            y_pos += 20
            
        if self.clicked_points:
            for i, point in enumerate(self.clicked_points[-5:]):  # Show last 5 clicks
                draw.text((20, y_pos), f"Click {i+1}: ({point[0]}, {point[1]})", fill=(100, 0, 0))
                # Draw a circle at the click position
                draw.ellipse((point[0]-5, point[1]-5, point[0]+5, point[1]+5), fill=(255, 0, 0))
                y_pos += 20
        
        # Draw a message about the mock browser
        draw.text((self.width // 2 - 200, self.height - 50), 
                  "This is a mock browser for testing. Playwright cannot be installed in this environment.",
                  fill=(150, 0, 0))
    
    def get_screenshot(self):
        """
        Get the current screenshot.
        
        Returns:
            bytes: The screenshot as bytes.
        """
        img_byte_arr = io.BytesIO()
        self.image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    def execute_action(self, action):
        """
        Execute a browser action based on the action type.
        
        Args:
            action: The action object from the Computer Use Agent API.
        """
        # Check action type
        if hasattr(action, 'type'):
            action_type = action.type
        else:
            action_type = action.get("type", "")
        
        self.last_action = action_type
        
        # Handle different action types
        if action_type == "click":
            self._handle_click(action)
        elif action_type == "double_click":
            self._handle_click(action, is_double=True)
        elif action_type == "type":
            self._handle_type(action)
        elif action_type == "keypress":
            self._handle_keypress(action)
        elif action_type == "scroll":
            self._handle_scroll(action)
        elif action_type == "navigate":
            self._handle_navigate(action)
        
        # Generate a new screenshot after the action
        self._generate_screenshot()
    
    def _handle_click(self, action, is_double=False):
        """Handle click or double-click action"""
        if hasattr(action, 'x') and hasattr(action, 'y'):
            x, y = action.x, action.y
        else:
            x = action.get("x", 100)
            y = action.get("y", 100)
        
        self.clicked_points.append((x, y))
        prefix = "Double-" if is_double else ""
        print(f"{prefix}Clicked at ({x}, {y})")
    
    def _handle_type(self, action):
        """Handle type action"""
        if hasattr(action, 'text'):
            text = action.text
        else:
            text = action.get("text", "")
        
        self.typed_text = text
        print(f"Typed: {text}")
    
    def _handle_keypress(self, action):
        """Handle keypress action"""
        if hasattr(action, 'keys'):
            keys = action.keys
            key_str = ", ".join(keys)
        else:
            key_str = action.get("key", "")
        
        print(f"Pressed key(s): {key_str}")
    
    def _handle_scroll(self, action):
        """Handle scroll action"""
        if hasattr(action, 'scroll_x') and hasattr(action, 'scroll_y'):
            dx, dy = action.scroll_x, action.scroll_y
        else:
            dx = action.get("dx", 0)
            dy = action.get("dy", 0)
        
        print(f"Scrolled: ({dx}, {dy})")
    
    def _handle_navigate(self, action):
        """Handle navigate action"""
        if hasattr(action, 'url'):
            url = action.url
        else:
            url = action.get("url", "https://www.example.com")
        
        self.current_url = url
        print(f"Navigated to: {url}")
    
    def navigate(self, url):
        """
        Navigate to a specific URL.
        
        Args:
            url (str): The URL to navigate to.
        """
        self.current_url = url
        print(f"Navigated to: {url}")
        self._generate_screenshot()
    
    def close(self):
        """
        Close the mock browser.
        """
        print("Mock browser closed")