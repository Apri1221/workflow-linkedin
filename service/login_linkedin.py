# service/login_linkedin.py
import logging
import asyncio
import getpass
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# Dictionary to track active sessions
active_sessions = {}

async def login_to_linkedin(session_id):
    """
    Placeholder function for existing code references
    In the new architecture, this will be handled by perform_terminal_login
    
    Args:
        session_id: The session ID
        
    Returns:
        bool: Always returns True for compatibility
    """
    logger.info(f"Placeholder login_to_linkedin called for session: {session_id}")
    # This function is kept for backward compatibility
    # The actual login logic will now be in perform_terminal_login
    
    # Mark this session as active
    active_sessions[session_id] = True
    
    return True

def perform_terminal_login(driver, session_id):
    """
    Perform LinkedIn login with credentials entered via terminal
    
    Args:
        driver: Selenium WebDriver instance
        session_id: Session ID for logging
    
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        logger.info(f"[Session {session_id}] Navigating to LinkedIn login page")
        driver.get("https://www.linkedin.com/login")
        
        # Wait for the login page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        
        # Prompt user for email in terminal
        print("\n" + "="*50)
        print(f"LinkedIn Login Required for Session {session_id}")
        print("="*50)
        email = input("Enter LinkedIn Email: ")
        
        # Enter email in browser
        logger.info(f"[Session {session_id}] Entering email")
        username_field = driver.find_element(By.ID, "username")
        username_field.clear()
        username_field.send_keys(email)
        
        # Prompt user for password in terminal (hidden input)
        password = getpass.getpass("Enter LinkedIn Password: ")
        
        # Enter password in browser
        logger.info(f"[Session {session_id}] Entering password")
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)
        
        # Click sign in button
        logger.info(f"[Session {session_id}] Clicking sign in button")
        sign_in_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        sign_in_button.click()
        
        print("Login credentials submitted. Waiting for LinkedIn to process login...")
        
        # Wait for login to complete
        logger.info(f"[Session {session_id}] Waiting for login to complete")
        
        # Check for common login result scenarios
        try:
            # Check if we're redirected to the feed page (success)
            WebDriverWait(driver, 30).until(
                lambda d: "feed" in d.current_url or "sales" in d.current_url
            )
            logger.info(f"[Session {session_id}] Login successful")
            print("✓ LinkedIn login successful!")
            print("="*50 + "\n")
            
            # Mark this session as active
            active_sessions[session_id] = True
            
            return True
        except:
            # Check for login error messages
            try:
                error_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "error-for-username"))
                )
                error_message = error_element.text
                logger.error(f"[Session {session_id}] Login failed: {error_message}")
                print(f"✗ LinkedIn login failed: {error_message}")
                print("="*50 + "\n")
                return False
            except:
                # Check for verification challenges
                if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
                    logger.warning(f"[Session {session_id}] Login requires verification. Please complete it manually.")
                    print("⚠ LinkedIn requires additional verification.")
                    print("Please complete the verification process in the browser if it's visible.")
                    print("If running in headless mode, you may need to restart with visible browser.")
                    
                    # Give user time to complete verification if not in headless mode
                    print("Waiting 60 seconds for you to complete verification...")
                    time.sleep(60)
                    
                    # Check if we got past the verification
                    if "feed" in driver.current_url or "sales" in driver.current_url:
                        logger.info(f"[Session {session_id}] Verification completed successfully")
                        print("✓ Verification completed! Login successful.")
                        print("="*50 + "\n")
                        
                        # Mark this session as active
                        active_sessions[session_id] = True
                        
                        return True
                    else:
                        logger.error(f"[Session {session_id}] Failed to complete verification")
                        print("✗ Verification could not be completed in time.")
                        print("="*50 + "\n")
                        return False
                
                # Check if we're still on the login page
                if "login" in driver.current_url:
                    logger.error(f"[Session {session_id}] Login failed: Still on login page")
                    print("✗ LinkedIn login failed: Still on login page")
                    print("="*50 + "\n")
                    return False
                
                # Assume success if we got past login page
                logger.info(f"[Session {session_id}] Login appears successful: URL={driver.current_url}")
                print("✓ LinkedIn login successful!")
                print("="*50 + "\n")
                
                # Mark this session as active
                active_sessions[session_id] = True
                
                return True
            
    except Exception as e:
        logger.error(f"[Session {session_id}] Error during login: {str(e)}")
        print(f"✗ Error during login process: {str(e)}")
        print("="*50 + "\n")
        return False

def check_session():
    """
    Return list of active platforms or sessions
    This is kept for backward compatibility
    """
    return {"linkedin": True}