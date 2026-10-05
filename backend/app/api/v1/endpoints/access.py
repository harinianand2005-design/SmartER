from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, require_roles
from app.models import UserRole

router = APIRouter(prefix="/access", tags=["authorization"])


@router.get("/dashboard")
def dashboard_access(current_user: CurrentUser) -> dict[str, str]:
    return {"message": "Dashboard access granted", "role": current_user.role.value}


@router.get("/admin-settings", dependencies=[Depends(require_roles(UserRole.ADMIN))])
def admin_settings_access() -> dict[str, str]:
    return {"message": "Admin access granted"}


@router.get("/triage-recommendations", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.TRIAGE_NURSE))])
def triage_recommendations_access() -> dict[str, str]:
    return {"message": "Triage recommendations access granted"}


@router.get("/health-authority-analytics", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.HEALTH_AUTHORITY))])
def health_authority_analytics_access() -> dict[str, str]:
    return {"message": "Aggregated analytics access granted"}