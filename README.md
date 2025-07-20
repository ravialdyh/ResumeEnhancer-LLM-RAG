# Resume Enhancer using LLM and RAG

Do you want to align your CV more with your dream job? Just upload your CV and dream job description then we will generate optimized resume for you! This repo leverages Google's Gemini AI model, Retrieval-Augmented Generation (RAG) techniques, and document parsing capabilities to provide intelligent resume analysis and optimization suggestions.

![Resume Enhancer image 1](images/resume-enhancer-1.png)

![Resume Enhancer image 2](images/resume-enhance-2.png)

## Tech Stack Overview

| Category      | Technology / Service                                                                               | Purpose                                                                                                                                              |
| :------------ | :------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Cloud** | Amazon Web Services (AWS)                                                                          | Hosting the entire application infrastructure.                                                                                                       |
| **Database** | AWS RDS for PostgreSQL                                                                             | Provides a managed, persistent SQL database to store user sessions and analysis results.                                                 |
| **Container** | Docker                                                                                             | Packages the Streamlit application, all its dependencies, and static assets (like fonts) into a portable image for consistent deployment. |
| **Registry** | AWS ECR (Elastic Container Registry)                                                               | A private registry to store and manage the application's Docker image.                                                                               |
| **Compute** | AWS EC2 (Elastic Compute Cloud)                                                                    | A virtual server that runs the Docker container, providing direct control over the environment and networking.                                       |
| **Framework** | Streamlit                                                                                          | The Python framework used to build the interactive web application UI.                                                                               |
| **AI** | Google Gemini Flash 2.5                                                                                      | The Large Language Model used for resume analysis and optimization.                                                                      |
| **RAG** | `sentence-transformers`, FAISS                                                                     | Used to create text embeddings and perform similarity searches for the Retrieval-Augmented Generation system.                               |

-----

## Deployment

This details the steps to deploy the application on an AWS EC2 instance.

### 1\. Database Setup

  * **Tech:** AWS RDS, PostgreSQL
  * **Purpose:** The application requires a persistent database to store session data and the results of each resume analysis.
  * **Action:**
    1.  Create a new **PostgreSQL** database instance using **AWS RDS**.
    2.  During setup, define a **Master username**, **Master password**, and an **Initial database name**. Store these credentials securely.
    3.  Configure the RDS instance's **Security Group** to be ready for the EC2 instance connection.

### 2\. Containerization

  * **Tech:** Docker, `requirements.txt`
  * **Purpose:** To create a self-contained, portable image of the application. This ensures that it runs the same way everywhere.
  * **Actions:**
    1.  Create a `Dockerfile` in the project root to define the build steps.
    2.  Create a `.dockerignore` file to exclude secrets (like `.env`) and unnecessary files from the image.
    3.  Modify `requirements.txt` to use the CPU-only version of PyTorch to reduce image size and prevent build errors:
        ```
        --extra-index-url https://download.pytorch.org/whl/cpu
        ...
        torch
        sentence-transformers
        ...
        ```
    4.  Build the Docker image locally, tag it, and push it to a private repository on **AWS ECR**.

### 3\. Compute Setup

  * **Tech:** AWS EC2, Docker
  * **Purpose:** To create a virtual server where the application container will run.
  * **Actions:**
    1.  Launch an **EC2 instance** (e.g., Ubuntu `t2.micro`).
    2.  Create a new **Key Pair** and download the `.pem` file to connect to the instance via SSH.
    3.  Create a new **Security Group** for the EC2 instance and add inbound rules to allow traffic on:
          * **Port 22 (SSH)** from your IP address.
          * **Port 8501 (Custom TCP)** from anywhere (`0.0.0.0/0`).
    4.  Connect to the instance via SSH and install Docker, the AWS CLI, and the PostgreSQL client (`psql`).

### 4\. Final Deployment

  * **Tech:** `psql`, Docker, `ssh`
  * **Purpose:** To connect all the pieces and run the application.
  * **Actions:**
    1.  **Configure Networking:** Add an inbound rule to the **RDS Security Group** to allow PostgreSQL traffic (port 5432) from the **Private IP address** of your EC2 instance.

    2.  **Create the Database:** Connect to your RDS instance from the EC2 terminal using `psql` and run `CREATE DATABASE "your_db_name";` to create the database your application needs.

    3.  **Run the Application:** From the EC2 terminal, pull the latest image from ECR and run the container using the `docker run` command, passing the `GEMINI_API_KEY` and `DATABASE_URL` as environment variables.

        ```bash
        # Command to run the container on the EC2 instance
        docker run -d -p 8501:8501 \
        --env GEMINI_API_KEY="YOUR_API_KEY_HERE" \
        --env DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DB_NAME" \
        YOUR_ECR_IMAGE_URI:latest
        ```