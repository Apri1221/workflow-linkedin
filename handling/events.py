from contextlib import asynccontextmanager
from fastapi import FastAPI
import pytest
import os
import signal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # exit_code = await run_unit_test()
    # if exit_code != 0:
    #     sys.exit(0)
    yield
    # Clean up the ML models and release the resources
    # ml_models.clear()
    os.kill(os.getpid(), signal.SIGTERM)


async def run_unit_test():
    return pytest.main(args=["-vv","--cov=test","--cov-report=term-missing","-s","--capture=sys"])