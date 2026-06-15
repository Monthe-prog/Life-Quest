from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.metrics import metrics_middleware, metrics_response
from app.modules.oracle.service import oracle_service


class GenerateRequest(BaseModel):
    prompt: str
    instructions: str | None = None


class BreakdownRequest(BaseModel):
    title: str
    horizon: str
    child_horizon: str


class OracleResultResponse(BaseModel):
    text: str
    provider: str
    degraded: bool
    error: str | None = None


app = FastAPI(
    title="OPERATOR Oracle Service",
    version="0.1.0",
    description="Internal Oracle AI microservice for OPERATOR.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.middleware("http")(metrics_middleware)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "online", "service": "operator-oracle-service"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return metrics_response()


@app.get("/oracle/status", tags=["oracle"])
async def status() -> dict[str, str | bool]:
    return {
        "provider": "openai" if oracle_service.configured else "fallback",
        "configured": oracle_service.configured,
        "model": oracle_service.model_name,
    }


@app.post("/oracle/generate", response_model=OracleResultResponse, tags=["oracle"])
async def generate(payload: GenerateRequest) -> OracleResultResponse:
    result = await oracle_service.generate(payload.prompt, payload.instructions)
    return OracleResultResponse(**result.__dict__)


@app.post("/oracle/breakdown-goal", response_model=OracleResultResponse, tags=["oracle"])
async def breakdown_goal(payload: BreakdownRequest) -> OracleResultResponse:
    result = await oracle_service.breakdown_goal(payload.title, payload.horizon, payload.child_horizon)
    return OracleResultResponse(**result.__dict__)
