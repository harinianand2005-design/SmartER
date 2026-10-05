from fastapi import APIRouter

from app.api.v1.endpoints import access, analytics, auth, intelligence, metrics, predictions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(access.router)
api_router.include_router(predictions.router)
api_router.include_router(predictions.models_router)
api_router.include_router(intelligence.router)
api_router.include_router(intelligence.alerts_router)
api_router.include_router(analytics.router)
api_router.include_router(metrics.router)


@api_router.get("/status", tags=["system"])
def api_status() -> dict[str, str]:
    return {"status": "ok", "api_version": "v1"}