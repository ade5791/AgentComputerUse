import base64
import time
import functools

def get_screenshot_as_base64(browser):
    """
    Get a screenshot from the browser and encode it as base64.
    
    Args:
        browser: The BrowserAutomation instance.
        
    Returns:
        str: The base64-encoded screenshot.
    """
    screenshot = browser.get_screenshot()
    return base64.b64encode(screenshot).decode('utf-8')

def retry_with_backoff(func, max_retries=3, initial_wait=1):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: The function to retry.
        max_retries (int): The maximum number of retries.
        initial_wait (int): The initial wait time in seconds.
        
    Returns:
        Any: The result of the function if successful.
        
    Raises:
        Exception: The last exception that occurred if all retries fail.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        wait_time = initial_wait
        last_exception = None
        
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retries += 1
                
                if retries >= max_retries:
                    break
                    
                # Exponential backoff with jitter
                wait_time = wait_time * 2
                time.sleep(wait_time)
        
        raise last_exception
    
    return wrapper