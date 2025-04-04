import logging
from fastapi import APIRouter, Header, Depends, HTTPException
from utils.constant import ConstantsTask
from schema.dto.request.index import SearchLeadRequest, CommonHeaders
from schema.dto.response.index import TaskResponse, DataTask
import asyncio
import globals
from typing import Annotated
from service.leads_service import start_search_leads_task
from service.login_linkedin import login_to_linkedin  
from service.login_linkedin import active_sessions




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
        
        try:
            login_success = await login_to_linkedin(session_id)
            if not login_success:
                raise HTTPException(status_code=500, detail="Failed to log in to LinkedIn")
        except Exception as e:
            logger.error(f"LinkedIn login error for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"LinkedIn login failed: {e}")
        
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
    current_task = ConstantsTask.CREATE_LEAD_FILTERS # Or should this be SEARCH_LEADS?
    next_task = ConstantsTask.SEARCH_LEADS # Or next task after search?
    async with state_lock:
        data = globals.global_state.get(session_id)
        if not data:
            logger.warning(f"/search-leads: Session data NOT found for session_id: {session_id} in global_state.")
            raise HTTPException(status_code=400, detail="Session not found")
        if data["next_task"] != current_task:
            raise HTTPException(status_code=400, detail="Invalid task order")

        # Log before retrieval attempt
        logger.info(f"/search-leads: Attempting to retrieve driver for session_id: {session_id} from global_state...")

        # **Get the driver from global_state**
        driver = globals.global_state[session_id].get("selenium_driver")
        if not driver:
            logger.warning(f"/search-leads: No active Selenium session found for session_id: {session_id} in global_state. Login required.") # Log warning if not found
            logger.warning(f"/search-leads: globals.global_state contents at retrieval failure: {globals.global_state}") # Log global_state at failure
            raise HTTPException(status_code=500, detail="No active Selenium session found. Login required.")

        logger.info(f"/search-leads: Driver successfully retrieved for session_id: {session_id} in /search-leads endpoint.") # Log success
        logger.info(f"/search-leads: globals.global_state contents AFTER successful retrieval: {globals.global_state}") # Log global_state after retrieval
        logger.info(f"--- /search-leads endpoint END ---") # Added end log


        start_search_leads_task(session_id, data, driver=driver) # **Pass driver to task function**
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