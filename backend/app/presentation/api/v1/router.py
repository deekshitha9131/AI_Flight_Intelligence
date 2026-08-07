"""Versioned API router aggregation.

Every v1 router is included here, exactly once. app/main.py imports only
`api_router` from this module — it never imports individual routers
directly, so adding a new resource in a later phase means adding one
`include_router` line here, not touching the application factory.
"""

from fastapi import APIRouter

from app.presentation.api.v1.routers import auth, gmail, health

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(gmail.router)

# Future phases register their routers the same way, e.g.:
#   from app.presentation.api.v1.routers import threads, drafts, contacts, settings
#   api_router.include_router(threads.router)
#   api_router.include_router(drafts.router)
#   api_router.include_router(contacts.router)
#   api_router.include_router(settings.router)