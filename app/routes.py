import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.schemas import AnalyseRequest, AnalyseResponse, ErrorDetail, ErrorResponse
from app.services import AdAnalyserService

logger = logging.getLogger(__name__)

health_router = APIRouter()
router = APIRouter(prefix="/api/v1")


@health_router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok"})


def get_service(request: Request) -> AdAnalyserService:
    return request.app.state.service


@router.post("/analyse-ad", response_model=AnalyseResponse)
async def analyse_ad(
    request: AnalyseRequest,
    service: AdAnalyserService = Depends(get_service),
) -> AnalyseResponse | JSONResponse:
    request_id = str(uuid.uuid4())
    logger.info("Request received: request_id=%s", request_id)
    start = time.perf_counter()
    try:
        data = await service.analyse_ad(request.ad_copy, request_id)
        elapsed = time.perf_counter() - start
        logger.info(
            "Request completed: request_id=%s elapsed=%.4fs", request_id, elapsed
        )
        return AnalyseResponse(success=True, request_id=request_id, data=data)
    except HTTPException as exc:
        logger.error(
            "HTTP error: request_id=%s detail=%s", request_id, exc.detail
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                request_id=request_id,
                error=ErrorDetail(message=exc.detail),
            ).model_dump(),
        )
    except Exception:
        logger.error("Unexpected error: request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                error=ErrorDetail(message="An unexpected error occurred."),
            ).model_dump(),
        )
