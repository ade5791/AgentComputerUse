import os
import asyncio
import base64
from playwright.async_api import async_playwright

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
        self.headless = headless
        self.width = width
        self.height = height
        self.starting_url = starting_url
        self.browser = None
        self.context = None
        self.page = None
        
        # Start the browser asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._start_browser())
    
    async def _start_browser(self):
        """
        Start the browser asynchronously.
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-extensions",
                "--disable-file-system",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": self.width, "height": self.height}
        )
        self.page = await self.context.new_page()
        await self.page.goto(self.starting_url)
    
    def get_screenshot(self):
        """
        Take a screenshot of the current page.
        
        Returns:
            bytes: The screenshot as bytes.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._get_screenshot())
    
    async def _get_screenshot(self):
        """
        Take a screenshot of the current page asynchronously.
        
        Returns:
            bytes: The screenshot as bytes.
        """
        screenshot = await self.page.screenshot()
        return screenshot
    
    def execute_action(self, action):
        """
        Execute a browser action based on the action type.
        
        Args:
            action: The action object from the Computer Use Agent API.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._execute_action(action))
    
    async def _execute_action(self, action):
        """
        Execute a browser action asynchronously.
        
        Args:
            action: The action object from the Computer Use Agent API.
        """
        # Check if this is a computer_call action from the Responses API
        if hasattr(action, 'type') and action.type == "action":
            action_type = action.type.lower()
        else:
            # Handle dictionary format for backward compatibility
            action_type = action.get("type", "").lower()
        
        if action_type == "click":
            await self._click(action)
        elif action_type == "double_click":
            await self._double_click(action)
        elif action_type == "scroll":
            await self._scroll(action)
        elif action_type == "type":
            await self._type(action)
        elif action_type == "keypress":
            await self._keypress(action)
        elif action_type == "wait":
            await self._wait(action)
        elif action_type == "navigate":
            await self.page.goto(action.get("url", self.starting_url))
    
    async def _click(self, action):
        """
        Perform a click action.
        
        Args:
            action: The click action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'x') and hasattr(action, 'y'):
            x = action.x
            y = action.y
            button = getattr(action, 'button', 'left')
        else:
            x = action.get("x", 0)
            y = action.get("y", 0)
            button = action.get("button", "left")
        
        # Map button type
        button_map = {"left": "left", "middle": "middle", "right": "right"}
        button_type = button_map.get(button, "left")
        
        await self.page.mouse.click(x, y, button=button_type)
    
    async def _double_click(self, action):
        """
        Perform a double-click action.
        
        Args:
            action: The double-click action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'x') and hasattr(action, 'y'):
            x = action.x
            y = action.y
        else:
            x = action.get("x", 0)
            y = action.get("y", 0)
        
        await self.page.mouse.dblclick(x, y)
    
    async def _scroll(self, action):
        """
        Perform a scroll action.
        
        Args:
            action: The scroll action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'scroll_x') and hasattr(action, 'scroll_y'):
            dx = action.scroll_x
            dy = action.scroll_y
        else:
            dx = action.get("dx", 0)
            dy = action.get("dy", 0)
        
        await self.page.mouse.wheel(dx, dy)
    
    async def _type(self, action):
        """
        Perform a type action.
        
        Args:
            action: The type action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'text'):
            text = action.text
        else:
            text = action.get("text", "")
        
        await self.page.keyboard.type(text)
    
    async def _keypress(self, action):
        """
        Perform a keypress action.
        
        Args:
            action: The keypress action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'keys'):
            keys = action.keys
            for key in keys:
                await self.page.keyboard.press(key)
        else:
            key = action.get("key", "")
            await self.page.keyboard.press(key)
    
    async def _wait(self, action):
        """
        Perform a wait action.
        
        Args:
            action: The wait action details.
        """
        # Support both object-style and dict-style actions
        if hasattr(action, 'ms'):
            ms = action.ms
        else:
            ms = action.get("ms", 1000)
        
        await asyncio.sleep(ms / 1000)
    
    def navigate(self, url):
        """
        Navigate to a specific URL.
        
        Args:
            url (str): The URL to navigate to.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.page.goto(url))
    
    def close(self):
        """
        Close the browser and clean up resources.
        """
        if self.browser:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._close())
    
    async def _close(self):
        """
        Close the browser asynchronously.
        """
        if self.browser:
            await self.browser.close()
            await self.playwright.stop()
            self.browser = None
            self.context = None
            self.page = None