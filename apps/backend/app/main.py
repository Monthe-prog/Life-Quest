from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.settings import get_settings
from app.ws.router import router as websocket_router

settings = get_settings()

app = FastAPI(
    title="OPERATOR API",
    version="0.1.0",
    description="Backend API for the OPERATOR life-management platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "online", "service": "operator-backend"}


app.include_router(api_router, prefix="/api")
app.include_router(websocket_router, prefix="/ws")
