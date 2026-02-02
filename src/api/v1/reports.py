from fastapi import APIRouter

from src.core.dependencies import DB, AdminUser
from src.schemas.report import DashboardSummary
from src.services import report as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(db: DB, admin: AdminUser):
    return await report_service.get_dashboard_summary(db)
