import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from mock_model import predict_conversion
from app.schemas import PredictionData
from app.config import settings


class AdAnalyserService:
    def __init__(self, executor: ThreadPoolExecutor):
        self._executor = executor

    async def analyse_ad(self, ad_copy: str, request_id: str) -> PredictionData:
        loop = asyncio.get_event_loop()
        timeout = settings.model_timeout if settings.model_timeout > 0 else None
        try:
            future = loop.run_in_executor(
                self._executor, predict_conversion, ad_copy
            )
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"Model inference timed out after {timeout}s.",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception:
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred."
            )
        return PredictionData(**result)
