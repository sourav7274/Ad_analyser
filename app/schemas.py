from pydantic import BaseModel, Field


class AnalyseRequest(BaseModel):
    ad_copy: str = Field(..., min_length=1)


class PredictionData(BaseModel):
    impulse_score: float
    trust_score: float
    conversion_probability: float
    model_version: str


class AnalyseResponse(BaseModel):
    success: bool = True
    request_id: str
    data: PredictionData


class ErrorDetail(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    request_id: str
    error: ErrorDetail
