from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.metrics import metrics_middleware, metrics_response
from app.core.settings import get_settings
from app.ws.router import router as websocket_router

settings = get_settings()

app = FastAPI(
    title="OPERATOR API",
    version="0.1.0",
    description="Backend API for the OPERATOR life-management platform.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(metrics_middleware)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "online", "service": "operator-backend"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return metrics_response()


app.include_router(api_router, prefix="/api")
app.include_router(websocket_router, prefix="/ws")
