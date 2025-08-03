# End to End Resume Aligner (LLM + RAG) with Restful API

Do you want to make your resume a perfect match for your dream job? Just upload your resume and the job description, and this app will use AI to create an optimized version for you\!

### Video Demo

![Resume Aligner Demo GIF](images/demo_project.gif)

-----

This project uses Google's powerful Gemini AI model, Retrieval-Augmented Generation (RAG), and a modern RESTful API architecture to give you smart suggestions for improving your resume.

-----

## 🛠️ Tech Stack

This project uses a combination of modern technologies to deliver a full-stack AI experience.

| Category | Technology / Service | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | To build the beautiful and interactive web user interface. |
| **Backend** | FastAPI | To create a fast, modern, and reliable RESTful API. |
| **Database** | PostgreSQL | To store all user data, analysis tasks, and results permanently. |
| **Async Tasks** | Celery & Redis | To run heavy AI analysis in the background without slowing down the website. |
| **AI Model** | Google Gemini | The large language model that analyzes and rewrites the resume content. |
| **RAG System**| `sentence-transformers`, FAISS | To create text embeddings and find the most relevant skills. |
| **Containerization**| Docker & Docker Compose | To package the entire application for easy setup and deployment. |
| **Web Scraping**| Playwright | To automatically scrape job descriptions from LinkedIn URLs. |
| **Deployment** | Amazon Web Services (AWS) | The application is designed to be easily deployed on the cloud. |

-----

## 🚀 Running the Project Locally

You can run this entire application on your own computer using Docker. It's very easy\!

### Prerequisites

  * **Docker** and **Docker Compose**: Make sure you have them installed on your computer.
  * **Git**: To copy the project files.
  * **Google Gemini API Key**: You need an API key from Google AI Studio.

### Step 1: Clone the Project

Open your terminal and run this command to get the code:

```bash
git clone https://github.com/your-username/ResumeEnhancer-LLM-RAG.git
cd ResumeEnhancer-LLM-RAG
```

### Step 2: Create Your Environment File

The project needs an environment file to store secret keys.

1.  Create a new file named `.env` in the main project folder.
2.  Copy the content below and paste it into your new `.env` file.

<!-- end list -->

```env
# REQUIRED
# Get your API key from Google AI Studio (https://aistudio.google.com/)
GEMINI_API_KEY="YOUR_GOOGLE_API_KEY_HERE"

# DO NOT CHANGE
# Secret key for user authentication tokens
JWT_SECRET="168b91157c7932822a9a83411a7a275494c2c544d65691038166946a15e61294"

# Local Database Settings
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=resumedb
DATABASE_URL="postgresql://user:password@db:5432/resumedb"

# Local API Settings for Frontend
API_BASE_URL=http://backend:8000

# Celery & Redis Settings
CELERY_BROKER_URL="redis://redis:6379/0"
CELERY_RESULT_BACKEND="redis://redis:6379/0"

# Optional: For error tracking
SENTRY_DSN=
```

3.  **Important**: Replace `"YOUR_GOOGLE_API_KEY_HERE"` with your actual Gemini API key.

### Step 3: Build and Run the Application

Now, run this single command in your terminal. It will build the Docker images and start all the services (frontend, backend, database, etc.).

```bash
docker compose up --build
```

The `--build` flag is important for the first time you run it. Wait for a few minutes for everything to download and start up. You will see a lot of logs in your terminal.

### Step 4: Open the Application

Once the services are running, open your web browser and go to:

**http://localhost:8501**

That's it\! You can now use the Resume Enhancer on your local machine.

-----

## ☁️ Deployment

This application is built with Docker Compose, which makes it ready for cloud deployment. You can deploy it to any cloud provider that supports Docker, like AWS, Google Cloud, or Azure. The main steps would involve:

1.  Setting up a virtual server (like **AWS EC2**).
2.  Using a managed database service (like **AWS RDS for PostgreSQL**).
3.  Storing the Docker images in a private registry (like **AWS ECR**).
4.  Running the application using `docker-compose.yml` on the server.