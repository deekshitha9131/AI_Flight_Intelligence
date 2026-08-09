from fastapi import APIRouter
from app.presentation.api.v1.routers import auth, emails, gmail, health, threads

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(gmail.router)
api_router.include_router(emails.router)
api_router.include_router(threads.router)