from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time
import datetime
import requests



WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3
base_url = "https://asia-southeast1-boringai-staging.cloudfunctions.net"



def perform_login(driver, credentials):
    """Logs into LinkedIn using provided credentials from config.json."""
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.NAME, "session_key"))
    )
    driver.find_element(By.NAME, "session_key").send_keys(credentials['email'])
    driver.find_element(By.NAME, "session_password").send_keys(credentials['password'] + Keys.RETURN)
    time.sleep(3)
    print("Login successful.")


def generate_timestamp():
    """Generates a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def configure_driver(headless=False):
    """Configures and returns a Chrome webdriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("start-maximized")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    if headless:
        chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver


def close_overlay_if_present(driver):
    """Closes any potential overlay/modal that might be intercepting clicks."""
    try:
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._scrim_1onvtb._dialog_1onvtb._visible_1onvtb._topLayer_1onvtb"))
        )
        print("Overlay detected.")
        try:
            close_button = overlay.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss") # Example close button selector, adjust if needed
            close_button.click()
            print("Overlay close button clicked.")
        except NoSuchElementException:
            print("No close button found on overlay, trying to click outside.")
            webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform() # Click at (0,0) to dismiss if overlay allows
        WebDriverWait(driver, 5).until(EC.invisibility_of_element(overlay)) # Wait for overlay to disappear
        print("Overlay should be closed now.")
    except TimeoutException:
        print("No overlay detected.")
        pass # No overlay, continue



def launch_browser():
    """Start a new remote browser session"""
    url = f"{base_url}/remote-browser-allocate"
    payload = {
        "userId": "1703",
        "startUrl": "https://www.linkedin.com/sales/search/people?viewAllFilters=true",
        "timeout": 600000
    }
    
    response = requests.post(url, json=payload)
    if not response.json().get('success'):
        raise ConnectionError("Failed to launch browser")
        
    browser_session = response.json()['data']
    return browser_session['url']


def get_cookies():
    url = f"{base_url}/remote-browser-cookies"
    payload = {"userId": "1703"}
    
    response = requests.post(url, json=payload)
    if not response.json().get('success'):
        raise ConnectionError("Failed to fetch cookies")
        
    return response.json()['data']