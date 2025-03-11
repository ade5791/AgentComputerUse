FROM python:3.11-slim

WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

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

# Expose the port Streamlit will run on
EXPOSE 5000

# Command to run the application
CMD ["streamlit", "run", "app.py"]