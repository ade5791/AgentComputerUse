import time
from playwright.sync_api import sync_playwright

class BrowserAutomation:
    """
    A class to handle browser automation using Playwright.
    """
    
    def __init__(self, headless=False, width=1024, height=768, starting_url="https://www.google.com"):
        """
        Initialize the browser automation.
        
        Args:
            headless (bool): Whether to run the browser in headless mode.
            width (int): The width of the browser window.
            height (int): The height of the browser window.
            starting_url (str): The URL to navigate to when starting the browser.
        """
        self.playwright = sync_playwright().start()
        
        # Launch browser with security settings
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            chromium_sandbox=True,
            env={},  # Empty environment variables for security
            args=[
                "--disable-extensions",
                "--disable-file-system"
            ]
        )
        
        # Create a new page and set viewport size
        self.page = self.browser.new_page()
        self.page.set_viewport_size({"width": width, "height": height})
        
        # Navigate to starting URL
        self.page.goto(starting_url)
        
        # Store dimensions for later use
        self.width = width
        self.height = height
    
    def get_screenshot(self):
        """
        Take a screenshot of the current page.
        
        Returns:
            bytes: The screenshot as bytes.
        """
        return self.page.screenshot()
    
    def execute_action(self, action):
        """
        Execute a browser action based on the action type.
        
        Args:
            action: The action object from the Computer Use Agent API.
        """
        action_type = action.type
        
        if action_type == "click":
            self._click(action)
        elif action_type == "double_click":
            self._double_click(action)
        elif action_type == "scroll":
            self._scroll(action)
        elif action_type == "type":
            self._type(action)
        elif action_type == "keypress":
            self._keypress(action)
        elif action_type == "wait":
            self._wait(action)
        elif action_type == "screenshot":
            # No need to do anything, we take screenshots at each step
            pass
        else:
            raise ValueError(f"Unsupported action type: {action_type}")
    
    def _click(self, action):
        """
        Perform a click action.
        
        Args:
            action: The click action details.
        """
        x, y = int(action.x), int(action.y)
        button = action.button if hasattr(action, 'button') else "left"
        
        # Ensure coordinates are within viewport
        if x < 0 or x > self.width or y < 0 or y > self.height:
            raise ValueError(f"Click coordinates ({x}, {y}) are outside viewport ({self.width}, {self.height})")
        
        # Map button string to Playwright button
        button_map = {
            "left": "left",
            "middle": "middle",
            "right": "right"
        }
        playwright_button = button_map.get(button, "left")
        
        # Perform the click
        self.page.mouse.click(x, y, button=playwright_button)
    
    def _double_click(self, action):
        """
        Perform a double-click action.
        
        Args:
            action: The double-click action details.
        """
        x, y = int(action.x), int(action.y)
        
        # Ensure coordinates are within viewport
        if x < 0 or x > self.width or y < 0 or y > self.height:
            raise ValueError(f"Double-click coordinates ({x}, {y}) are outside viewport ({self.width}, {self.height})")
        
        # Perform the double-click
        self.page.mouse.dblclick(x, y)
    
    def _scroll(self, action):
        """
        Perform a scroll action.
        
        Args:
            action: The scroll action details.
        """
        x, y = int(action.x), int(action.y)
        scroll_x, scroll_y = int(getattr(action, 'scroll_x', 0)), int(getattr(action, 'scroll_y', 0))
        
        # Position mouse at given coordinates
        self.page.mouse.move(x, y)
        
        # Perform the scroll
        self.page.mouse.wheel(delta_x=scroll_x, delta_y=scroll_y)
    
    def _type(self, action):
        """
        Perform a type action.
        
        Args:
            action: The type action details.
        """
        text = action.text
        
        # Type the text
        self.page.keyboard.type(text)
    
    def _keypress(self, action):
        """
        Perform a keypress action.
        
        Args:
            action: The keypress action details.
        """
        keys = action.keys
        
        # Press each key one by one
        for key in keys:
            # Map some common key names to Playwright keys
            key_map = {
                "enter": "Enter",
                "tab": "Tab",
                "escape": "Escape",
                "space": " ",
                "backspace": "Backspace",
                "delete": "Delete",
                "arrowup": "ArrowUp",
                "arrowdown": "ArrowDown",
                "arrowleft": "ArrowLeft",
                "arrowright": "ArrowRight"
            }
            
            playwright_key = key_map.get(key.lower(), key)
            self.page.keyboard.press(playwright_key)
    
    def _wait(self, action):
        """
        Perform a wait action.
        
        Args:
            action: The wait action details.
        """
        # Default wait time is 2 seconds if not specified
        wait_time = getattr(action, 'time', 2)
        
        # Ensure wait time is reasonable
        wait_time = max(0, min(10, wait_time))  # Cap at 10 seconds
        
        time.sleep(wait_time)
    
    def navigate(self, url):
        """
        Navigate to a specific URL.
        
        Args:
            url (str): The URL to navigate to.
        """
        self.page.goto(url)
    
    def close(self):
        """
        Close the browser and clean up resources.
        """
        if self.browser:
            self.browser.close()
        
        if self.playwright:
            self.playwright.stop()
