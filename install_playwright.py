import subprocess
import sys
import os

print("Installing Playwright browsers...")
try:
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"])
    print("✅ Playwright browsers have been installed successfully")
except Exception as e:
    print(f"❌ Error installing Playwright browsers: {e}")
    print("Trying alternate method...")
    try:
        subprocess.check_call(["playwright", "install", "--with-deps", "chromium"])
        print("✅ Playwright browsers have been installed successfully using alternate method")
    except Exception as e2:
        print(f"❌ Error with alternate method: {e2}")
        print("Please try running one of these commands manually:")
        print("  python -m playwright install --with-deps chromium")
        print("  playwright install --with-deps chromium")
        sys.exit(1)

print("\nSetup complete. You can now run the application.")