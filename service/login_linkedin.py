import os
import time
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

active_sessions = {}

async def login_to_linkedin(session_id: str, chrome_version: str = None) -> bool:
    """Log in to LinkedIn Sales Navigator and keep the session open."""
    try:
        if session_id in active_sessions and active_sessions[session_id]['driver']:
            logging.info(f"Session {session_id} is already active.")
            return True

        logging.info(f"Starting LinkedIn login for session: {session_id}")

        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # Use the latest webdriver_manager, which accepts 'version'
        try:
            if chrome_version:
                service = Service(ChromeDriverManager(version=chrome_version).install())
                logging.info(f"Using ChromeDriver version: {chrome_version}")
            else:
                service = Service(ChromeDriverManager().install())
                logging.info("Using webdriver-manager to get the latest ChromeDriver.")
            driver = webdriver.Chrome()
        except Exception as driver_init_error:
            logging.error(f"Error initializing ChromeDriver: {driver_init_error}")
            return False

        driver.get('https://www.linkedin.com/sales/login')

        # Switch to the login iframe
        try:
            WebDriverWait(driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, 'iframe[title="Login screen"]'))
            )
        except Exception as iframe_error:
            logging.error(f"Error waiting for or switching to login iframe: {iframe_error}")
            driver.quit()
            return False

        # Wait for username/password fields
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'session_key')))
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'session_password')))
        except Exception as element_error:
            logging.error(f"Error waiting for username/password fields: {element_error}")
            driver.quit()
            return False

        # Input credentials
        try:
            driver.find_element(By.NAME, 'session_key').send_keys(os.getenv('LINKEDIN_USERNAME'))
            driver.find_element(By.NAME, 'session_password').send_keys(os.getenv('LINKEDIN_PASSWORD'))
        except Exception as credential_error:
            logging.error(f"Error inputting credentials: {credential_error}")
            driver.quit()
            return False

        # Click login
        try:
            driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        except Exception as login_button_error:
            logging.error(f"Error clicking login button: {login_button_error}")
            driver.quit()
            return False

        # Function to check if still on the login page
        def check_login_page():
            try:
                current_url = driver.current_url
                if '/sales/login' in current_url:
                    logging.info("Waiting for user verification (2FA or CAPTCHA)...")
                    return True
                return False
            except Exception as e:
                logging.error(f"Error checking login page: {e}")
                return False

        # Wait up to 10 cycles of 30s to allow user to pass 2FA/CAPTCHA
        for _ in range(10):
            if check_login_page():
                await asyncio.sleep(30)
            else:
                logging.info("Login Successful!")
                break

        # Store driver in session dictionary
        active_sessions[session_id] = {
            "driver": driver,
            "session_url": None,
            "session_id": driver.session_id
        }

        logging.info(f"Session URL: {driver}")
        logging.info(f"Session ID: {driver.session_id}")
        return True

    except Exception as e:
        logging.error(f"LinkedIn login failed: {e}")
        return False

async def close_session(session_id: str):
    """Closes the active LinkedIn session for the given session ID."""
    if session_id in active_sessions:
        active_sessions[session_id]["driver"].quit()
        del active_sessions[session_id]
        logging.info(f"Closed session {session_id}. Browser window has been closed and the Selenium session is now INVALID. A new login will be required to start a fresh session.") # More explicit log message
        if session_id in globals.global_state and "selenium_driver" in globals.global_state[session_id]:
            del globals.global_state[session_id]["selenium_driver"]
            logging.info(f"Removed driver from global_state for session {session_id}.")
