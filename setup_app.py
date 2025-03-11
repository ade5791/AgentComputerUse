import subprocess
import sys
import os
import platform
import time

def check_install_dependencies():
    """
    Check and install required dependencies for the application.
    Sets up the environment appropriately for production or development.
    """
    print("Checking and installing dependencies...")
    
    # Define required packages
    required_packages = [
        "streamlit",
        "openai",
        "playwright",
        "Pillow",
        "pandas",
        "matplotlib",
        "altair"
    ]
    
    for package in required_packages:
        try:
            __import__(package.lower())
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} has been installed")
    
    # Check for different environments
    is_replit = os.environ.get("REPL_ID") is not None
    is_docker = os.path.exists("/.dockerenv")
    is_production = os.environ.get("PRODUCTION") == "true"
    
    # Force real browser in production
    if is_production:
        print("🚀 Production environment detected - forcing real browser automation")
        force_real_browser = True
    else:
        force_real_browser = False
    
    playwright_installed = False
    
    # More thorough browser installation for production
    try:
        # Define browser installation paths (different by OS)
        if platform.system() == "Windows":
            playwright_cache = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "ms-playwright")
        elif platform.system() == "Darwin":  # macOS
            playwright_cache = os.path.expanduser("~/Library/Caches/ms-playwright")
        else:  # Linux and others
            playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
        
        missing_browsers = True
        if os.path.exists(playwright_cache) and os.listdir(playwright_cache):
            print("✅ Playwright browser directory exists")
            # Check if chromium is actually installed by looking for browser executable
            chromium_path = os.path.join(playwright_cache, "chromium-")
            # Use glob to find directories starting with chromium-
            import glob
            chromium_dirs = glob.glob(f"{chromium_path}*")
            if chromium_dirs:
                # Check for browser executables in the directories
                for chrome_dir in chromium_dirs:
                    if platform.system() == "Windows":
                        browser_exec = os.path.join(chrome_dir, "chrome.exe")
                    elif platform.system() == "Darwin":  # macOS
                        browser_exec = os.path.join(chrome_dir, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium")
                    else:  # Linux
                        browser_exec = os.path.join(chrome_dir, "chrome-linux", "chrome")
                    
                    if os.path.exists(browser_exec):
                        print(f"✅ Found Chromium browser executable at {browser_exec}")
                        missing_browsers = False
                        playwright_installed = True
                        break
        
        if missing_browsers or force_real_browser:
            print("Installing Playwright browsers (this may take a few minutes)...")
            # Multiple installation attempts with increasing verbosity
            max_attempts = 3 if is_production else 2
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"Installation attempt {attempt}/{max_attempts}...")
                    if attempt == 1:
                        # Standard installation
                        subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
                    elif attempt == 2:
                        # Try with system-level permissions if applicable
                        if platform.system() == "Linux":
                            print("Attempting with sudo...")
                            subprocess.check_call(["sudo", sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
                        else:
                            # Alternative installation for non-Linux platforms
                            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                            print("Installed browser without system dependencies")
                    elif attempt == 3:
                        # Production attempt - try using npm for additional installation paths
                        print("Trying via npm in production environment...")
                        subprocess.check_call(["npm", "install", "-g", "playwright"])
                        subprocess.check_call(["npx", "playwright", "install", "--with-deps", "chromium"])
                    
                    print(f"✅ Playwright browsers successfully installed on attempt {attempt}")
                    playwright_installed = True
                    break
                except Exception as e:
                    print(f"Error on attempt {attempt}: {str(e)}")
                    if attempt < max_attempts:
                        print(f"Waiting before next attempt...")
                        time.sleep(2)  # Short delay between attempts
                    else:
                        print("All installation attempts failed")
                        
                        # Extra options for production
                        if is_production:
                            print("Critical failure: Production requires browser automation")
                            # Exit or use very obvious warning
                            if os.environ.get("FAIL_ON_MISSING_BROWSER") == "true":
                                sys.exit(1)
        else:
            print("✅ Playwright browsers are already installed")
            playwright_installed = True
    except Exception as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        
        if is_production:
            print("⚠️ WARNING: Production environment without browser automation!")
        elif is_replit:
            print("Detected Replit environment - will use mock browser automation")
        else:
            print("Please run 'python -m playwright install --with-deps chromium' manually")
    
    # Create an environment flag file to indicate whether to use mock or real browser
    with open('.browser_env', 'w') as f:
        # Always use real browser in production, regardless of installation status
        if is_production:
            f.write("real")
            print("🚀 Production environment: Using real browser automation")
        # Fall back to mock in Replit only when browser installation failed
        elif is_replit and not playwright_installed:
            f.write("mock")
            print("⚠️ Development environment: Using mock browser automation")
        # Use real browser in all other cases
        else:
            f.write("real")
            print("✅ Using real browser automation")

def get_browser_environment():
    """
    Get the browser environment type (mock or real).
    
    Returns:
        str: 'mock' or 'real'
    """
    # Production always uses real browsers
    if os.environ.get("PRODUCTION") == "true":
        return 'real'
        
    try:
        with open('.browser_env', 'r') as f:
            env = f.read().strip()
            return env if env in ['mock', 'real'] else 'mock'
    except:
        # If file doesn't exist or can't be read, check if we're in Replit
        is_replit = os.environ.get("REPL_ID") is not None
        return 'mock' if is_replit else 'real'

if __name__ == "__main__":
    check_install_dependencies()
    print("\nSetup complete. You can now run 'streamlit run app.py' to start the application.")