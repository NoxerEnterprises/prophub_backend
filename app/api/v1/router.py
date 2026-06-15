from fastapi import APIRouter

from app.api.v1.routes import admin, agent_properties, agents, auth, chats, health, payments, properties, ws

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(agent_properties.router)
api_router.include_router(properties.router)
api_router.include_router(payments.router)
api_router.include_router(chats.router)
api_router.include_router(ws.router)
api_router.include_router(admin.router)
