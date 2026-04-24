# Implementation Plan: FastAPI Ad Analyser

## Overview

Build a production-ready FastAPI service that wraps `mock_model.py`'s `predict_conversion` function. The implementation follows a foundation-first approach: scaffold the app skeleton and health endpoint, then add the core analyse endpoint with async execution, error handling, and logging, then add the test suite, and finally add Docker and CI/CD artifacts.

All blocking model calls are offloaded to a `ThreadPoolExecutor` via `loop.run_in_executor`. Every response — success or error — shares the same envelope shape with a UUID `request_id`. Tests always mock `predict_conversion` to avoid the 2–4 second sleep.

---

## Tasks

- [x] 1. Project scaffold and configuration module
  - Create the `app/` package directory with an empty `__init__.py`
  - Create `app/config.py` using `os.getenv` to load `HOST` (default `"0.0.0.0"`), `PORT` (default `8000`), `LOG_LEVEL` (default `"INFO"`), `WORKERS` (default `1`), and `EXECUTOR_THREADS` (default `4`); expose a module-level `settings` singleton
  - Create `requirements.txt` listing `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`, `hypothesis`
  - _Requirements: 7.1, 7.3_

- [ ] 2. Pydantic schemas
  - [x] 2.1 Implement request and response schemas in `app/schemas.py`
    - `AnalyseRequest(BaseModel)` with `ad_copy: str = Field(..., min_length=1)`
    - `PredictionData(BaseModel)` with `impulse_score`, `trust_score`, `conversion_probability` (all `float`) and `model_version` (`str`)
    - `AnalyseResponse(BaseModel)` with `success: bool = True`, `request_id: str`, `data: PredictionData`
    - `ErrorDetail(BaseModel)` with `message: str`
    - `ErrorResponse(BaseModel)` with `success: bool = False`, `request_id: str`, `error: ErrorDetail`
    - _Requirements: 1.2, 3.1, 3.2, 4.1, 4.2, 4.4_

  - [x] 2.2 Write unit tests for schema validation
    - Test that `AnalyseRequest` rejects an empty string (422 path)
    - Test that `AnalyseRequest` accepts a single-character string (passes Pydantic, fails model)
    - Test that `AnalyseResponse` and `ErrorResponse` serialise to the expected JSON shapes
    - _Requirements: 4.1, 4.2_

- [ ] 3. Service layer with async executor
  - [x] 3.1 Implement `AdAnalyserService` in `app/services.py`
    - Accept a `ThreadPoolExecutor` in `__init__`
    - Implement `async def analyse_ad(self, ad_copy: str, request_id: str) -> PredictionData`
    - Use `loop = asyncio.get_event_loop(); result = await loop.run_in_executor(self._executor, predict_conversion, ad_copy)` — not a naive `async def` wrapper
    - Map `ValueError` → raise `HTTPException(status_code=400, detail=str(e))`
    - Map `RuntimeError` → raise `HTTPException(status_code=500, detail=str(e))`
    - Map any other `Exception` → raise `HTTPException(status_code=500, detail="An unexpected error occurred.")`
    - `services.py` MUST NOT import from `routes.py`
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.4, 7.4_

  - [x] 3.2 Write unit tests for the service layer
    - Patch `app.services.predict_conversion` with `unittest.mock.patch`
    - Test happy path: mock returns valid dict → `analyse_ad` returns `PredictionData`
    - Test `ValueError` from mock → service raises `HTTPException` with status 400
    - Test `RuntimeError` from mock → service raises `HTTPException` with status 500
    - Test unexpected `Exception` from mock → service raises `HTTPException` with status 500 and generic message
    - _Requirements: 2.1, 3.1, 3.2, 3.4_

- [ ] 4. Application entry point and health endpoint
  - [x] 4.1 Implement `app/main.py`
    - Create the `FastAPI` app instance with `title="Ad Analyser API"`
    - Implement an `asynccontextmanager` lifespan that creates a `ThreadPoolExecutor(max_workers=settings.executor_threads)`, stores it on `app.state`, instantiates `AdAnalyserService`, and calls `executor.shutdown(wait=True)` on teardown
    - Register the analyse router and health router
    - Configure `logging.basicConfig` using `settings.log_level` with a consistent format
    - _Requirements: 7.1, 7.2, 6.4_

  - [x] 4.2 Implement the health endpoint in `app/routes.py`
    - Add `GET /health` returning `{"status": "ok"}` with HTTP 200
    - _Requirements: 5.1, 5.2_

  - [x] 4.3 Write unit tests for the health endpoint in `tests/test_health.py`
    - `test_health_ok`: assert HTTP 200 and body `{"status": "ok"}`
    - `test_health_response_time`: assert response time < 500 ms
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 5. Checkpoint — foundation verified
  - Ensure all tests written so far pass with `pytest tests/ -x`; ask the user if any questions arise before continuing.

- [ ] 6. Analyse endpoint with logging
  - [x] 6.1 Implement `POST /api/v1/analyse-ad` in `app/routes.py`
    - Create `APIRouter(prefix="/api/v1")` and add the `POST /analyse-ad` handler
    - Generate `request_id = str(uuid.uuid4())` at the top of the handler
    - Inject `AdAnalyserService` via `Depends` (resolve from `request.app.state`)
    - Log at INFO on request received (include `request_id`)
    - `await service.analyse_ad(request.ad_copy, request_id)` inside a `try` block
    - On success: log at INFO with `request_id` and elapsed time; return `AnalyseResponse`
    - On `HTTPException`: log at ERROR with `request_id` and `exc.detail`; return `JSONResponse` with `ErrorResponse` body
    - On bare `Exception`: log at ERROR with `request_id`; return `JSONResponse(status_code=500)` with generic `ErrorResponse` — no stack trace in response body
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 6.1, 6.2, 6.3_

  - [x] 6.2 Write unit tests for the analyse endpoint in `tests/test_analyse.py`
    - Use `TestClient` from `conftest.py` with `predict_conversion` patched
    - `test_valid_ad_copy`: POST valid payload → HTTP 200, `success: true`, all four prediction fields present with correct types, non-empty `request_id`
    - `test_missing_ad_copy`: POST `{}` → HTTP 422
    - `test_empty_ad_copy`: POST `{"ad_copy": ""}` → HTTP 422
    - `test_short_ad_copy`: POST `{"ad_copy": "short"}` → HTTP 400, `success: false`, non-empty `request_id`
    - `test_runtime_error`: POST `{"ad_copy": "force_runtime_error trigger"}` → HTTP 500, `success: false`, non-empty `request_id`
    - `test_unexpected_error`: patch service to raise bare `Exception` → HTTP 500, body does not contain stack trace
    - _Requirements: 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 10.1, 10.2, 10.3, 10.5_

- [ ] 7. Test infrastructure and conftest
  - [x] 7.1 Create `tests/conftest.py`
    - Create a `pytest` fixture that patches `app.services.predict_conversion` for the entire test session with a deterministic mock return value: `{"impulse_score": 0.75, "trust_score": 0.5, "conversion_probability": 0.6, "model_version": "v1.0-mock"}`
    - Create a `client` fixture that returns a `TestClient` wrapping the FastAPI app (import from `app.main`)
    - Add `pytest.ini` (or `[tool.pytest.ini_options]` in `pyproject.toml`) setting `testpaths = tests`
    - _Requirements: 10.4, 10.6_

  - [x] 7.2 Create `tests/__init__.py` (empty, makes `tests/` a package)
    - _Requirements: 10.6_

- [ ] 8. Property-based tests
  - [x] 8.1 Create `tests/test_properties.py` and implement Property 1
    - **Property 1: Valid request always produces a well-formed success response**
    - Use `@given(st.text(min_size=10).filter(lambda s: "force_runtime_error" not in s.lower()))` with `@settings(max_examples=100)`
    - Assert HTTP 200, `success: true`, all four prediction fields present with correct types, `request_id` is a non-empty UUID v4 string
    - Tag: `# Feature: fastapi-ad-analyser, Property 1: Valid request always produces a well-formed success response`
    - **Validates: Requirements 1.2, 1.3, 10.1**

  - [x] 8.2 Implement Property 2 in `tests/test_properties.py`
    - **Property 2: Every response always contains a valid UUID request_id**
    - Use `@given(st.one_of(st.text(min_size=10).filter(...), st.text(min_size=1, max_size=9), st.just("force_runtime_error trigger")))` with `@settings(max_examples=100)`
    - Assert `request_id` is present in the response body and is a non-empty, valid UUID v4 string for all three input categories
    - Tag: `# Feature: fastapi-ad-analyser, Property 2: Every response always contains a valid UUID request_id`
    - **Validates: Requirements 1.3, 3.3, 10.5**

  - [x] 8.3 Implement Property 3 in `tests/test_properties.py`
    - **Property 3: Short ad_copy always produces a well-formed HTTP 400 error response**
    - Use `@given(st.text(min_size=1, max_size=9))` with `@settings(max_examples=100)`
    - Assert HTTP 400, `success: false`, non-empty `request_id`, non-empty `error.message`
    - Tag: `# Feature: fastapi-ad-analyser, Property 3: Short ad_copy always produces a well-formed HTTP 400 error response`
    - **Validates: Requirements 3.1, 4.3, 10.2**

  - [x] 8.4 Implement Property 4 in `tests/test_properties.py`
    - **Property 4: Every valid request produces INFO log entries containing the request_id**
    - Use `@given(st.text(min_size=10).filter(lambda s: "force_runtime_error" not in s.lower()))` with `@settings(max_examples=100)`
    - Capture log records using `caplog` (pytest fixture) or `unittest.mock` on the logger; assert at least two INFO-level entries both contain the `request_id` from the response
    - Tag: `# Feature: fastapi-ad-analyser, Property 4: Every request produces INFO log entries containing the request_id`
    - **Validates: Requirements 6.1, 6.2**

- [x] 9. Checkpoint — full test suite green
  - Run `pytest tests/ -x` and ensure all example-based and property-based tests pass; ask the user if any questions arise before continuing.

- [x] 10. Dockerfile
  - Create `Dockerfile` using `python:3.11-slim` as the base image
  - Copy and install `requirements.txt` before copying application source (preserves layer cache)
  - Copy the `app/` directory and `mock_model.py` into the image
  - Create a non-root user `appuser` and switch to it with `USER appuser`
  - `EXPOSE 8000`
  - Set `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]`
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 11. GitHub Actions CI/CD pipeline
  - Create `.github/workflows/deploy.yml`
  - Define a single job `test-build-push` triggered on `push` to `main`
  - Step 1: Checkout code
  - Step 2: Set up Python 3.11 and install dependencies from `requirements.txt`
  - Step 3: Run `pytest tests/` — the build MUST NOT proceed if this step fails
  - Step 4: Configure AWS credentials using `aws-actions/configure-aws-credentials` with secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (add `# TODO` comments for placeholder values)
  - Step 5: Login to ECR using `aws-actions/amazon-ecr-login`
  - Step 6: Build Docker image and tag with `${{ github.sha }}`
  - Step 7: Push tagged image to `ECR_REPOSITORY` (add `# TODO` comment for the repository URI)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 12. Bonus artifacts
  - [x] 12.1 Create `docker-compose.yml`
    - Define a single `api` service that builds from the local `Dockerfile`, maps port `8000:8000`, and passes `LOG_LEVEL` as an environment variable
  - [x] 12.2 Create `Makefile`
    - Targets: `install` (pip install), `run` (uvicorn dev server), `test` (pytest), `build` (docker build), `up` (docker-compose up)
  - [x] 12.3 Create `README.md`
    - Document: project overview, prerequisites, local setup (`make install && make run`), running tests (`make test`), Docker usage (`make build && make up`), environment variables, and CI/CD notes

- [x] 13. Final checkpoint — end-to-end verification
  - Run `pytest tests/ -v` and confirm all tests pass with no warnings; ask the user if any questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- `mock_model.py` at the workspace root MUST NOT be modified
- All tests MUST patch `app.services.predict_conversion` to avoid the 2–4 second sleep
- Property tests use Hypothesis with `max_examples=100`; each property is its own sub-task for independent execution
- The executor is created once at app startup (lifespan) and shut down cleanly on teardown — never create it per-request
- `services.py` MUST NOT import from `routes.py` (enforced by the module dependency graph)
- For production scale-out, swap `uvicorn` CMD to `gunicorn -k uvicorn.workers.UvicornWorker`
