# Ad Analyser API

A production-ready FastAPI service that wraps `mock_model.py`'s `predict_conversion` function to score advertising copy for conversion potential. Each request is processed asynchronously via a `ThreadPoolExecutor`, and every response — success or error — carries a UUID `request_id` for traceability.

## Prerequisites

- Python 3.11+
- Docker
- Docker Compose
- Make

## Local Setup

Install dependencies and start the development server:

```bash
make install
make run
```

The API will be available at `http://localhost:8000`.

## Running Tests

```bash
make test
```

This runs the full test suite under `tests/`, including unit tests and Hypothesis property-based tests.

## Docker Usage

Build the image and start the service with Docker Compose:

```bash
make build
make up
```

The service will be available at `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/api/v1/analyse-ad` | Analyse ad copy and return conversion scores |

### POST /api/v1/analyse-ad

**Request body:**

```json
{
  "ad_copy": "Your advertisement text here"
}
```

**Success response (HTTP 200):**

```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "impulse_score": 0.82,
    "trust_score": 0.74,
    "conversion_probability": 0.68,
    "model_version": "v1.0"
  }
}
```

**Error response (HTTP 400 / 500):**

```json
{
  "success": false,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": {
    "message": "ad_copy must be at least 10 characters"
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host address the server binds to |
| `PORT` | `8000` | Port the server listens on |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `WORKERS` | `1` | Number of Uvicorn worker processes |
| `EXECUTOR_THREADS` | `4` | Size of the `ThreadPoolExecutor` for model inference |

## CI/CD

A GitHub Actions workflow is defined in `.github/workflows/deploy.yml`. It triggers on every push to `main` and runs the following steps:

1. Checkout code
2. Set up Python 3.11 and install dependencies
3. Run `pytest tests/` — the pipeline stops here if any test fails
4. Configure AWS credentials (requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` secrets in the repository settings)
5. Log in to Amazon ECR
6. Build and tag the Docker image with the commit SHA
7. Push the image to ECR

To use the pipeline, add the required AWS secrets to your GitHub repository under **Settings → Secrets and variables → Actions**.
