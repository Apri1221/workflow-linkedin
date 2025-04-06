from fastapi import APIRouter, Depends
from api.endpoints import (
    setup,
    task,
    chrome  # Add the new chrome module
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

# Add the chrome router
api_router.include_router(
    chrome.router,  # Use the chrome.router from the chrome module
    prefix="/chrome",
    tags=["Chrome"],
    dependencies=[Depends(rate_limited_shared)]
)