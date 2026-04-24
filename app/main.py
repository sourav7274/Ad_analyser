import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.services import AdAnalyserService
from app.routes import router, health_router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    executor = ThreadPoolExecutor(max_workers=settings.executor_threads)
    app.state.executor = executor
    app.state.service = AdAnalyserService(executor)
    yield
    executor.shutdown(wait=True)


app = FastAPI(title="Ad Analyser API", lifespan=lifespan)

app.include_router(router)
app.include_router(health_router)
