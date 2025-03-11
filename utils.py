import base64
import time

def get_screenshot_as_base64(browser):
    """
    Get a screenshot from the browser and encode it as base64.
    
    Args:
        browser: The BrowserAutomation instance.
        
    Returns:
        str: The base64-encoded screenshot.
    """
    if not browser:
        raise ValueError("Browser is not initialized")
    
    try:
        # Take a screenshot with the browser
        screenshot_bytes = browser.get_screenshot()
        
        # Encode the screenshot as base64
        return base64.b64encode(screenshot_bytes).decode('utf-8')
    except Exception as e:
        raise Exception(f"Failed to get screenshot: {str(e)}")

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
    retries = 0
    wait_time = initial_wait
    last_exception = None
    
    while retries < max_retries:
        try:
            return func()
        except Exception as e:
            last_exception = e
            retries += 1
            
            if retries >= max_retries:
                break
                
            # Wait with exponential backoff
            time.sleep(wait_time)
            wait_time *= 2
    
    raise last_exception
