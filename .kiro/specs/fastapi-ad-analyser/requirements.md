# Requirements Document

## Introduction

This feature wraps the existing `mock_model.py` ML inference function (`predict_conversion`) in a production-ready FastAPI backend. The API accepts ad copy text, runs asynchronous model inference, and returns structured prediction scores. The service is containerised with Docker, includes a CI/CD pipeline targeting AWS ECR, and is covered by a pytest test suite. Code is structured into separate modules (routes, schemas, services, config) rather than a single file.

---

## Glossary

- **API**: The FastAPI application that exposes HTTP endpoints to clients.
- **Ad_Analyser_Service**: The internal service layer that calls the ML model and handles business logic.
- **Model**: The `predict_conversion` function in `mock_model.py` that simulates ML inference.
- **Request_Validator**: The Pydantic layer responsible for validating incoming request payloads.
- **Request_ID**: A UUID generated per request used to correlate logs and responses.
- **Executor**: A `ThreadPoolExecutor` used to run the blocking `Model` call without blocking the async event loop.
- **Health_Endpoint**: The `/health` HTTP endpoint that reports service liveness.
- **Analyse_Endpoint**: The `POST /api/v1/analyse-ad` HTTP endpoint that triggers model inference.
- **Logger**: The application-level structured logger attached to each request.
- **Dockerfile**: The container build definition for the API service.
- **CI_Pipeline**: The GitHub Actions workflow defined in `.github/workflows/deploy.yml`.
- **ECR**: Amazon Elastic Container Registry, the target image registry.
- **ASGI_Server**: The production-grade async server (e.g., Uvicorn or Gunicorn+Uvicorn) used to run the API.

---

## Requirements

### Requirement 1: Ad Analysis Endpoint

**User Story:** As a frontend client, I want to POST ad copy text to the API and receive structured prediction scores, so that I can display conversion likelihood to the user.

#### Acceptance Criteria

1. THE `API` SHALL expose a `POST /api/v1/analyse-ad` endpoint.
2. WHEN a valid request body `{ "ad_copy": "<string>" }` is received, THE `Analyse_Endpoint` SHALL return HTTP 200 with the body:
   ```json
   {
     "success": true,
     "request_id": "<uuid>",
     "data": {
       "impulse_score": <float>,
       "trust_score": <float>,
       "conversion_probability": <float>,
       "model_version": "<string>"
     }
   }
   ```
3. THE `Analyse_Endpoint` SHALL include a unique `Request_ID` (UUID v4) in every response, both success and error.
4. WHEN the `ad_copy` field is missing from the request body, THE `Request_Validator` SHALL return HTTP 422 with a descriptive validation error message.

---

### Requirement 2: Asynchronous Model Execution

**User Story:** As a system operator, I want the blocking ML model call to be offloaded from the async event loop, so that the server remains responsive while inference runs.

#### Acceptance Criteria

1. WHEN the `Analyse_Endpoint` receives a valid request, THE `Ad_Analyser_Service` SHALL invoke the `Model` using `asyncio.get_event_loop().run_in_executor` (or `loop.run_in_executor`) with a `ThreadPoolExecutor`, not via a naive `async def` wrapper.
2. WHILE the `Model` is executing in the `Executor`, THE `API` SHALL remain able to accept and begin processing other incoming requests.
3. THE `Ad_Analyser_Service` SHALL await the `Executor` future before constructing the response.

---

### Requirement 3: Error Handling

**User Story:** As a frontend client, I want consistent, structured error responses, so that I can handle failures gracefully without parsing unstructured text.

#### Acceptance Criteria

1. IF the `Model` raises a `ValueError`, THEN THE `Ad_Analyser_Service` SHALL return HTTP 400 with the body:
   ```json
   { "success": false, "request_id": "<uuid>", "error": { "message": "<error detail>" } }
   ```
2. IF the `Model` raises a `RuntimeError`, THEN THE `Ad_Analyser_Service` SHALL return HTTP 500 with the body:
   ```json
   { "success": false, "request_id": "<uuid>", "error": { "message": "<error detail>" } }
   ```
3. THE `API` SHALL include the same `Request_ID` in error responses as was assigned at the start of that request.
4. IF an unexpected exception occurs, THEN THE `API` SHALL return HTTP 500 with a generic error message and SHALL NOT expose internal stack traces to the client.

---

### Requirement 4: Request Validation

**User Story:** As a system operator, I want all incoming payloads validated before reaching the model, so that invalid data never causes unhandled exceptions in the service layer.

#### Acceptance Criteria

1. THE `Request_Validator` SHALL use a Pydantic model to define the request schema for `POST /api/v1/analyse-ad`.
2. THE `Request_Validator` SHALL enforce that `ad_copy` is a non-empty string.
3. WHEN `ad_copy` is present but contains fewer than 10 characters, THE `Request_Validator` SHALL allow the request to pass validation (the `Model` itself enforces the 10-character minimum and raises `ValueError`, which maps to HTTP 400 per Requirement 3).
4. THE `Request_Validator` SHALL use a Pydantic model to define the response schema, ensuring all response fields are typed.

---

### Requirement 5: Health Endpoint

**User Story:** As a DevOps engineer, I want a `/health` endpoint, so that load balancers and container orchestrators can verify the service is alive.

#### Acceptance Criteria

1. THE `API` SHALL expose a `GET /health` endpoint.
2. WHEN the service is running, THE `Health_Endpoint` SHALL return HTTP 200 with the body `{ "status": "ok" }`.
3. THE `Health_Endpoint` SHALL respond within 500ms under normal operating conditions.

---

### Requirement 6: Application Logging

**User Story:** As a system operator, I want structured logs for every request and error, so that I can trace issues using the `Request_ID`.

#### Acceptance Criteria

1. THE `Logger` SHALL emit a log entry at INFO level when a request is received by the `Analyse_Endpoint`, including the `Request_ID`.
2. THE `Logger` SHALL emit a log entry at INFO level when a successful prediction is returned, including the `Request_ID` and response time.
3. IF an error occurs during model inference, THEN THE `Logger` SHALL emit a log entry at ERROR level, including the `Request_ID` and the exception message.
4. THE `Logger` SHALL use Python's standard `logging` module with a consistent format across all modules.

---

### Requirement 7: Code Structure

**User Story:** As a developer, I want the codebase split into separate modules, so that each concern is isolated and the project is maintainable.

#### Acceptance Criteria

1. THE `API` SHALL organise source code into at minimum the following modules: `routes` (HTTP handlers), `schemas` (Pydantic models), `services` (business logic and model calls), and `config` (application settings).
2. THE `API` SHALL NOT define all logic in a single `app.py` file.
3. THE `config` module SHALL load settings (e.g., host, port, log level) from environment variables with documented defaults.
4. THE `routes` module SHALL import from `services` and `schemas`; THE `services` module SHALL NOT import from `routes`.

---

### Requirement 8: Containerisation

**User Story:** As a DevOps engineer, I want a production-ready Dockerfile, so that the service can be deployed consistently across environments.

#### Acceptance Criteria

1. THE `Dockerfile` SHALL use a lightweight base image (e.g., `python:3.11-slim` or equivalent).
2. THE `Dockerfile` SHALL copy and install `requirements.txt` before copying application source code, so that the dependency layer is cached independently.
3. THE `Dockerfile` SHALL run the application as a non-root user.
4. THE `Dockerfile` SHALL use a production `ASGI_Server` (e.g., `uvicorn` with `--workers` or `gunicorn` with a uvicorn worker class) as the container entrypoint.
5. THE `Dockerfile` SHALL expose the application port via the `EXPOSE` instruction.

---

### Requirement 9: CI/CD Pipeline

**User Story:** As a DevOps engineer, I want a GitHub Actions workflow that tests, builds, and pushes the Docker image to ECR, so that deployments are automated and repeatable.

#### Acceptance Criteria

1. THE `CI_Pipeline` SHALL be defined in `.github/workflows/deploy.yml`.
2. THE `CI_Pipeline` SHALL execute the pytest test suite as the first job step; the build step SHALL NOT run if tests fail.
3. THE `CI_Pipeline` SHALL build the Docker image using the project `Dockerfile`.
4. THE `CI_Pipeline` SHALL tag the Docker image with the Git commit SHA.
5. THE `CI_Pipeline` SHALL authenticate to `ECR` using AWS credentials stored as GitHub Actions secrets (placeholder values marked with `# TODO` comments).
6. THE `CI_Pipeline` SHALL push the tagged image to the configured `ECR` repository.

---

### Requirement 10: Test Suite

**User Story:** As a developer, I want a pytest test suite covering the core API behaviours, so that regressions are caught before deployment.

#### Acceptance Criteria

1. THE test suite SHALL include a test that sends a valid `ad_copy` payload to `POST /api/v1/analyse-ad` and asserts HTTP 200, `success: true`, and the presence of all four prediction fields (`impulse_score`, `trust_score`, `conversion_probability`, `model_version`).
2. THE test suite SHALL include a test that sends an `ad_copy` value shorter than 10 characters and asserts HTTP 400 with `success: false`.
3. THE test suite SHALL include a test that sends an `ad_copy` containing `"force_runtime_error"` and asserts HTTP 500 with `success: false`.
4. THE test suite SHALL mock the `Model` (i.e., patch `predict_conversion`) so that tests do not incur the 2–4 second `time.sleep` delay.
5. FOR ALL test cases, THE test suite SHALL assert that the response body contains a non-empty `request_id` field.
6. THE test suite SHALL be runnable with `pytest` from the project root without additional configuration beyond installing dependencies.
