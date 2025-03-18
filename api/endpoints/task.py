import logging
from fastapi import APIRouter, Header, Depends
from utils.constant import ConstantsTask
from schema.dto.request.index import CommonHeaders
from schema.dto.response.index import TaskResponse, DataTask
import asyncio
import globals
from typing import Annotated
from service.leads_service import start_search_leads_task, start_fetch_lead_data_task


# ------------- configuration
state_lock = asyncio.Lock()

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s:\t %(name)-20s %(message)s"
)

async def common_headers_dependency(
    sessionId: Annotated[str, Header()],
) -> CommonHeaders:
    return CommonHeaders(
        sessionId=sessionId,
    )
# -------------- end configuration




@router.get("")
async def initial_task(
    header: CommonHeaders = Depends(common_headers_dependency)
):
    session_id = header.sessionId
    next_task = ConstantsTask.CREATE_LEAD_FILTERS
    async with state_lock:
        if session_id in globals.global_state:
            globals.global_state[session_id]["next_task"] = next_task
        else:
            raise KeyError(f"Session {session_id} not found in global state")

    return {
        "task": next_task,
        "payload": {
            "currentSessionId": session_id
        }
    }


@router.post("/create-lead-filters", response_model=TaskResponse)
async def create_lead_filters(
    header: CommonHeaders = Depends(common_headers_dependency)
):
    session_id = header.sessionId
    current_task = ConstantsTask.CREATE_LEAD_FILTERS
    next_task = ConstantsTask.SEARCH_LEADS
    async with state_lock:
        data = globals.global_state.get(session_id)
        if not data:
            raise Exception("Session not found")
        if data["next_task"] != current_task:
            raise Exception("Invalid task order")
        
        return {
            "success": True,
            "data": DataTask(
                results = [],
                state = {
                    "sessionId": session_id
                },
                next = {
                    "task": next_task,
                    "payload": data["payload"]
                }
            )
        }
    

@router.post("/search-leads", response_model=TaskResponse)
async def search_leads(
    header: CommonHeaders = Depends(common_headers_dependency)
):
    session_id = header.sessionId
    current_task = ConstantsTask.CREATE_LEAD_FILTERS
    next_task = ConstantsTask.SEARCH_LEADS
    async with state_lock:
        data = globals.global_state.get(session_id)
        if not data:
            raise Exception("Session not found")
        if data["next_task"] != current_task:
            raise Exception("Invalid task order")
        
        start_search_leads_task(session_id, data)
        return {
            "success": True,
            "data": DataTask(
                results = [],
                state = {
                    "sessionId": session_id
                },
                next = {
                    "task": next_task,
                    "payload": data["payload"]
                }
            )
        }


@router.post("/fetch-lead-data", response_model=TaskResponse)
async def search_leads(
    header: CommonHeaders = Depends(common_headers_dependency)
):
    session_id = header.sessionId
    current_task = ConstantsTask.SEARCH_LEADS
    next_task = ConstantsTask.ANALYZE_LEAD_DATA
    # async with state_lock:
    #     data = globals.global_state.get(session_id)
    #     if not data:
    #         raise Exception("Session not found")
    #     if data["next_task"] != current_task:
    #         raise Exception("Invalid task order")
        
    start_fetch_lead_data_task(session_id)
    return {
        "success": True,
        "data": DataTask(
            results = [],
            state = {
                "sessionId": session_id
            },
            next = {
                "task": next_task,
                "payload": None
            }
        )
    }