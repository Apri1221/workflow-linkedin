from fastapi import APIRouter, Depends
from api.endpoints import (
    setup,
    task
)
from utils.limit_generator import rate_limited_shared

api_router = APIRouter()

api_router.include_router(
    task.router,
    prefix="/task",
    tags=["Tasks"],
    dependencies=[Depends(rate_limited_shared)]
)

api_router.include_router(
    setup.router,
    prefix="",
    tags=["Setup"],
    dependencies=[Depends(rate_limited_shared)]
)