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



WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3



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
    """Closes any overlay or modal that might be obstructing interaction."""
    try:
        overlay = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div._scrim_1onvtb._dialog_1onvtb._visible_1onvtb._topLayer_1onvtb"))
        )
        print("Overlay detected.")
        try:
            close_button = overlay.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
            close_button.click()
            print("Overlay dismissed via close button.")
        except NoSuchElementException:
            webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform()
            print("Overlay dismissed via outside click.")
        WebDriverWait(driver, 5).until(EC.invisibility_of_element(overlay))
    except TimeoutException:
        # No overlay found
        pass