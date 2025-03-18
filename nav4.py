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
from fuzzywuzzy import process
import logging
 


# -------------------------------
# Utility Functions
#global driver
driver = None

def generate_timestamp():
    """Generates a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def login_to_site():
    global driver
    session_url = input("Enter the session URL: ")
    session_id = input("Enter the session ID: ")

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Keep headless for now, but can test without
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Remote(command_executor=session_url, options=chrome_options)
        driver.session_id = session_id
        print(f"Driver initialized with session ID: {driver.session_id}") # Debug print session ID
        return True
    except Exception as e:
        print(f"Error in login_to_site: {e}")
        return False

# -------------------------------
# Groq Parsing & Function Classification

# Static list of functions
# optional
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

YEAR_EXPERIENCE = ["Less than 1 year","1 to 2 years","3 to 5 years","6 to 10 years","More than 10 years"]

INDUSTRY = [
    "Accounting", "Airlines & Aviation", "Alternative Dispute Resolution", "Alternative Medicine", "Animation",
    "Apparel & Fashion", "Architecture & Planning", "Arts & Crafts", "Automotive", "Aviation & Aerospace",
    "Banking", "Biotechnology", "Broadcast Media", "Building Materials", "Business Supplies & Equipment",
    "Capital Markets", "Chemicals", "Civic & Social Organization", "Civil Engineering", "Commercial Real Estate",
    "Writing & Editing"
]


def clean_groq_output(raw_text):
    try:
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
        else:
            logging.warning("No JSON object found in Groq output.")
            return None
    except json.JSONDecodeError as e:
        logging.error(f"JSONDecodeError cleaning Groq output: {e}")
        logging.debug(f"Raw Groq output that failed to parse: {raw_text}")
        return None
    except Exception as e:
        logging.exception("Unexpected error cleaning Groq output:")
        return None

def parse_candidate_criteria(criteria_text):
    prompt = (
        "Your task is to extract candidate search criteria from the text provided and structure it as a valid JSON object.\n"
        "The JSON object should contain the following keys:\n"
        "- 'job title':  The desired job title of the candidate.\n" # Changed to "job title"
        "- 'seniority level': The desired seniority level of the candidate.\n"
        "- 'industry': The industry or industries the candidate should have experience in.\n"
        "- 'years of experience': The minimum number of years of relevant experience required.\n"
        "\n"
        "If a specific criterion is NOT mentioned in the candidate criteria text, set its corresponding JSON value to null.\n"
        "Do not include any text or explanations outside of the JSON object in your response.\n"
        "\n"
        "Candidate criteria text:\n"
        f"\"{criteria_text}\"\n"
        "\n"
        "Example of the desired JSON output format:\n"
        "{\n"
        '  "job title": "Head of Sustainability",\n' # Changed to "job title" in example
        '  "seniority level": "Entry Level",\n'
        '  "industry": "Accounting",\n'
        '  "years of experience": "Less than 1 year"\n'
        "}\n"
    )

    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    raw_output = response.choices[0].message.content
    print(f"Raw Groq Output: {raw_output}") # Log raw Groq output!
    structured_data = clean_groq_output(raw_output)
    return structured_data

def get_closest_match(extracted_value, options_list, score_cutoff=80):
    print(f"get_closest_match called with extracted_value: {extracted_value}, type: {type(extracted_value)}") # Debug print (original value & type)
    if extracted_value is None:
        return None

    # Explicitly convert extracted_value to string before using fuzzywuzzy
    extracted_value_str = str(extracted_value)
    print(f"After str() conversion, extracted_value_str: {extracted_value_str}, type: {type(extracted_value_str)}") # Debug print (after conversion)

    print(f"Options list (YEAR_EXPERIENCE): {options_list}") # Print options list

    best_match_tuple = process.extractOne(extracted_value_str, options_list) # Get tuple
    if best_match_tuple: # Check if not None
        best_match, score = best_match_tuple # Unpack tuple
        print(f"fuzzywuzzy result: best_match: {best_match}, score: {score}") # Print fuzzywuzzy result
        if score >= score_cutoff:
            return best_match
    else:
        print("fuzzywuzzy returned None (no match found)") # Print if fuzzywuzzy returns None

    return None

def apply_job_title_filter(driver, parsed_data): # ADD parsed_data argument
    print("Applying Job Title Filter...")
    driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true') # Consider removing this line, navigation already done in main

    time.sleep(10)

        # filter function
    job_title_fieldset = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='CURRENT_TITLE']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", job_title_fieldset)  # crucial
    time.sleep(1)
    job_title_fieldset.click()

    # isi value (job title input)
    job_title_input_xpath = (
        "//fieldset[@data-x-search-filter='CURRENT_TITLE']//input[@type='text']"
    )
    job_title_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, job_title_input_xpath))
    )
    extracted_job_title = parsed_data.get("job title")
    job_title_input.send_keys(extracted_job_title)
    print(f"Typed '{extracted_job_title}' into the job title filter input.")
    time.sleep(1)

    # Click "Include" button in dropdown
    include_button_xpath = f'//div[@aria-label="Include “{extracted_job_title}” in Current job title filter"]' # Dynamic XPath

    try:
        include_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, include_button_xpath))
        )
        include_button.click()
        print(f"Clicked 'Include' for job title '{extracted_job_title}'.")
        time.sleep(2) # Add a small wait after clicking include
    except TimeoutException:
        print(f"Timeout: 'Include' button for job title '{extracted_job_title}' not found or clickable.")
    except NoSuchElementException:
        print(f"NoSuchElement: 'Include' button for job title '{extracted_job_title}' not found.")
    except Exception as e:
        print(f"Error clicking 'Include' button: {e}")

    return

def apply_seniority_filter(driver, parsed_data, matched_seniority): # ADD matched_seniority argument
    print(f"Applying Seniority Level Filter (clicking 'Include' button - revised) for: '{matched_seniority}'...") # Updated print statement
    seniority_level = parsed_data.get("seniority level") # Keep this for logging purposes if needed
    if not matched_seniority: # Check matched_seniority now
        print("No matched seniority level, skipping filter.\n")
        return

    seniority_fieldset_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']"
    expand_seniority_button_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']//button[@aria-expanded='false'][.//span[contains(text(), 'Expand')]]"
    # More Specific XPath for "Include" button - targeting within the dropdown list
    include_seniority_button_xpath = f'//li[@role="option"]//div[@aria-label="Include “{matched_seniority}” in Seniority level filter"]' # Use matched_seniority in XPath


    try:
        seniority_fieldset = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.XPATH, seniority_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seniority_fieldset)
        time.sleep(1)
        seniority_fieldset.click() # Expand the filter

        # 1. Click "Expand" button
        expand_button = WebDriverWait(driver, 30).until( # Increased timeout to 30s
            EC.element_to_be_clickable((By.XPATH, expand_seniority_button_xpath))
        )
        expand_button.click()
        print("Clicked 'Expand' button for Seniority Level filter.")
        time.sleep(2) # Wait for options to load

        # 2. Find and click "Include" button
        print(f"Attempting to find 'Include' button for matched seniority: '{matched_seniority}' using XPath: {include_seniority_button_xpath}") # Debug log BEFORE finding

        include_button = WebDriverWait(driver, 30).until( # Increased timeout to 30s
            EC.element_to_be_clickable((By.XPATH, include_seniority_button_xpath))
        )

        print(f"Found 'Include' button element: {include_button}") # Debug log AFTER finding

        print("Attempting to click 'Include' button (regular click)...") # Debug log BEFORE click
        include_button.click() # Try regular click first
        print(f"Clicked 'Include' button for matched seniority level '{matched_seniority}' (regular click).") # Updated log

        time.sleep(2)

    except TimeoutException:
        print(f"Timeout: 'Include' button for matched seniority level '{matched_seniority}' not found or clickable.") # Updated log
    except NoSuchElementException:
        print(f"NoSuchElement: 'Include' button for matched seniority level '{matched_seniority}' not found.") # Updated log
    except ElementClickInterceptedException: # Catch interception exception
        print(f"ElementClickIntercepted: 'Include' button click intercepted! Trying JavaScript click...")
        try:
            driver.execute_script("arguments[0].click();", include_button) # JavaScript click fallback
            print(f"Clicked 'Include' button for matched seniority level '{matched_seniority}' using JavaScript click.") # Updated log
            time.sleep(2)
        except Exception as js_click_error:
            print(f"JavaScript click also failed: {js_click_error}")

    except Exception as e:
        print(f"Error applying seniority level filter (clicking 'Include' button) for matched seniority level '{matched_seniority}': {e}") # Updated log
    print(f"Seniority Level Filter Applied for matched seniority level '{matched_seniority}' (clicking 'Include' button - revised).\n") # Updated log




def apply_industry_filter(driver, parsed_data):
    print("Applying Industry Filter...")
    industry = parsed_data.get("industry")
    if not industry:
        print("No industry extracted, skipping filter.\n") # Added newline
        return

    industry_fieldset_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']" # **VERIFY THIS XPATH**
    industry_input_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']//input[@type='text']" # **VERIFY THIS XPATH**
    include_industry_button_xpath = f'//div[@aria-label="Include “{industry}” in Industry filter"]' # **VERIFY THIS XPATH**


    try:
        industry_fieldset = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.XPATH, industry_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", industry_fieldset)
        time.sleep(1)
        industry_fieldset.click()

        industry_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, industry_input_xpath))
        )
        industry_input.send_keys(industry)
        print(f"Typed '{industry}' into the industry filter input.")
        time.sleep(1)

        include_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, include_industry_button_xpath))
        )
        include_button.click()
        print(f"Clicked 'Include' for industry '{industry}'.")
        time.sleep(2)

    except TimeoutException:
        print(f"Timeout: Elements for industry filter not found or clickable.")
    except NoSuchElementException:
        print(f"NoSuchElement: Elements for industry filter not found.")
    except Exception as e:
        print(f"Error applying industry filter: {e}")
    print("Industry Filter Applied.\n") # Added newline


def apply_years_experience_filter(driver, parsed_data, matched_experience):
    print(f"Applying Years of Experience Filter for: '{matched_experience}'...")
    if not matched_experience:
        print("No matched years of experience, skipping filter.\n")
        return

    years_experience_fieldset_xpath = "//fieldset[@data-x-search-filter='YEARS_AT_CURRENT_COMPANY']"
    years_experience_dropdown_list_xpath = '//ul[@role="listbox" and @aria-label="Years in current company filter suggestions"]'
    # Adjusted XPath: targeting the <li> (or its inner <div>) using normalize-space
    years_experience_option_xpath = f'//li[@role="option" and contains(normalize-space(.), "{matched_experience}")]/div'

    try:
        # Wait for and click the fieldset to expand the dropdown
        fieldset = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, years_experience_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", fieldset)
        time.sleep(1)
        fieldset.click()

        print("Waiting for Years of Experience dropdown list to be visible...")
        dropdown_list = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, years_experience_dropdown_list_xpath))
        )
        print("Dropdown list is visible.")

        print(f"Searching for option element for '{matched_experience}' using XPath: {years_experience_option_xpath}")
        option_element = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, years_experience_option_xpath))
        )
        print("Option element found. Outer HTML:", option_element.get_attribute('outerHTML'))
        time.sleep(1)
        driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
        time.sleep(1)

        print("Attempting to click the years of experience option...")
        try:
            option_element.click()
            print(f"Clicked years of experience option: '{matched_experience}'.")
        except ElementClickInterceptedException:
            print("Click intercepted; attempting ActionChains click...")
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).move_to_element(option_element).click().perform()
            print(f"Clicked years of experience option using ActionChains: '{matched_experience}'.")
        time.sleep(2)

    except TimeoutException:
        timestamp = generate_timestamp()
        screenshot_filename = f"timeout_screenshot_years_experience_{timestamp}.png"
        driver.save_screenshot(screenshot_filename)
        print(f"Timeout: Option for '{matched_experience}' not found. Screenshot saved as: {screenshot_filename}")
    except NoSuchElementException:
        timestamp = generate_timestamp()
        screenshot_filename = f"nosuchelement_screenshot_years_experience_{timestamp}.png"
        driver.save_screenshot(screenshot_filename)
        print(f"NoSuchElement: Option for '{matched_experience}' not found. Screenshot saved as: {screenshot_filename}")
    except Exception as e:
        print(f"Error applying filter: {e}")
    print(f"Filter applied for: '{matched_experience}'.\n")

# -----------------------
# Main Workflow
# -----------------------

if __name__ == "__main__":
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    if login_to_site():
        print("Login successful.")
        try:
            driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true')
            print("Successfully navigated to LinkedIn Sales Navigator search page.")
        except Exception as e:
            print(f"Error navigating to URL after login: {e}")

        # Candidate criteria input
        criteria_text = """
        Looking for [Head of Sustainability] for [10] leads
        The leads are ideally to possess a [Experienced Manager] level
        have an experience in [Accounting]industry
        with a minimum [3] years of experience

        It is good if the leads also have:
        1. Experience in facilities procurement
        2. Interest in waste management and circular economy
        3. Knowledge of sustainability practices
        """

        parsed_data = parse_candidate_criteria(criteria_text)

        print(f"Parsed data from Groq: {parsed_data}") # Ensure this print statement is still there

        # --- Check parsed_data values BEFORE get_closest_match ---
        job_title_value = parsed_data.get("job title")
        seniority_value = parsed_data.get("seniority level")
        industry_value = parsed_data.get("industry")
        experience_value = parsed_data.get("years of experience")

        print(f"Job Title Value from parsed_data: {job_title_value}, Type: {type(job_title_value)}")
        print(f"Seniority Value from parsed_data: {seniority_value}, Type: {type(seniority_value)}")
        print(f"Industry Value from parsed_data: {industry_value}, Type: {type(industry_value)}")
        print(f"Experience Value from parsed_data: {experience_value}, Type: {type(experience_value)}")

        print(f"YEAR_EXPERIENCE List in main: {YEAR_EXPERIENCE}") # Print YEAR_EXPERIENCE in main


        matched_job_title = job_title_value # No matching for job title
        matched_seniority = get_closest_match(seniority_value, SENIORITY)
        matched_industry = get_closest_match(industry_value, INDUSTRY, score_cutoff=70)
        matched_experience = get_closest_match(experience_value, YEAR_EXPERIENCE, score_cutoff=60)

        print("Extracted Job Title:", matched_job_title)
        print("Matched Seniority:", matched_seniority)
        print("Matched Industry:", matched_industry)
        print("Matched Years of Experience:", matched_experience)


        apply_job_title_filter(driver, parsed_data)
        apply_seniority_filter(driver, parsed_data, matched_seniority)
        apply_years_experience_filter(driver, parsed_data, matched_experience)
        apply_industry_filter(driver, parsed_data)

    else:
        print("Login failed, exiting.")