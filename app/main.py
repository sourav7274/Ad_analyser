import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.services import AdAnalyserService
from app.routes import router, health_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Rate limiter — keyed by client IP
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])


@asynccontextmanager
async def lifespan(app: FastAPI):
    executor = ThreadPoolExecutor(max_workers=settings.executor_threads)
    app.state.executor = executor
    app.state.service = AdAnalyserService(executor)
    yield
    executor.shutdown(wait=True)


app = FastAPI(title="Ad Analyser API", lifespan=lifespan)

# Attach rate limiter to app state and register 429 handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(router)
app.include_router(health_router)
