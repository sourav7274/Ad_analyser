import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas import AnalyseRequest, AnalyseResponse, ErrorDetail, ErrorResponse
from app.services import AdAnalyserService
from app.metrics import metrics
from app.config import settings

logger = logging.getLogger(__name__)

# Limiter instance — must match the one registered on the app in main.py
limiter = Limiter(key_func=get_remote_address)

health_router = APIRouter()
router = APIRouter(prefix="/api/v1")


@health_router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok"})


@health_router.get("/metrics")
async def get_metrics() -> JSONResponse:
    """Simple in-memory metrics — request counts since last restart."""
    return JSONResponse(status_code=200, content=metrics.snapshot())


def get_service(request: Request) -> AdAnalyserService:
    return request.app.state.service


@router.post("/analyse-ad", response_model=AnalyseResponse)
@limiter.limit(lambda: settings.rate_limit)
async def analyse_ad(
    request: Request,
    body: AnalyseRequest,
    service: AdAnalyserService = Depends(get_service),
) -> AnalyseResponse | JSONResponse:
    request_id = str(uuid.uuid4())
    logger.info("Request received: request_id=%s", request_id)
    metrics.increment("requests.total")
    start = time.perf_counter()
    try:
        data = await service.analyse_ad(body.ad_copy, request_id)
        elapsed = time.perf_counter() - start
        logger.info(
            "Request completed: request_id=%s elapsed=%.4fs", request_id, elapsed
        )
        metrics.increment("requests.success")
        return AnalyseResponse(success=True, request_id=request_id, data=data)
    except HTTPException as exc:
        logger.error(
            "HTTP error: request_id=%s detail=%s", request_id, exc.detail
        )
        metrics.increment(f"requests.error.{exc.status_code}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                request_id=request_id,
                error=ErrorDetail(message=exc.detail),
            ).model_dump(),
        )
    except Exception:
        logger.error("Unexpected error: request_id=%s", request_id)
        metrics.increment("requests.error.500")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                error=ErrorDetail(message="An unexpected error occurred."),
            ).model_dump(),
        )
