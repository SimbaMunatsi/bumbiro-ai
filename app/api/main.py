import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings 
from app.api.dependencies import get_rag_pipeline

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT

from fastapi import FastAPI
from app.api.routes import router as rag_router
from app.api.auth import router as auth_router
from app.core.database import engine, Base
from app.models.user import User
from app.models.chat import ChatMessage

# --- NEW: Build the User Database Tables ---
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server booting up: Pre-warming BumbiroAI pipeline...")
    get_rag_pipeline()
    print("BumbiroAI is fully indexed and ready to receive traffic!")
    yield
    print("Shutting down BumbiroAI...")

app = FastAPI(
    title="BUMBIRO API",
    version="1.0",
    lifespan=lifespan
)

# --- NEW: Include both routers ---
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(rag_router, tags=["RAG Chat"])