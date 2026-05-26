from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.calendar.router import router as calendar_router
from app.modules.character.router import router as character_router
from app.modules.goals.router import router as goals_router
from app.modules.guilds.router import router as guilds_router
from app.modules.oracle.router import router as oracle_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(oracle_router, prefix="/oracle", tags=["oracle"])
api_router.include_router(goals_router, prefix="/goals", tags=["goals"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(character_router, prefix="/character", tags=["character"])
api_router.include_router(guilds_router, prefix="/guilds", tags=["guilds"])

