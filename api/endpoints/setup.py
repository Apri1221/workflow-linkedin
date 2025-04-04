import logging
from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from schema.dto.response.index import SetupResponse, DataCookies, Profile, DataPrompt
from schema.dto.request.index import PromptRequest, CookiesRequest
from typing import List
from service.leads_service import init, check_session
from utils.uuid import uuid7
import asyncio
import globals


# ------------- configuration
state_lock = asyncio.Lock()

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s:\t %(name)-20s %(message)s"
)
# -------------- end configuration




@router.post("/cookies")
async def initial_setup(request: List[CookiesRequest]):
    session = check_session()
    session_id = str(uuid7())
    async with state_lock:
        globals.global_state[session_id] = {
            "platforms": session,
            "state": "",
            "payload": {}
        }

    approved = False
    dataCookies = None
    if approved:
        dataCookies = DataCookies(
                approved=approved,
                profile=Profile(
                    title="akbarfauzi@yopmail.com",
                    data={
                        "name": "Akbar Fauzi",
                        "url": "https://www.linkedin.com/in/akbarfauzi/",
                        "email": "akbarfauzi@yopmail.com",
                        "key": "-F8dj3Fdf210Jf29f"
                    }
                ),
            )
    else:
        dataCookies = DataCookies(
                approved=approved,
                reason="You are not logged in to LinkedIn. Please log in to LinkedIn and try again."
            )

    return {
        "success": True,
        "data": dataCookies
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
        "data": DataPrompt(
            platforms = session,
            result = data,
            state = {
                "sessionId": session_id
            }
        )
    }
