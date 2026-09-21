from fastapi import FastAPI

from bff.infrastructure.config import settings
from bff.interfaces.graphql.router import graphql_router
from bff.interfaces.health import router as health_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="BFF GraphQL - Hogar de los Alpes",
)

app.include_router(health_router)
app.include_router(graphql_router)
