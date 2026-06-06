from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.calendar.router import router as calendar_router
from app.modules.character.router import router as character_router
from app.modules.goals.router import router as goals_router
from app.modules.guilds.router import router as guilds_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.oracle.router import router as oracle_router
from app.modules.quests.router import router as quests_router
from app.modules.weekly_reviews.router import router as weekly_reviews_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(oracle_router, prefix="/oracle", tags=["oracle"])
api_router.include_router(goals_router, prefix="/goals", tags=["goals"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(character_router, prefix="/character", tags=["character"])
api_router.include_router(guilds_router, prefix="/guilds", tags=["guilds"])
api_router.include_router(weekly_reviews_router, prefix="/weekly-reviews", tags=["weekly-reviews"])
api_router.include_router(quests_router, prefix="/quests", tags=["quests"])
