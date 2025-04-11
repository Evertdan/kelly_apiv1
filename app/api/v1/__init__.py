from fastapi import APIRouter
from app.api.v1.endpoints import chat, status

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(status.router, prefix="/status", tags=["status"])