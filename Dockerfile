FROM python:3.11-bullseye

WORKDIR /app

# Set production environment flag
ENV PRODUCTION=true
ENV FAIL_ON_MISSING_BROWSER=true

# Install necessary system dependencies including browser requirements
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    libappindicator3-1 \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

# Install Playwright with thorough browser setup
RUN python -m playwright install chromium --with-deps
# Verify browser installation or fail
RUN python -c "from playwright.sync_api import sync_playwright; \
    with sync_playwright() as p: \
        browser = p.chromium.launch(); \
        page = browser.new_page(); \
        page.goto('about:blank'); \
        print('Playwright browser verification successful'); \
        browser.close()"

# Copy application files
COPY . .

# Setup Streamlit config
RUN mkdir -p /root/.streamlit
RUN echo "\
[server]\n\
headless = true\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
address = '0.0.0.0'\n\
port = 5000\n\
" > /root/.streamlit/config.toml

# Expose the Streamlit and API ports
EXPOSE 5000
EXPOSE 5001

# Create a startup script that runs both servers
RUN echo '#!/bin/bash\n\
# Run API server in background\n\
python api.py & \n\
# Setup DISPLAY for Xvfb (headless browser support)\n\
Xvfb :99 -screen 0 1280x720x24 &\n\
export DISPLAY=:99\n\
# Run the Streamlit app\n\
exec streamlit run app.py\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]