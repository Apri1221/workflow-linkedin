import csv
import json
import re
import os
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from groq import Groq
from dotenv import load_dotenv

# -------------------------------
# Utility Functions

def generate_timestamp():
    """Generates a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_results_to_csv(results, filename):
    """Write scraped results to CSV with a timestamp in the filename."""
    timestamp = generate_timestamp()
    filename_with_timestamp = filename.replace(".csv", f"_{timestamp}.csv")
    print(f"Writing results to CSV: {filename_with_timestamp}")

    with open(filename_with_timestamp, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["person_name", "person_title", "linkedin_profile_link", "company_name", "location", "job_title_1", "job_title_2", "company_name_1", "company_name_2", "company_description_1", "company_description_2", "email"])
        for result in results:
            writer.writerow([
                result.get("person_name", "NA"),
                result.get("person_title", "NA"),
                result.get("linkedin_profile_link", "NA"),
                result.get("company_name", "NA"),
                result.get("location", "NA"),
                result.get("job_title_1", "NA"),
                result.get("job_title_2", "NA"),
                result.get("company_name_1", "NA"),
                result.get("company_name_2", "NA"),
                result.get("company_description_1", "NA"),
                result.get("company_description_2", "NA"),
                result.get("email", "NA"),
            ])
    print(f"Results written to {filename_with_timestamp}")

# -------------------------------
# Login and Scraping Functions

def login_to_site(driver, config):
    print('Starting login process...')
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "session_key")),
        "Timeout waiting for login page to load"
    )
    print("Login page loaded.")
    email_field = driver.find_element(By.NAME, "session_key")
    password_field = driver.find_element(By.NAME, "session_password")
    email_field.send_keys(config['email'])
    password_field.send_keys(config['password'])
    password_field.send_keys(Keys.RETURN)
    print("Login credentials entered and submitted.")
    time.sleep(15)  # Adjust if manual login is needed
    print("Login completed, navigating to start URL.")



def get_linkedin_profile_details(driver, profile_url):
    job_titles = ["NA", "NA"]
    company_names = ["NA", "NA"]
    company_descriptions = ["NA", "NA"]
    email = "NA"

    try:
        print(f"Loading profile page: {profile_url}")
        driver.get(profile_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#experience-section")),
            f"Timeout waiting for experience section on profile page: {profile_url}"
        )
        print(f"Profile page loaded and experience section found: {profile_url}")
    except Exception as e_load:
        print(f"Error loading profile page {profile_url}: {e_load}")
        error_filename = f"profile_page_source_error_load_{generate_timestamp()}.html"
        with open(error_filename, "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print(f"Profile page HTML saved to '{error_filename}' due to load error.")
        return job_titles, company_names, company_descriptions, email

    try:
        experience_section = driver.find_element(By.CSS_SELECTOR, "#experience-section")
        roles = experience_section.find_elements(By.CSS_SELECTOR, "li._experience-entry_1irc72")
        print(f"Found {len(roles)} experience entries.")
    except Exception as e_exp:
        print(f"Error finding experience section or roles: {e_exp}")
        error_filename = f"profile_page_source_no_exp_section_{generate_timestamp()}.html"
        with open(error_filename, "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        print(f"Profile page HTML saved to '{error_filename}' due to experience section error.")
        return job_titles, company_names, company_descriptions, email

    processed = 0
    for index, role in enumerate(roles):
        if processed >= 2:
            break
        try:
            try:
                date_range_text = role.find_element(By.CSS_SELECTOR, ".FlFnZlIaBBqjmUkntQjGZaWDjaAiwAhClE").text.lower()
                print(f"Role {index+1} date range: {date_range_text}")
            except Exception:
                print(f"Date range element not found for role {index+1}.")

            try:
                job_title_element = role.find_element(By.CSS_SELECTOR, "h2[data-anonymize='job-title']")
                job_titles[processed] = job_title_element.text.strip() or "NA"
            except Exception as e_job:
                print(f"Job title not found for role {index+1}: {e_job}")
                job_titles[processed] = "NA"

            try:
                company_name_element = role.find_element(By.CSS_SELECTOR, "p[data-anonymize='company-name']")
                company_names[processed] = company_name_element.text.strip() or "NA"
            except Exception as e_comp:
                print(f"Company name not found for role {index+1}: {e_comp}")
                company_names[processed] = "NA"

            try:
                company_desc_element = role.find_element(By.CSS_SELECTOR, "div[data-anonymize='person-blurb']")
                company_descriptions[processed] = company_desc_element.text.strip() or "NA"
            except Exception as e_desc:
                print(f"Company description not found for role {index+1}: {e_desc}")
                company_descriptions[processed] = "NA"

            processed += 1
        except Exception as inner:
            print(f"Error processing role {index+1}: {inner}")
            continue

    return job_titles, company_names, company_descriptions, email



def scroll_down_page(driver, scroll_pause_time=2):
    """Scrolls down the page to load more content."""
    print("Starting scroll down...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    max_scrolls = 5

    while scrolls < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Reached bottom of page or no new content loaded.")
            break
        last_height = new_height
        scrolls += 1
        print(f"Scrolled down, scroll count: {scrolls}")
    print("Scrolling complete.")

# -------------------------------
# Groq Parsing & Function Classification

# Static list of functions
FUNCTIONS = [
    "Administrative", "Business Development", "Consulting", "Education", "Engineering",
    "Entrepreneurship", "Finance", "Healthcare Services", "Human Resources",
    "Information Technology", "Legal", "Marketing", "Media & Communication",
    "Military & Protective Services", "Operations", "Product Management",
    "Program & Project Management", "Purchasing", "Quality Assurance", "Real Estate",
    "Research", "Sales", "Support"
]

# Static list seniority level
SENIORITY = [
    "Entry Level","Director","In Training", "Experienced Manager", "Owner/Partner","Entry Level Manager","CXO",
    "Vice President","Strategic","Senior"
]

YEAR_EXPERIENCE = ["Less than 1 year","1-2 years","3-5 years","6-10 years","More than 10 years"]

INDUSTRY = [
    "Accounting", "Airlines & Aviation", "Alternative Dispute Resolution", "Alternative Medicine", "Animation",
    "Apparel & Fashion", "Architecture & Planning", "Arts & Crafts", "Automotive", "Aviation & Aerospace",
    "Banking", "Biotechnology", "Broadcast Media", "Building Materials", "Business Supplies & Equipment",
    "Capital Markets", "Chemicals", "Civic & Social Organization", "Civil Engineering", "Commercial Real Estate",
    "Computer & Network Security", "Computer Games", "Computer Hardware", "Computer Networking", "Computer Software",
    "Construction", "Consumer Electronics", "Consumer Goods", "Consumer Services", "Cosmetics",
    "Dairy", "Defense & Space", "Design", "Education Management", "E-learning",
    "Electrical & Electronic Manufacturing", "Entertainment", "Environmental Services", "Events Services", "Executive Office",
    "Facilities Services", "Farming", "Financial Services", "Fine Art", "Fishery",
    "Food & Beverages", "Food Production", "Fundraising", "Furniture", "Gambling & Casinos",
    "Glass, Ceramics & Concrete", "Government Administration", "Government Relations", "Graphic Design", "Health, Wellness & Fitness",
    "Higher Education", "Hospital & Health Care", "Hospitality", "Human Resources", "Import & Export",
    "Individual & Family Services", "Industrial Automation", "Information Services", "Information Technology & Services", "Insurance",
    "International Affairs", "International Trade & Development", "Internet", "Investment Banking", "Investment Management",
    "Judiciary", "Law Enforcement", "Law Practice", "Legal Services", "Legislative Office",
    "Leisure, Travel & Tourism", "Libraries", "Logistics & Supply Chain", "Luxury Goods & Jewelry", "Machinery",
    "Management Consulting", "Maritime", "Marketing & Advertising", "Market Research", "Mechanical or Industrial Engineering",
    "Media Production", "Medical Devices", "Medical Practice", "Mental Health Care", "Military",
    "Mining & Metals", "Motion Pictures & Film", "Museums & Institutions", "Music", "Nanotechnology",
    "Newspapers", "Nonprofit Organization Management", "Oil & Energy", "Online Media", "Outsourcing/Offshoring",
    "Package/Freight Delivery", "Packaging & Containers", "Paper & Forest Products", "Performing Arts", "Pharmaceuticals",
    "Philanthropy", "Photography", "Plastics", "Political Organization", "Primary/Secondary Education",
    "Printing", "Professional Training & Coaching", "Program Development", "Public Policy", "Public Relations & Communications",
    "Public Safety", "Publishing", "Railroad Manufacture", "Ranching", "Real Estate",
    "Recreational Facilities & Services", "Religious Institutions", "Renewables & Environment", "Research", "Restaurants",
    "Retail", "Security & Investigations", "Semiconductors", "Shipbuilding", "Sporting Goods",
    "Sports", "Staffing & Recruiting", "Supermarkets", "Telecommunications", "Textiles",
    "Think Tanks", "Tobacco", "Translation & Localization", "Transportation/Trucking/Railroad", "Utilities",
    "Venture Capital & Private Equity", "Veterinary", "Warehousing", "Wholesale", "Wine & Spirits",
    "Wireless", "Writing & Editing"
]


def clean_groq_output(raw_text):
    """
    Extract the JSON substring from the raw Groq output.
    """
    try:
        # Use regex to extract the JSON object.
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
    except Exception as e:
        print("Error cleaning Groq output:", e)
    # Fallback if extraction fails
    return {"function": raw_text.strip()}

def parse_candidate_criteria(criteria_text):
    """
    Send candidate criteria to the LLM via Groq and return structured search parameters.
    Expected output JSON includes a "function" key.
    """
    prompt = (
        "Extract the following detail from the candidate search criteria below and return it in valid JSON format "
        "with only the key 'function','seniority level' and no additional text.\n\n"
        "Candidate criteria:\n"
        f"\"{criteria_text}\"\n\n"
        "For example, the output should be exactly:\n"
        "{\n"
        '  "function": "Engineering",\n'
        '  "seniority level": "Experienced Manager"\n'
        "}\n"
    )

    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    raw_output = response.choices[0].message.content
    structured_data = clean_groq_output(raw_output)
    return structured_data



def classify_candidate_function(parsed_data):
    """
    Extract and classify the candidate function from parsed data.
    """
    candidate_function = parsed_data.get("function", "").strip()

    # Try an exact or case-insensitive match against the static list.
    for func in FUNCTIONS:
        if candidate_function.lower() == func.lower():
            return func

    # Otherwise, attempt a substring match.
    for func in FUNCTIONS:
        if candidate_function.lower() in func.lower():
            return func

    # Fallback: return the original value.
    return candidate_function


def classify_candidate_seniority_level(parsed_data):
    """
    Extract and classify the candidate function from parsed data.
    """
    candidate_seniority_level = parsed_data.get("seniority level", "").strip()

    # Try an exact or case-insensitive match against the static list.
    for senior in SENIORITY:
        if candidate_seniority_level.lower() == senior.lower():
            return senior

    # Otherwise, attempt a substring match.
    for senior in SENIORITY:
        if candidate_seniority_level.lower() in senior.lower():
            return senior

    # Fallback: return the original value.
    return candidate_seniority_level


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

def apply_function_filter(driver, candidate_function, candidate_seniority_level):

    driver.get("https://www.linkedin.com/sales/search/people?viewAllFilters=true")

    # Check and close overlay before interacting with filters
    close_overlay_if_present(driver)

    function_fieldset = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='FUNCTION']"))
    )
    function_fieldset.click()

    function_xpath = f'//div[contains(@aria-label, "{candidate_function}")]'
    print(f"Applying function filter using XPath: {function_xpath}")
    candidate_function_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, function_xpath))
    )
    candidate_function_button.click()
    print(f"Function filter '{candidate_function}' applied.")


    senior_fieldset = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']"))
    )
    senior_fieldset.click()

    senior_xpath = f'//div[contains(@aria-label, "{candidate_seniority_level}")]'
    print(f"Applying seniority filter using XPath: {senior_xpath}")
    candidate_senior_button = WebDriverWait(driver, 25).until(
        EC.element_to_be_clickable((By.XPATH, senior_xpath))
    )
    candidate_senior_button.click()
    print(f"Seniority filter '{candidate_seniority_level}' applied.")

# -------------------------------
# Scraping Main Workflow

def scrape_results_page(driver, max_leads=10):
    # Click Geography filter and set location to Jakarta.
    geography_fieldset = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='GEOGRAPHY']"))
    )
    geography_fieldset.click()

    # Locate the location input field using a retry mechanism.
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            location_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Add locations']"))
            )
            location_input.clear()
            location_input.send_keys("Jakarta")
            break
        except StaleElementReferenceException as e:
            print(f"Stale element on location input, retrying attempt {attempt+1}/{max_attempts}...")
            time.sleep(1)
            if attempt == max_attempts - 1:
                raise e

    location_suggestion = WebDriverWait(driver, 50).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@aria-label, 'Jakarta, Indonesia')]"))
    )
    location_suggestion.click()

    total_results = []  # Accumulator for all scraped leads
    page_number = 1

    while True:
        try:
            # Close any modal if present.
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, "button.close-modal")
                close_button.click()
                print("Closed modal")
            except NoSuchElementException:
                print("No modal found")

            print(f"Waiting for leads list to load on page {page_number}...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")),
                f"Timeout waiting for lead items on page {page_number}"
            )
            print(f"Leads list found on page {page_number}")
            time.sleep(5)  # Adjust if necessary

            scroll_down_page(driver)
            print("Scroll down on leads page completed.")

            lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
            print(f"Found {len(lead_items)} leads on page {page_number} after scroll down.")

            for index, item in enumerate(lead_items):
                if len(total_results) >= max_leads:
                    print("Reached target number of leads. Stopping.")
                    break  # Stop if we have reached the target number of leads

                print(f"--- Starting to process lead index: {index} on page {page_number} ---")
                person_name = "NA"
                person_title = "NA"
                linkedin_profile_link = "NA"
                company_name = "NA"
                location = "NA"

                try:
                    driver.execute_script("arguments[0].scrollIntoView(false);", item)
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of(item),
                        f"Timeout waiting for lead item to be visible on page {page_number}, item {index+1}"
                    )
                    # Extract the person's name.
                    try:
                        name_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']")
                        person_name = name_element.text.strip() if name_element else "NA"
                    except Exception as e:
                        print(f"Error extracting name: {e}")

                    # Extract the profile link.
                    try:
                        link_element = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='person-name']")
                        linkedin_profile_link = link_element.get_attribute("href") if link_element else "NA"
                    except Exception as e:
                        print(f"Error extracting profile link: {e}")

                    # Extract the job title.
                    try:
                        title_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='title']")
                        person_title = title_element.text.strip() if title_element else "NA"
                    except Exception as e:
                        print(f"Error extracting title: {e}")

                    # Extract the company name.
                    try:
                        company_element = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='company-name']")
                        company_name = company_element.text.strip() if company_element else "NA"
                    except Exception as e:
                        print(f"Error extracting company: {e}")

                    # Extract the location.
                    try:
                        location_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='location']")
                        location = location_element.text.strip() if location_element else "NA"
                    except Exception as e:
                        print(f"Error extracting location: {e}")

                    print(f"Processing: {person_name} on page {page_number}, item {index + 1}")

                    # --- Click on the lead's name to go to the intermediate page ---
                    try:
                        person_name_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']")
                        person_name_element.click()
                        print(f"Clicked on person name: {person_name}")
                        intermediate_page_start_time = time.time() # Start timing intermediate page load

                        intermediate_page_loaded = False
                        intermediate_page_timeout = False
                        while time.time() - intermediate_page_start_time < 60: # Wait max 60 seconds for intermediate page to load
                            try:
                                # Check for a specific element on the intermediate page to confirm load
                                WebDriverWait(driver, 5).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[aria-label='Open profile in new tab']")) # Example: Wait for the icon itself
                                )
                                intermediate_page_loaded = True
                                print(f"Intermediate page loaded successfully for {person_name} after {(time.time() - intermediate_page_start_time):.2f} seconds.")
                                break  # Exit the loop if the page is loaded
                            except TimeoutException:
                                print(f"Waiting for intermediate page to load for {person_name}...") # Log waiting attempts
                                time.sleep(2) # Wait a bit longer before retrying
                        else: # else block of while loop executes if loop completes without break
                            intermediate_page_timeout = True # Indicate timeout

                        if intermediate_page_timeout: # Check flag after loop
                            raise TimeoutException(f"Timeout waiting for intermediate page to load for {person_name}")


                        # --- Click "Open profile in new tab" icon on the intermediate page ---
                        try:
                            print(f"--- Attempting to find 'Open profile in new tab' icon on intermediate page for {person_name} ---") # Added log
                            view_profile_icon_intermediate_page = WebDriverWait(driver, 60).until( # Increased timeout to 60 seconds
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[aria-label='Open profile in new tab']")) # Using aria-label from HTML snippet
                            )
                            print(f"--- 'Open profile in new tab' icon FOUND on intermediate page for {person_name} ---") # Log after wait success
                            view_profile_icon_intermediate_page.click()
                            print(f"Clicked 'Open profile in new tab' icon on intermediate page for {person_name}")
                            time.sleep(5) # Wait for the actual profile page to load

                            # --- Click "View profile" button (link with icon) on the profile page ---
                            try:
                                print(f"--- Attempting to find 'More actions' button (icon) on profile page for {person_name} ---") # Added log
                                more_actions_button_profile_page = WebDriverWait(driver, 30).until( # Increased timeout
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='See more actions for']")) # Generic selector
                                )
                                print(f"--- 'More actions' button (icon) FOUND on profile page for {person_name} ---")

                                # --- Attempt 1: Direct click ---
                                try:
                                    more_actions_button_profile_page.click()
                                    print(f"Clicked 'More actions' button (icon) on profile page using direct click for {person_name}")
                                    time.sleep(1) # Wait for dropdown

                                except ElementClickInterceptedException as eci_direct_click:
                                    print(f"ElementClickInterceptedException on direct click for 'More actions' button (icon) for {person_name}: {eci_direct_click}")

                                    # --- Attempt 2: JavaScript click ---
                                    try:
                                        driver.execute_script("arguments[0].click();", more_actions_button_profile_page)
                                        print(f"Clicked 'More actions' button (icon) on profile page using JavaScript click for {person_name}")
                                        time.sleep(1)  # Wait for dropdown
                                    except Exception as js_click_e:
                                        print(f"JavaScript click also failed for 'More actions' button (icon) for {person_name}: {js_click_e}")

                                        # --- Attempt 3: ActionChains click ---
                                        try:
                                            actions = webdriver.ActionChains(driver)
                                            actions.move_to_element(more_actions_button_profile_page).click().perform()
                                            print(f"Clicked 'More actions' button (icon) on profile page using ActionChains for {person_name}")
                                            time.sleep(1)  # Wait for dropdown
                                        except Exception as action_click_e:
                                            print(f"ActionChains click also failed for 'More actions' button (icon) for {person_name}: {action_click_e}")
                                            raise # Re-raise the last exception to trigger timeout handling


                                    # --- Find and click "View LinkedIn profile" link in the dropdown on profile page ---
                                    try:
                                        view_profile_link_profile_page = WebDriverWait(driver, 20).until(
                                            EC.element_to_be_clickable((By.XPATH, "//div[contains(@aria-expanded, 'true') and contains(@aria-controls, 'hue-menu-')]//a[contains(text(), 'View LinkedIn profile')]")) # Reusing XPath
                                        )
                                        view_profile_link_profile_page.click()
                                        print(f"Clicked 'View LinkedIn profile' link on profile page for {person_name}")
                                        time.sleep(5) # Wait for profile details to load (though we are already on profile page)


                                        # Now we are (again) on the actual profile page (after clicking "View LinkedIn profile" in dropdown - redundant step?)
                                        job_titles, company_names_details, company_descriptions, email = get_linkedin_profile_details(driver, driver.current_url)
                                        print(f"Back from get_linkedin_profile_details for {person_name}")
                                        # No more driver.back() calls here as we are done with profile page scraping in this flow

                                    except TimeoutException as dropdown_view_profile_timeout:
                                        print(f"Timeout waiting for 'View LinkedIn profile' button (icon) on PROFILE page for {person_name}: {dropdown_view_profile_timeout}")
                                        driver.back() # Go back to intermediate page
                                        driver.back() # Go back to search results
                                        print("Navigated back to search results due to timeout for 'View LinkedIn profile' button (icon) on PROFILE page.")
                                    except NoSuchElementException as no_dropdown_view_profile_element:
                                        print(f"Could not find 'View LinkedIn profile' button (icon) on PROFILE page for {person_name}: {no_dropdown_view_profile_element}")
                                        driver.back() # Go back to intermediate page
                                        driver.back() # Go back to search results
                                        print("Navigated back to search results because 'View LinkedIn profile' button (icon) on PROFILE page not found.")


                            except TimeoutException as more_actions_profile_timeout:
                                print(f"Timeout waiting for 'More actions' button (icon) on PROFILE page for {person_name}: {more_actions_profile_timeout}")
                                error_filename = f"profile_page_source_timeout_more_actions_profile_{generate_timestamp()}.html" # Specific filename
                                with open(error_filename, "w", encoding="utf-8") as file:
                                    file.write(driver.page_source)
                                print(f"Profile page HTML saved to '{error_filename}' due to timeout finding 'More actions' icon on PROFILE page.") # Specific log
                                driver.save_screenshot(f"profile_page_screenshot_timeout_more_actions_profile_{generate_timestamp()}.png") # Save screenshot as well
                                driver.back() # Go back to search results
                                print("Navigated back to search results due to timeout finding 'More actions' icon on PROFILE page.")
                            except NoSuchElementException as no_more_actions_profile_element:
                                print(f"Could not find 'More actions' button (icon) on PROFILE page for {person_name}: {no_more_actions_profile_element}")
                                driver.back() # Go back to search results
                                print("Navigated back to search results because 'More actions' icon on PROFILE page not found.")


                        except TimeoutException as view_profile_icon_timeout:
                            print(f"Timeout waiting for 'Open profile in new tab' icon on intermediate page for {person_name}: {view_profile_icon_timeout}")
                            error_filename = f"intermediate_page_source_timeout_view_profile_icon_{generate_timestamp()}.html" # Specific filename
                            with open(error_filename, "w", encoding="utf-8") as file:
                                file.write(driver.page_source)
                            print(f"Intermediate page HTML saved to '{error_filename}' due to timeout finding 'Open profile in new tab' icon on intermediate page.") # Specific log
                            driver.save_screenshot(f"intermediate_page_screenshot_timeout_view_profile_icon_{generate_timestamp()}.png") # Save screenshot
                            driver.back() # Go back to search results
                            print("Navigated back to search results due to timeout for 'Open profile in new tab' icon.")

                        except NoSuchElementException as no_view_profile_element:
                            print(f"Could not find 'Open profile in new tab' icon on intermediate page for {person_name}: {no_view_profile_element}")
                            driver.back() # Go back to search results
                            print("Navigated back to search results because 'Open profile in new tab' icon on intermediate page not found.")


                    except NoSuchElementException as no_name_element:
                        print(f"Could not find person name element to click for {person_name}: {no_name_element}")
                    except ElementClickInterceptedException as name_click_intercepted:
                        print(f"Click intercepted while trying to click person name for {person_name}: {name_click_intercepted}")
                    except TimeoutException as name_timeout_exception:
                        print(f"Timeout waiting after clicking person name for {person_name}: {name_timeout_exception}")


                    total_results.append({
                        'person_name': person_name,
                        'person_title': person_title,
                        'linkedin_profile_link': linkedin_profile_link,
                        'job_title_1': job_titles[0],
                        'job_title_2': job_titles[1],
                        'company_name': company_name,
                        'location': location,
                    })
                    time.sleep(random.uniform(1, 3))
                except StaleElementReferenceException as stale_e:
                    print(f"StaleElementReferenceException on page {page_number}, item {index+1}: {stale_e}")
                    total_results.append({
                        'person_name': "NA",
                        'person_title': "NA",
                        'linkedin_profile_link': "NA",
                        'job_title_1': "NA",
                        'job_title_2': "NA",
                        'company_name_1': "NA",
                        'company_name_2': "NA",
                        'company_description_1': "NA",
                        'company_description_2': "NA",
                        'email': "NA",
                        'company_name': "NA",
                        'location': "NA",
                    })
                except Exception as e:
                    print(f"Failed to process item on page {page_number}, item {index+1}: {e}")
                    total_results.append({
                        'person_name': "NA",
                        'person_title': "NA",
                        'linkedin_profile_link': "NA",
                        'job_title_1': "NA",
                        'job_title_2': "NA",
                        'company_name_1': "NA",
                        'company_name_2': "NA",
                        'company_description_1': "NA",
                        'company_description_2': "NA",
                        'email': "NA",
                        'company_name': "NA",
                        'location': "NA",
                    })
                print(f"--- Finished processing lead index: {index} on page {page_number} ---")

            if len(total_results) >= max_leads:
                # Break out of the page loop if we've reached our target.
                break

            try:
                print("Attempting to go to next page...")
                next_button = driver.find_element(By.CSS_SELECTOR, "button.artdeco-pagination__button--next")
                if next_button.is_enabled():
                    next_button.click()
                    page_number += 1
                    print(f"Clicked next page, moving to page {page_number}")
                    time.sleep(random.uniform(2, 4))
                else:
                    print("Next button is not enabled, assuming last page")
                    break
            except NoSuchElementException:
                print("Next button not found, assuming last page")
                break
        except TimeoutException as timeout_page_exception:
            print(f"Timeout occurred while waiting for leads list on page {page_number}: {timeout_page_exception}")
            error_filename = f"page_source_timeout_page_{page_number}_{generate_timestamp()}.html"
            with open(error_filename, "w", encoding="utf-8") as file:
                file.write(driver.page_source)
            print(f"HTML saved to '{error_filename}'")
            driver.save_screenshot(f"screenshot_page_{page_number}_{generate_timestamp()}.png")
            print(f"Screenshot saved to 'screenshot_page_{page_number}_{generate_timestamp()}.png'")
            break
        except Exception as page_exception:
            print(f"Error during page scraping on page {page_number}: {page_exception}")
            break

    write_results_to_csv(total_results, 'prospects_10.csv')
    print(f"Data written to CSV for the scraped leads.")



# -----------------------
# Main Workflow
# -----------------------

if __name__ == "__main__":
# def scraping_leads():
    # Load configuration from config.json (should include email and password)
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    # Configure Chrome options.
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

    # Uncomment the following line to run headless:
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), 
        options=chrome_options
    )
    try:
        #Log in to LinkedIn.
        login_to_site(driver, config)

        driver.get("https://www.linkedin.com/sales/search/people?viewAllFilters=true")

        # Candidate criteria input
        # baru bisa sampai level seniority
        criteria_text = (
            "Looking for [Business Development] for [10] leads. "
            "The leads are ideally to possess a [Experienced Manager] level" # Removed extra criteria for now for testing
        )

        #Parse dari groq
        parsed_data = parse_candidate_criteria(criteria_text)
        print("Parsed candidate criteria:", parsed_data)

        # Classify the candidate function.
        candidate_function = classify_candidate_function(parsed_data)
        candidate_seniority_level = classify_candidate_seniority_level(parsed_data)
        print("Classified Candidate Function:", candidate_function)
        print("Classified Candidate Seniority:", candidate_seniority_level)


        apply_function_filter(driver, candidate_function,candidate_seniority_level)

        scrape_results_page(driver)

    finally:
        driver.quit()