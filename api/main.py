import os
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.exc import IntegrityError
import sentry_sdk
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, UTC
import uuid

from .tasks import run_analysis_task, run_optimization_task
from utils.job_scraper import scrape_job_description
from database.service import DatabaseService

from sqlalchemy.orm import Session
from database.service import DatabaseService
from database.models import AppUser, get_db

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=1.0)

app = FastAPI(title="Resume Enhancer API", version="v1")
db_service = DatabaseService()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

Instrumentator().instrument(app).expose(app)

class AnalysisRequest(BaseModel):
    job_description: str

class AnalysisResponse(BaseModel):
    analysis_id: str
    message: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)): 
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        
        return db_service.get_user_by_username(db, username=username)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@app.post("/users", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        hashed_password = pwd_context.hash(user.password)
        db_user = db_service.create_user(db=db, username=user.username, hashed_password=hashed_password)
        return db_user
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists."
        )

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)): 
    
    user = db_service.authenticate_user(db=db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode({"sub": user.username, "exp": datetime.now(UTC) + access_token_expires}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    job_description: str

@app.post("/v1/scrape-job", response_model=ScrapeResponse)
async def scrape_job(request: ScrapeRequest, current_user: User = Depends(get_current_user)):
    """
    Accepts a URL and returns the scraped job description text.
    """
    logger.info(f"Scraping job URL for user {current_user.username}: {request.url}")
    if not request.url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
    
    try:
        scraped_text = await scrape_job_description(request.url)
        if not scraped_text:
            raise HTTPException(status_code=404, detail="Could not extract a job description from the URL. The content might be dynamic or protected.")
        return ScrapeResponse(job_description=scraped_text)
    except Exception as e:
        logger.error(f"Scraping failed for URL {request.url}: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while scraping: {e}")


@app.post("/v1/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    job_description: str = Form(...),
    resume_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db) 
):
    resume_bytes = await resume_file.read()
    session_id = str(uuid.uuid4())
    analysis = db_service.create_initial_analysis(
        db=db, 
        session_id=session_id,
        user_id=current_user.id,
        original_filename=resume_file.filename,
        job_description=job_description
    )
    run_analysis_task.delay(str(analysis.id), resume_bytes, resume_file.content_type, job_description)
    logger.info(f"Queued analysis {analysis.id} for user {current_user.username}")
    return {"analysis_id": str(analysis.id), "message": "Analysis queued successfully."}

@app.get("/v1/analysis/{analysis_id}")
def get_analysis_results(analysis_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)): 
    results = db_service.get_analysis_by_id(db=db, analysis_id=analysis_id, user_id=current_user.id) 
    if not results:
        raise HTTPException(status_code=404, detail="Analysis not found or unauthorized")
    return results

@app.post("/v1/optimize/{analysis_id}", status_code=status.HTTP_202_ACCEPTED)
def optimize_resume(analysis_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)): 
    analysis = db_service.get_analysis_by_id(db=db, analysis_id=analysis_id, user_id=current_user.id) 
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found or unauthorized")

    run_optimization_task.delay(analysis_id)
    logger.info(f"Queued optimization for analysis {analysis_id} for user {current_user.username}")
    return {"message": "Optimization task queued successfully."}