import platform
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from api.api import api_router as api_router_v1
from starlette.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from dotenv import dotenv_values
from handling.events import lifespan
import uvicorn
import logging
import sys
import os
import globals
import time
import atexit  # Import atexit for cleanup on exit


config = dotenv_values(".env")


logging.getLogger().handlers.clear()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter("%(levelname)s:\t  %(name)s - %(message)s")
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)
logger.info(f"Python Version : {platform.python_version()}")
logger.info('API is starting up')


#untuk membaca global.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
globals.init()


def custom_openapi():
    return get_openapi(
        title="Docs Spec KYC Service",
        version="1.0.0",
        description="Swagger UI By Apri",
        # routes=app.routes,
    )


def create_app():
    app = FastAPI(lifespan=lifespan)
    app.include_router(api_router_v1, prefix="/boring-ai/v1")
    # app.openapi = custom_openapi

    origins = [
        # "*",
        "https://aprijpltwondr-showcase.vercel.app"
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# application creation
application = create_app()


@application.middleware("http")
async def wrap_response(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        response = await handle_exception(request, exc)
    end_time = time.time()
    logger.info(f"Execution time: {(end_time - start_time) * 1000} ms")
    return response

async def handle_exception(request: Request, exc: Exception):
    status_code = 500
    detail = getattr(exc, 'detail', str(exc))
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    elif isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
        detail = exc.detail
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": detail
        },
    )

@application.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_messages = []
    for err in exc.errors():
        error_messages.append(err['msg'])
    
    # Split combined messages into array and clean up
    split_errors = [
        error.strip() 
        for error in ", ".join(error_messages).split("Value error,") 
        if error.strip()
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": split_errors
        }
    )


# Optional: Import and ensure cleanup of WebDriver sessions on application exit
try:
    from api.endpoints.chrome import driver_manager
    
    # Register cleanup function on exit
    @atexit.register
    def cleanup_driver_sessions():
        logger.info("Cleaning up all Chrome WebDriver sessions")
        driver_manager.close_all_sessions()
        
except ImportError:
    logger.info("Chrome WebDriver manager not available")


if __name__ == "__main__":
    uvicorn.run("main:application", host=config["HOST_URL"], port=int(config["HOST_PORT"]), workers=1, reload=True)