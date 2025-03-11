import subprocess
import sys
import os
import platform

def check_install_dependencies():
    """
    Check and install required dependencies for the application.
    """
    print("Checking and installing dependencies...")
    
    # Define required packages
    required_packages = [
        "streamlit",
        "openai",
        "playwright",
        "Pillow"
    ]
    
    for package in required_packages:
        try:
            __import__(package.lower())
            print(f"✅ {package} is already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} has been installed")
    
    # Check if we are in a Replit environment
    is_replit = os.environ.get("REPL_ID") is not None
    playwright_installed = False
    
    # Check if playwright browsers are installed
    try:
        # Check if the browser directory exists
        playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
        if not os.path.exists(playwright_cache) or not os.listdir(playwright_cache):
            print("Installing Playwright browsers...")
            try:
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
                print("✅ Playwright browsers have been installed")
                playwright_installed = True
            except Exception as e:
                print(f"Error installing browsers with Python module: {e}")
                # Try alternative install method
                try:
                    subprocess.check_call(["playwright", "install", "--with-deps", "chromium"])
                    print("✅ Playwright browsers have been installed with CLI method")
                    playwright_installed = True
                except Exception as e2:
                    print(f"Error installing browsers with CLI: {e2}")
                    if is_replit:
                        print("Detected Replit environment - will use mock browser automation")
                    else:
                        print("Please run 'python -m playwright install --with-deps chromium' manually")
        else:
            print("✅ Playwright browsers are already installed")
            playwright_installed = True
    except Exception as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        if is_replit:
            print("Detected Replit environment - will use mock browser automation")
        else:
            print("Please run 'python -m playwright install --with-deps chromium' manually")
    
    # Create an environment flag file to indicate whether to use mock or real browser
    with open('.browser_env', 'w') as f:
        if is_replit and not playwright_installed:
            f.write("mock")
            print("⚠️ Using mock browser automation for this environment")
        else:
            f.write("real")
            print("✅ Using real browser automation")

def get_browser_environment():
    """
    Get the browser environment type (mock or real).
    
    Returns:
        str: 'mock' or 'real'
    """
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