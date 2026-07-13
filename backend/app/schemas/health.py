from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status payload returned by the monitoring endpoint."""

    status: str = Field(..., example=["healthy"])
    application: str = Field(..., example=["AI Flight Intelligence Platform"])
    version: str = Field(..., example=["1.0.0"])
