import logging
import secrets
import threading
import asyncio
import platform
import os
from typing import Dict, Any

from fastapi import APIRouter, Form, HTTPException
from pydantic import BaseModel
import globals

# Import WebDriver dependencies
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions

# Setup router and logging
router = APIRouter()
logger = logging.getLogger(__name__)

# Shared state lock from globals
state_lock = asyncio.Lock()


# Request Models
class ActivityRequest(BaseModel):
    url: str


# WebDriver Session Manager Implementation
class WebDriverSessionManager:
    """
    Manages multiple WebDriver sessions
    """
    def __init__(self):
        # Thread-safe dictionary to store active sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Thread lock for session management
        self._lock = threading.Lock()
    
    # Update the create_session method in WebDriverSessionManager class in chrome.py

    def create_session(self, browser_type: str, headless: bool = False):
        """
        Create a new WebDriver session
        
        :param browser_type: Type of browser to create
        :param headless: Whether to run the browser in headless mode
        :return: Session information dictionary
        """

        try:
            # Generate unique session ID (using chrome_id instead of session_id)
            chrome_id = secrets.token_urlsafe(16)
            
            # Check the system architecture
            system = platform.system()
            is_mac = system == 'Darwin'
            is_arm = platform.machine() in ['arm64', 'aarch64']
            
            # Create WebDriver based on browser type
            if browser_type == 'chrome':
                chrome_options = ChromeOptions()
                
                # Set headless mode if requested
                if headless:
                    # These options improve headless operation
                    chrome_options.add_argument("--headless=new")  # New headless implementation
                    chrome_options.add_argument("--disable-gpu")  # Recommended for headless
                    chrome_options.add_argument("--window-size=1920,1080")  # Set window size
                
                # Add options that work better for automation
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-infobars")
                
                # Special handling for Mac M1/M2 (ARM architecture)
                if is_mac and is_arm:
                    logger.info("Detected Mac ARM architecture, using special ChromeDriver setup")
                    
                    try:
                        # Direct approach for Mac ARM without webdriver_manager
                        logger.info("Trying direct Chrome instantiation without webdriver_manager")
                        driver = webdriver.Chrome(options=chrome_options)
                    except Exception as direct_error:
                        logger.warning(f"Direct Chrome instantiation failed: {str(direct_error)}")
                        
                        try:
                            # Try using Homebrew-installed chromedriver
                            logger.info("Trying with Homebrew-installed chromedriver")
                            driver_path = "/opt/homebrew/bin/chromedriver"
                            if not os.path.exists(driver_path):
                                # Try the Intel homebrew path as fallback
                                driver_path = "/usr/local/bin/chromedriver"
                            
                            if os.path.exists(driver_path):
                                service = ChromeService(executable_path=driver_path)
                                driver = webdriver.Chrome(service=service, options=chrome_options)
                            else:
                                raise FileNotFoundError(f"Chromedriver not found at {driver_path}")
                        except Exception as brew_error:
                            logger.warning(f"Homebrew chromedriver attempt failed: {str(brew_error)}")
                            
                            # Last resort - download specific version known to work on Mac ARM
                            logger.info("Trying with a specific ChromeDriver version")
                            from webdriver_manager.chrome import ChromeDriverManager
                            
                            try:
                                from webdriver_manager.core.os_manager import ChromeType
                                # Specify a version known to work well with Mac ARM
                                driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM, version="112.0.5615.49").install()
                            except ImportError:
                                # If ChromeType is not available, try without it
                                driver_path = ChromeDriverManager(version="112.0.5615.49").install()
                                
                            service = ChromeService(executable_path=driver_path)
                            driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    # Standard setup for other platforms
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    
            elif browser_type == 'firefox':
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                firefox_options = FirefoxOptions()
                
                if headless:
                    firefox_options.add_argument("--headless")
                
                try:
                    # Try using webdriver_manager
                    service = FirefoxService(GeckoDriverManager().install())
                    driver = webdriver.Firefox(service=service, options=firefox_options)
                except Exception as e:
                    logger.warning(f"Firefox with webdriver_manager failed: {str(e)}")
                    
                    # Try direct initialization
                    driver = webdriver.Firefox(options=firefox_options)
                    
            else:
                raise ValueError(f'Unsupported browser type: {browser_type}')
            
            # Common setup for all browser types
            # Open a new tab
            driver.execute_script("window.open('');")
            
            # Switch to the new tab
            driver.switch_to.window(driver.window_handles[-1])
            
            # Navigate to a default page (optional)
            driver.get("about:blank")
            
            # Set a longer page load timeout for slower networks/operations
            driver.set_page_load_timeout(60)
            
            # Store session information
            with self._lock:
                self._sessions[chrome_id] = {
                    'driver': driver,
                    'browser_type': browser_type,
                    'headless': headless,
                    'created_at': threading.get_ident()  # Track creation thread
                }
            
            # Log that we've successfully created the session
            mode_str = "headless" if headless else "visible"
            logger.info(f"Created new {mode_str} {browser_type} session with chrome_id: {chrome_id}")
            
            return {
                'status': 'success',
                'chrome_id': chrome_id,
                'browser': browser_type,
                'headless': headless,
                'message': f'WebDriver session created successfully in {mode_str} mode'
            }
        
        except Exception as e:
            logger.error(f"Error creating WebDriver session: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
        
    def perform_session_activity(self, chrome_id: str, url: str):
        """
        Perform an activity in a specific WebDriver session
        
        :param chrome_id: ID of the chrome session
        :param url: URL to navigate to
        :return: Activity result
        """
        with self._lock:
            session = self._sessions.get(chrome_id)
            
            if not session:
                return {
                    'status': 'error',
                    'message': f'Chrome session {chrome_id} not found'
                }
            
            try:
                # Get the WebDriver for this session
                driver = session['driver']
                
                # Ensure we're on the last tab
                driver.switch_to.window(driver.window_handles[-1])
                
                # Navigate to the URL
                driver.get(url)
                
                return {
                    'status': 'success',
                    'message': f'Navigated to {url} in chrome session {chrome_id}'
                }
            
            except Exception as e:
                logger.error(f"Error in WebDriver session activity: {str(e)}")
                return {
                    'status': 'error',
                    'message': str(e)
                }
    
    def list_sessions(self):
        """
        List all active WebDriver sessions
        
        :return: List of active session details
        """
        with self._lock:
            return [
                {
                    'chrome_id': cid, 
                    'browser': session['browser_type'],
                    'headless': session.get('headless', False)
                } 
                for cid, session in self._sessions.items()
            ]
    
    def close_session(self, chrome_id: str):
        """
        Close a specific WebDriver session
        
        :param chrome_id: ID of the chrome session to close
        :return: Closure status
        """
        with self._lock:
            session = self._sessions.get(chrome_id)
            if session:
                try:
                    session['driver'].quit()
                    del self._sessions[chrome_id]
                    return {
                        'status': 'success',
                        'message': f'Chrome session {chrome_id} closed successfully'
                    }
                except Exception as e:
                    logger.error(f"Error closing WebDriver session: {str(e)}")
                    return {
                        'status': 'error',
                        'message': str(e)
                    }
            else:
                return {
                    'status': 'error',
                    'message': f'Chrome session {chrome_id} not found'
                }
    
    def close_all_sessions(self):
        """
        Close all active WebDriver sessions
        """
        with self._lock:
            for session in list(self._sessions.values()):
                try:
                    session['driver'].quit()
                except Exception as e:
                    logger.error(f"Error during session cleanup: {str(e)}")
            self._sessions.clear()
            return {
                'status': 'success',
                'message': 'All chrome sessions closed successfully'
            }


# Initialize the WebDriver Session Manager
driver_manager = WebDriverSessionManager()


# Chrome Session Management Routes - Updated with headless parameter
@router.post("/create")
async def create_chrome_session(
    browser: str = Form(default='chrome'),
    headless: bool = Form(default=True)
):
    """
    Create a new Chrome WebDriver session
    
    Parameters:
    - browser: Browser type (chrome, firefox)
    - headless: Whether to run the browser in headless mode
    """
    result = driver_manager.create_session(browser, headless)
    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])
    return result


@router.post("/{chrome_id}/navigate")
async def chrome_navigate(chrome_id: str, request: ActivityRequest):
    """Navigate to a URL in a specific Chrome session"""
    result = driver_manager.perform_session_activity(chrome_id, request.url)
    if result['status'] == 'error':
        raise HTTPException(
            status_code=404 if 'not found' in result['message'] else 500, 
            detail=result['message']
        )
    return result


@router.get("/list")
async def list_chrome_sessions():
    """List all active Chrome sessions"""
    return driver_manager.list_sessions()


@router.post("/{chrome_id}/close")
async def close_chrome_session(chrome_id: str):
    """Close a specific Chrome session"""
    result = driver_manager.close_session(chrome_id)
    if result['status'] == 'error' and 'not found' in result['message']:
        raise HTTPException(status_code=404, detail=result['message'])
    return result


@router.post("/close-all")
async def close_all_chrome_sessions():
    """Close all active Chrome sessions"""
    return driver_manager.close_all_sessions()


# Route to associate a Chrome session with an existing app session
@router.post("/{chrome_id}/associate/{session_id}")
async def associate_chrome_with_session(chrome_id: str, session_id: str):
    """Associate a Chrome session with an application session"""
    # Check if the chrome_id exists
    chrome_sessions = driver_manager.list_sessions()
    chrome_exists = any(session['chrome_id'] == chrome_id for session in chrome_sessions)
    
    if not chrome_exists:
        raise HTTPException(status_code=404, detail=f"Chrome session {chrome_id} not found")
    
    # Check if the session_id exists in global state
    async with state_lock:
        if session_id not in globals.global_state:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Associate the chrome_id with the session
        globals.global_state[session_id]["chrome_id"] = chrome_id
    
    return {
        "status": "success",
        "message": f"Chrome session {chrome_id} associated with application session {session_id}"
    }


# Add shutdown event handler to close all sessions
@router.on_event("shutdown")
async def shutdown_event():
    """Close all Chrome sessions when the application shuts down"""
    driver_manager.close_all_sessions()