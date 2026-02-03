from fastapi import APIRouter

from src.api.v1 import (
    auth,
    discounts,
    ev_charging,
    memberships,
    orgs,
    parking_spaces,
    payments,
    rates,
    reports,
    reservations,
    sessions,
    users,
    vehicles,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(vehicles.router)
api_router.include_router(parking_spaces.router)
api_router.include_router(sessions.router)
api_router.include_router(payments.router)
api_router.include_router(rates.router)
api_router.include_router(discounts.router)
api_router.include_router(reservations.router)
api_router.include_router(memberships.router)
api_router.include_router(reports.router)
api_router.include_router(ev_charging.router)
api_router.include_router(orgs.router)
