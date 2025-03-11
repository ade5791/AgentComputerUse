# Computer Use Agent Streamlit App

This Streamlit application integrates with OpenAI's Computer Use Agent API to automate browser tasks through screenshots and actions.

## Features

- Browser automation using Playwright
- Integration with OpenAI's Computer Use Agent API
- Support for common browser actions:
  - Click
  - Double-click
  - Scroll
  - Type
  - Keypress
  - Wait
- Screenshot capture and processing
- Continuous feedback loop with the API
- Safety check acknowledgment
- Error handling for failed actions
- Configurable browser settings

## Requirements

- Python 3.7+
- OpenAI API key
- Playwright installed and configured

## Setup

1. Install dependencies:
   ```
   pip install streamlit openai playwright pillow
   ```

2. Initialize Playwright:
   ```
   playwright install
   ```

3. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY="your-api-key"
   ```
   Alternatively, you can enter your API key in the application.

## Running the Application

Start the Streamlit app:
