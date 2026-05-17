from fastapi import APIRouter

from app.api.v1.routes import admin_agents, agents, auth, debug_roles, health, status

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(status.router, tags=["Status"])
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(admin_agents.router)
api_router.include_router(debug_roles.router)
