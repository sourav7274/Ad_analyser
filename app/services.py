import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from mock_model import predict_conversion
from app.schemas import PredictionData
from app.config import settings

logger = logging.getLogger(__name__)


class AdAnalyserService:
    def __init__(self, executor: ThreadPoolExecutor):
        self._executor = executor

    async def analyse_ad(self, ad_copy: str, request_id: str) -> PredictionData:
        loop = asyncio.get_event_loop()
        timeout = settings.model_timeout if settings.model_timeout > 0 else None
        max_attempts = 1 + max(0, settings.model_retries)  # 1 initial + N retries

        last_runtime_error: RuntimeError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                future = loop.run_in_executor(
                    self._executor, predict_conversion, ad_copy
                )
                result = await asyncio.wait_for(future, timeout=timeout)
                return PredictionData(**result)

            except asyncio.TimeoutError:
                # Timeout is not retried — fail fast
                raise HTTPException(
                    status_code=504,
                    detail=f"Model inference timed out after {timeout}s.",
                )

            except ValueError as e:
                # Input validation error — not retried
                raise HTTPException(status_code=400, detail=str(e))

            except RuntimeError as e:
                last_runtime_error = e
                if attempt < max_attempts:
                    backoff = 0.5 * attempt  # 0.5s, 1.0s, ...
                    logger.warning(
                        "Model RuntimeError on attempt %d/%d for request_id=%s — "
                        "retrying in %.1fs: %s",
                        attempt, max_attempts, request_id, backoff, e,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Model RuntimeError after %d attempt(s) for request_id=%s: %s",
                        max_attempts, request_id, e,
                    )

            except Exception:
                # Unexpected error — not retried
                raise HTTPException(
                    status_code=500, detail="An unexpected error occurred."
                )

        # All retries exhausted — raise the last RuntimeError as HTTP 500
        raise HTTPException(
            status_code=500,
            detail=str(last_runtime_error),
        )
