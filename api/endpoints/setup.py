import logging
import asyncio

from fastapi import APIRouter
from schema.dto.response.index import SetupResponse, DataSetup
from schema.dto.request.index import PromptRequest
from service.leads_service import init, check_session
from utils.uuid import uuid7
import globals

# ------------- configuration
state_lock = asyncio.Lock()

router = APIRouter()
logger = logging.getLogger(__name__)
# -------------- end configuration


# Existing routes
@router.post("/cookies")
async def initial_setup():
    data = init()
    session = check_session()
    session_id = str(uuid7())
    async with state_lock:
        globals.global_state[session_id] = {
            "platforms": session,
            "state": "",
            "payload": {}
        }
    return {
        "success": True,
        "data": DataSetup(
            platforms = session,
            result = data,
        )
    }


@router.post("/prompt", response_model=SetupResponse)
async def setup_prompt(request: PromptRequest):
    data = init()
    session = check_session()
    session_id = str(uuid7())
    async with state_lock:
        globals.global_state[session_id] = {
            "platforms": session,
            "next_task": None,
            "state": None,
            "payload": {
                "jobTitle": request.jobTitle,
                "numberOfLeads": request.numberOfLeads,
                "seniorityLevel": request.seniorityLevel,
                "industry": request.industry,
                "yearsOfExperience": request.yearsOfExperience,
                "goodToHave": request.goodToHave,
            }
        }
    return {
        "success": True,
        "data": DataSetup(
            platforms = session,
            result = data,
            state = {
                "sessionId": session_id
            }
        )
    }