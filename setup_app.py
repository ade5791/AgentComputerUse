import subprocess
import sys
import os

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
    
    # Check if playwright browsers are installed
    try:
        # Check if the browser directory exists
        playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
        if not os.path.exists(playwright_cache) or not os.listdir(playwright_cache):
            print("Installing Playwright browsers...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("✅ Playwright browsers have been installed")
        else:
            print("✅ Playwright browsers are already installed")
    except Exception as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        print("Please run 'python -m playwright install chromium' manually")

if __name__ == "__main__":
    check_install_dependencies()
    print("\nSetup complete. You can now run 'streamlit run app.py' to start the application.")