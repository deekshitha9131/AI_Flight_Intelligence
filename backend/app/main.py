from fastapi import FastAPI, Request, Response
from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.flight import router as flight_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.conversation import router as conversation_router
from app.api.v1.predictions import router as prediction_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.favourites import router as favourites_router

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI Flight Intelligence API"
)

print("CORS_ORIGINS:", settings.CORS_ORIGINS, flush=True)

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin", "")
    if request.method == "OPTIONS":
        return Response(
            content="",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin if origin in settings.CORS_ORIGINS else "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600",
            },
        )
    response = await call_next(request)
    if origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.include_router(auth_router, prefix="/api/v1")
app.include_router(flight_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(conversation_router, prefix="/api/v1")
app.include_router(prediction_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(favourites_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
