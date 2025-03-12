# Computer Use Agent Application

A full-stack application that leverages OpenAI's Computer Use Agent API to automate browser tasks through intelligent screenshot analysis and action generation.

## Features

- **Streamlit Interface**: User-friendly dashboard for task management and visualization
- **REST API**: Backend API for programmatic access to automation features
- **Browser Automation**: Real-time browser control using Playwright
- **Production-Ready**: Docker containerization for cloud deployment
- **Mock Fallback**: Development environment with fallback mock browser for testing
- **Session Management**: Track, save, and share automation sessions
- **Visualization**: Dashboard for analytics and session tracking

### Supported Browser Actions
- Click and double-click
- Typing and keypresses
- Scrolling
- Navigation
- Waiting
- Advanced DOM interaction

## Architecture

- **Frontend**: Streamlit dashboard on port 5000
- **Backend**: FastAPI REST endpoints on port 5001
- **Browser**: Playwright for real browser automation
- **Mock System**: Environment-adaptive fallback for constrained environments

## Local Development

### Requirements
- Python 3.9+
- OpenAI API key
- Playwright (installed automatically)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/computer-use-agent-app.git
   cd computer-use-agent-app
   ```

2. Install dependencies:
   ```
   pip install -r docker-requirements.txt
   ```

3. Set your OpenAI API key:
   ```
   export OPENAI_API_KEY="your-api-key"
   ```

4. Start the application:
   ```
   python setup_app.py
   streamlit run app.py
   ```
   In a separate terminal:
   ```
   python api.py
   ```

## Docker Deployment

1. Build the Docker image:
   ```
   docker build -t browser-automation-app .
   ```

2. Run the container:
   ```
   docker run -p 5000:5000 -p 5001:5001 -e OPENAI_API_KEY="your-api-key" -e PRODUCTION=true browser-automation-app
   ```

## Google Cloud Deployment

This project comes with built-in CI/CD configuration for deployment to Google Cloud Run.

### Prerequisites

1. Google Cloud Platform account
2. Google Cloud SDK installed
3. GitHub repository set up

### Setup Steps

1. Create a Google Cloud Project and enable required APIs:
   ```
   gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com
   ```

2. Create a Secret for your OpenAI API key:
   ```
   echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
   ```

3. Create a Service Account for GitHub Actions:
   ```
   gcloud iam service-accounts create github-actions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. Add GitHub Secrets:
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: The contents of the `key.json` file (as a base64-encoded string)

5. Push to GitHub:
   ```
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

The application will automatically deploy to Google Cloud Run whenever changes are pushed to the main branch.

## Running the Application

Once deployed, you can access:
- Streamlit UI: https://browser-automation-app-[unique-id].run.app
- API endpoints: https://browser-automation-app-[unique-id].run.app/api/health
# AgentComputerUse
