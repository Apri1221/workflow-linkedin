import logging
from fastapi import APIRouter, Header, Depends, HTTPException, Path, Body
from utils.constant import ConstantsTask
from schema.dto.request.index import SearchLeadRequest, CommonHeaders, PromptRequest
from schema.dto.response.index import TaskResponse, DataTask
import asyncio
import globals
from typing import Annotated, Optional
from service.leads_service import start_search_leads_task, main_scrape_leads
from service.login_linkedin import login_to_linkedin, active_sessions
from utils.uuid import uuid7
from pydantic import BaseModel, Field
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from service.login_linkedin import login_to_linkedin, active_sessions, perform_terminal_login
from typing import Union, List
import threading



# Import for chrome session
from api.endpoints.chrome import driver_manager

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
    current_task = ConstantsTask.CREATE_LEAD_FILTERS
    next_task = ConstantsTask.SEARCH_LEADS
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


# LINKEDIN SCRAPING WITH CHROME
# -----------------------------


# Create a request model for LinkedIn scraping
# LINKEDIN SCRAPING WITH CHROME
# -----------------------------


# Create a request model for LinkedIn scraping
class LinkedInScrapeRequest(BaseModel):
    jobTitle: str
    numberOfLeads: int
    seniorityLevel: Union[str, List[str]]  # Accept either string or list
    industry: str
    yearsOfExperience: Union[int, str]  # Accept either int or string
    goodToHave: Union[str, List[str]] = []
    
    # Headless mode should be False by default to see the browser for manual verification if needed
    headless: bool = Field(default=False, description="Run in headless mode (no visible browser)")


# LinkedIn scrape endpoint with terminal login
@router.post("/linkedin-scrape")
async def linkedin_scrape(request: LinkedInScrapeRequest):
    """
    Create a LinkedIn scraping task with login via terminal
    
    This endpoint:
    1. Creates a new Chrome session (visible by default for easier login verification)
    2. Prompts for login credentials in the terminal
    3. Performs the specified search and scrapes leads
    """
    session_id = str(uuid7())
    
    # Create a new Chrome session (default to visible browser for login verification)
    logger.info(f"Creating a new Chrome session for LinkedIn scraping (headless: {request.headless})")
    chrome_result = driver_manager.create_session("chrome", headless=request.headless)
    if chrome_result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Failed to create Chrome session: {chrome_result['message']}")
    chrome_id = chrome_result["chrome_id"]
    logger.info(f"Created new Chrome session with chrome_id: {chrome_id}")
    
    # Get the WebDriver
    with driver_manager._lock:
        chrome_session = driver_manager._sessions.get(chrome_id)
        driver = chrome_session.get("driver")
    
    # Store session data
    async with state_lock:
        globals.global_state[session_id] = {
            "chrome_id": chrome_id,
            "state": "waiting_for_login",
            "headless": request.headless,
            "payload": {
                "jobTitle": request.jobTitle,
                "numberOfLeads": request.numberOfLeads,
                "seniorityLevel": request.seniorityLevel,
                "industry": request.industry,
                "yearsOfExperience": request.yearsOfExperience,
                "goodToHave": request.goodToHave,
            }
        }
    
    # Start background task that includes terminal login
    import threading
    
    def scrape_task_with_terminal_login():
        try:
            # First perform login via terminal
            logger.info(f"[Session {session_id}] Starting LinkedIn login process via terminal")
            
            # Define a function to safely update the global state
            def update_global_state(update_func):
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def _update():
                        async with state_lock:
                            if session_id in globals.global_state:
                                update_func(globals.global_state[session_id])
                    
                    # Run the async function in this thread's event loop
                    loop.run_until_complete(_update())
                    loop.close()
                except Exception as e:
                    logger.error(f"Error updating global state: {e}")
            
            # Update state to show we're waiting for input
            update_global_state(lambda state: state.update({"state": "waiting_for_login_input"}))
            
            # Perform the login
            login_success = perform_terminal_login(driver, session_id)
            
            # Update state based on login result
            if login_success:
                update_global_state(lambda state: state.update({"state": "scraping"}))
            else:
                update_global_state(lambda state: state.update({
                    "state": "error", 
                    "error": "LinkedIn login failed"
                }))
            
            if not login_success:
                logger.error(f"[Session {session_id}] Aborting scraping due to login failure")
                return
            
            # Proceed with scraping if login successful
            logger.info(f"[Session {session_id}] Login successful, starting LinkedIn scraping")
            
            main_scrape_leads(
                session_id=session_id, 
                driver=driver, 
                industry=request.industry,
                job_title=request.jobTitle, 
                seniority_level=request.seniorityLevel,
                years_of_experience=request.yearsOfExperience
            )
            
            # Update the session state when completed
            update_global_state(lambda state: state.update({"state": "completed"}))
                    
            logger.info(f"[Session {session_id}] LinkedIn scraping completed successfully")
        except Exception as e:
            logger.error(f"[Session {session_id}] Error in LinkedIn scraping task: {str(e)}")
            import traceback
            logger.error(f"[Session {session_id}] Traceback: {traceback.format_exc()}")
            
            # Update the session state on error
            try:
                def update_error_state(state):
                    state.update({
                        "state": "error",
                        "error": str(e)
                    })
                update_global_state(update_error_state)
            except Exception as state_error:
                logger.error(f"[Session {session_id}] Failed to update state: {state_error}")
    
    # Start the task in a background thread
    thread = threading.Thread(target=scrape_task_with_terminal_login)
    thread.daemon = True
    thread.start()
    
    # Return response immediately
    return {
        "success": True,
        "data": {
            "message": "LinkedIn scraping task started. Please check terminal for login prompt.",
            "sessionId": session_id,
            "chromeId": chrome_id,
            "state": "waiting_for_login"
        }
    }


# LinkedIn scrape with existing Chrome session
@router.post("/linkedin-scrape/with-chrome/{chrome_id}")
async def linkedin_scrape_with_chrome(
    chrome_id: str,
    request: LinkedInScrapeRequest
):
    """Create a LinkedIn scraping task using an existing Chrome session with terminal login"""
    session_id = str(uuid7())
    
    # Verify chrome_id exists
    chrome_sessions = driver_manager.list_sessions()
    chrome_session_info = next((session for session in chrome_sessions if session['chrome_id'] == chrome_id), None)
    
    if not chrome_session_info:
        raise HTTPException(status_code=404, detail=f"Chrome session {chrome_id} not found")
    
    # Get the WebDriver
    with driver_manager._lock:
        chrome_session = driver_manager._sessions.get(chrome_id)
        if not chrome_session:
            raise HTTPException(status_code=404, detail=f"Chrome session {chrome_id} not found")
        driver = chrome_session.get("driver")
    
    # Store session data
    async with state_lock:
        globals.global_state[session_id] = {
            "chrome_id": chrome_id,
            "state": "waiting_for_login",
            "payload": {
                "jobTitle": request.jobTitle,
                "numberOfLeads": request.numberOfLeads,
                "seniorityLevel": request.seniorityLevel,
                "industry": request.industry,
                "yearsOfExperience": request.yearsOfExperience,
                "goodToHave": request.goodToHave,
            }
        }
    
    
    def scrape_task_with_terminal_login():
        try:
            # First perform login via terminal
            logger.info(f"[Session {session_id}] Starting LinkedIn login process via terminal with existing Chrome session")
            
            # Define a function to safely update the global state
            def update_global_state(update_func):
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def _update():
                        async with state_lock:
                            if session_id in globals.global_state:
                                update_func(globals.global_state[session_id])
                    
                    # Run the async function in this thread's event loop
                    loop.run_until_complete(_update())
                    loop.close()
                except Exception as e:
                    logger.error(f"Error updating global state: {e}")
            
            # Update state to show we're waiting for input
            update_global_state(lambda state: state.update({"state": "waiting_for_login_input"}))
            
            # Perform the login
            login_success = perform_terminal_login(driver, session_id)
            
            # Update state based on login result
            if login_success:
                update_global_state(lambda state: state.update({"state": "scraping"}))
            else:
                update_global_state(lambda state: state.update({
                    "state": "error", 
                    "error": "LinkedIn login failed"
                }))
            
            if not login_success:
                logger.error(f"[Session {session_id}] Aborting scraping due to login failure")
                return
                
            # Process the seniorityLevel field - convert to string if it's a list
            seniority_level = request.seniorityLevel
            if isinstance(seniority_level, list) and len(seniority_level) > 0:
                seniority_level = seniority_level[0]
            
            # Process the goodToHave field - convert to string if needed
            good_to_have = request.goodToHave
            if isinstance(good_to_have, str):
                good_to_have = [good_to_have]
                
            # Process yearsOfExperience - ensure it's a string
            years_of_experience = str(request.yearsOfExperience)
                
            # Proceed with scraping
            main_scrape_leads(
                session_id=session_id, 
                driver=driver, 
                industry=request.industry,
                job_title=request.jobTitle, 
                seniority_level=seniority_level,
                years_of_experience=years_of_experience
            )
            
            # Update the session state when completed
            update_global_state(lambda state: state.update({"state": "completed"}))
                    
            logger.info(f"[Session {session_id}] LinkedIn scraping completed successfully")
        except Exception as e:
            logger.error(f"[Session {session_id}] Error in LinkedIn scraping task: {str(e)}")
            import traceback
            logger.error(f"[Session {session_id}] Traceback: {traceback.format_exc()}")
            
            # Update the session state on error
            try:
                def update_error_state(state):
                    state.update({
                        "state": "error",
                        "error": str(e)
                    })
                update_global_state(update_error_state)
            except Exception as state_error:
                logger.error(f"[Session {session_id}] Failed to update state: {state_error}")
    
    # Start the task in a background thread
    thread = threading.Thread(target=scrape_task_with_terminal_login)
    thread.daemon = True
    thread.start()
    
    return {
        "success": True,
        "data": {
            "message": "LinkedIn scraping task started with existing Chrome session. Please check terminal for login prompt.",
            "sessionId": session_id,
            "chromeId": chrome_id,
            "state": "waiting_for_login"
        }
    }


# Add status check endpoint
@router.get("/linkedin-scrape/{session_id}/status")
async def linkedin_scrape_status(session_id: str):
    """Get the status of a LinkedIn scraping task"""
    async with state_lock:
        session_data = globals.global_state.get(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    state = session_data.get("state", "unknown")
    
    response = {
        "success": True,
        "data": {
            "sessionId": session_id,
            "chromeId": session_data.get("chrome_id"),
            "state": state
        }
    }
    
    # Add error information if there was an error
    if state == "error" and "error" in session_data:
        response["data"]["error"] = session_data["error"]
    
    # Add output files information if completed
    if state == "completed":
        response["data"]["outputFiles"] = [
            f"{session_id}.csv",
            f"{session_id}_leads_pro.csv"
        ]
    
    return response