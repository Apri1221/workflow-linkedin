import csv
import json
import re
import os
import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from groq import Groq
from dotenv import load_dotenv
from fuzzywuzzy import process
import pandas as pd

# -------------------------------
# Constants & Static Lists
WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3

# (You may eventually replace these with values from a constants module.)
FUNCTIONS = [
    "Administrative", "Business Development", "Consulting", "Education", "Engineering",
    "Entrepreneurship", "Finance", "Healthcare Services", "Human Resources",
    "Information Technology", "Legal", "Marketing", "Media & Communication",
    "Military & Protective Services", "Operations", "Product Management",
    "Program & Project Management", "Purchasing", "Quality Assurance", "Real Estate",
    "Research", "Sales", "Support"
]
SENIORITY = [
    "Entry Level", "Director", "In Training", "Experienced Manager", "Owner/Partner", "Entry Level Manager", "CXO",
    "Vice President", "Strategic", "Senior"
]
YEAR_EXPERIENCE = ["Less than 1 year", "1 to 2 years", "3 to 5 years", "6 to 10 years", "More than 10 years"]
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

# -------------------------------
# Utility Functions

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

def function_filter_retry(driver, filter_xpath, option_xpath, placeholder_text=None, input_value=None):
    """
    Generic retry function for filters.
    Waits for the filter field to be clickable, optionally sends input, and clicks the desired option.
    """
    close_overlay_if_present(driver)
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, filter_xpath))
    ).click()
    if placeholder_text and input_value:
        for attempt in range(MAX_RETRIES):
            try:
                input_field = WebDriverWait(driver, SHORT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, f"//input[@placeholder='{placeholder_text}']"))
                )
                input_field.clear()
                input_field.send_keys(input_value)
                break
            except StaleElementReferenceException:
                print(f"Stale element on input, retrying attempt {attempt+1}/{MAX_RETRIES}...")
                time.sleep(1)
                if attempt == MAX_RETRIES - 1:
                    raise
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    ).click()
    time.sleep(1)

def get_closest_match(extracted_value, options_list, score_cutoff=80):
    """Uses fuzzy matching to return the closest option from a list."""
    if extracted_value is None:
        return None
    extracted_value_str = str(extracted_value)
    best_match_tuple = process.extractOne(extracted_value_str, options_list)
    if best_match_tuple:
        best_match, score = best_match_tuple
        if score >= score_cutoff:
            return best_match
    return None

def parse_candidate_criteria(criteria_text):
    """
    Uses Groq LLM to extract candidate criteria from the given text.
    Returns a JSON object with keys: 'job title', 'seniority level', 'industry', 'years of experience'.
    If a key is not mentioned, its value will be null.
    """
    prompt = (
        "Your task is to extract candidate search criteria from the text provided and structure it as a valid JSON object.\n"
        "The JSON object should contain the following keys:\n"
        "- 'job title':  The desired job title of the candidate.\n"
        "- 'seniority level': The desired seniority level of the candidate.\n"
        "- 'industry': The industry or industries the candidate should have experience in.\n"
        "- 'years of experience': The minimum number of years of relevant experience required.\n"
        "If a specific criterion is NOT mentioned, set its corresponding JSON value to null.\n"
        "Candidate criteria text:\n"
        f"\"{criteria_text}\"\n"
    )
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    raw_output = response.choices[0].message.content
    logging.info(f"Raw Groq Output: {raw_output}")
    return clean_groq_output(raw_output)

def clean_groq_output(raw_text):
    """Cleans the Groq output and returns a parsed JSON object."""
    try:
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
        else:
            logging.warning("No JSON object found in Groq output.")
            return {}
    except json.JSONDecodeError as e:
        logging.error(f"JSONDecodeError: {e}")
        return {}
    except Exception as e:
        logging.exception("Unexpected error cleaning Groq output:")
        return {}

def llm_analyze_criteria(criteria_text):
    """
    Uses Groq LLM to analyze the candidate criteria text for 'good-to-have' criteria.
    Returns a JSON object with key 'good_to_have' containing a list of applicable criteria.
    """
    prompt = (
        "Analyze the following candidate criteria text and determine which of the following 'good-to-have' criteria are applicable:\n"
        "1. Experience in facilities procurement\n"
        "2. Interest in waste management and circular economy\n"
        "3. Knowledge of sustainability practices\n\n"
        "Candidate criteria text:\n"
        f"\"{criteria_text}\"\n\n"
        "Return a JSON object with a key 'good_to_have' whose value is a list of the applicable criteria (choose from the above three) based on your analysis. "
        "Do not include any extra text."
    )
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    raw_output = response.choices[0].message.content
    logging.info(f"Raw LLM Good-to-Have Output: {raw_output}")
    try:
        return json.loads(raw_output)
    except Exception as e:
        logging.error(f"Error parsing LLM output for good-to-have criteria: {e}")
        return {"good_to_have": []}

def apply_filters(driver, parsed_data, matched_seniority, matched_industry, matched_experience):
    """
    Applies the various filters on LinkedIn Sales Navigator.
    Uses separate functions to filter by job title, seniority, industry, and years of experience.
    """
    # Navigate to the search page and close any overlays.
    driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true')
    close_overlay_if_present(driver)
    time.sleep(5)

    # --- Job Title Filter ---
    try:
        print("Applying Job Title Filter...")
        job_title_fieldset = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='CURRENT_TITLE']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", job_title_fieldset)
        job_title_fieldset.click()
        job_title_input_xpath = "//fieldset[@data-x-search-filter='CURRENT_TITLE']//input[@type='text']"
        job_title_input = WebDriverWait(driver, SHORT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, job_title_input_xpath))
        )
        extracted_job_title = parsed_data.get("job title")
        job_title_input.send_keys(extracted_job_title)
        time.sleep(1)
        include_button_xpath = f'//div[@aria-label="Include “{extracted_job_title}” in Current job title filter"]'
        include_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, include_button_xpath))
        )
        include_button.click()
        print(f"Job Title filter applied for '{extracted_job_title}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying job title filter: {e}")

    # --- Seniority Filter ---
    try:
        print(f"Applying Seniority Filter for: '{matched_seniority}'...")
        seniority_fieldset_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']"
        expand_seniority_button_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']//button[@aria-expanded='false'][.//span[contains(text(), 'Expand')]]"
        include_seniority_button_xpath = f'//li[@role="option"]//div[@aria-label="Include “{matched_seniority}” in Seniority level filter"]'
        seniority_fieldset = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, seniority_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seniority_fieldset)
        seniority_fieldset.click()
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, expand_seniority_button_xpath))
        ).click()
        time.sleep(2)
        include_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, include_seniority_button_xpath))
        )
        include_button.click()
        print(f"Seniority filter applied for '{matched_seniority}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying seniority filter: {e}")

    # --- Industry Filter ---
    try:
        print("Applying Industry Filter...")
        industry = parsed_data.get("industry")
        if industry:
            industry_fieldset_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']"
            industry_input_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']//input[@type='text']"
            include_industry_button_xpath = f'//div[@aria-label="Include “{industry}” in Industry filter"]'
            industry_fieldset = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, industry_fieldset_xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", industry_fieldset)
            industry_fieldset.click()
            industry_input = WebDriverWait(driver, SHORT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, industry_input_xpath))
            )
            industry_input.send_keys(industry)
            time.sleep(1)
            include_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, include_industry_button_xpath))
            )
            include_button.click()
            print(f"Industry filter applied for '{industry}'.")
            time.sleep(2)
        else:
            print("No industry extracted; skipping industry filter.")
    except Exception as e:
        print(f"Error applying industry filter: {e}")

    # --- Years of Experience Filter ---
    try:
        print(f"Applying Years of Experience Filter for: '{matched_experience}'...")
        years_experience_fieldset_xpath = "//fieldset[@data-x-search-filter='YEARS_AT_CURRENT_COMPANY']"
        years_experience_dropdown_list_xpath = '//ul[@role="listbox" and @aria-label="Years in current company filter suggestions"]'
        years_experience_option_xpath = f'//li[@role="option" and contains(normalize-space(.), "{matched_experience}")]/div'
        fieldset = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, years_experience_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", fieldset)
        fieldset.click()
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.visibility_of_element_located((By.XPATH, years_experience_dropdown_list_xpath))
        )
        option_element = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, years_experience_option_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
        time.sleep(1)
        option_element.click()
        print(f"Years of experience filter applied for '{matched_experience}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying years of experience filter: {e}")

def scroll_until_loaded(driver, pause_time=3, max_attempts=10):
    """Scrolls down the page until no new lead items are loaded."""
    last_count = 0
    attempts = 0
    while attempts < max_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)
        lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        current_count = len(lead_items)
        print(f"Scroll attempt {attempts+1}: Found {current_count} lead items")
        if current_count == last_count:
            print("No new leads loaded; stopping scrolling.")
            break
        last_count = current_count
        attempts += 1
    return last_count

def scrape_leads(driver):
    """
    Scrolls the page to load all lead items and scrapes them.
    Returns a list of dictionaries with lead details.
    """
    print("Scrolling to load all leads...")
    scroll_until_loaded(driver, pause_time=3, max_attempts=10)
    print("Finished scrolling. Now scraping leads...")
    leads_data = []
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3"))
        )
        lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        print(f"Found {len(lead_items)} lead items on the page.")
        for index, item in enumerate(lead_items):
            name = "NA"
            title = "NA"
            profile_link = "NA"
            company = "NA"
            location = "NA"
            # Extract Name
            try:
                name_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='person-name']")
                name = name_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Primary name extraction failed: {e}")
                try:
                    headshot_anchor = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']")
                    img = headshot_anchor.find_element(By.TAG_NAME, "img")
                    alt_text = img.get_attribute("alt")
                    if alt_text:
                        name = alt_text.strip().replace("Go to ", "").replace("’s profile", "")
                except Exception as e:
                    print(f"Lead {index+1}: Fallback name extraction failed: {e}")
            # Extract Profile Link
            try:
                profile_anchor = item.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__title a")
                profile_link = profile_anchor.get_attribute("href")
            except Exception as e:
                print(f"Lead {index+1}: Primary profile link extraction failed: {e}")
                try:
                    headshot_anchor = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']")
                    href = headshot_anchor.get_attribute("href")
                    profile_link = "https://www.linkedin.com" + href if href.startswith("/") else href
                except Exception as e:
                    print(f"Lead {index+1}: Fallback profile link extraction failed: {e}")
            # Extract Title
            try:
                title_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='title']")
                title = title_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Title extraction failed: {e}")
            # Extract Company
            try:
                company_element = item.find_element(By.CSS_SELECTOR, "a[data-anonymize='company-name']")
                company = company_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Company extraction failed: {e}")
            # Extract Location
            try:
                location_element = item.find_element(By.CSS_SELECTOR, "span[data-anonymize='location']")
                location = location_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Location extraction failed: {e}")
            lead = {
                "Name": name,
                "Title": title,
                "Profile Link": profile_link,
                "Company": company,
                "Location": location
            }
            print(f"Lead {index+1} extracted: {lead}")
            leads_data.append(lead)
        print("Leads scraping completed.")
        return leads_data
    except Exception as e:
        print(f"Error scraping leads: {e}")
        return leads_data

def save_leads_to_csv(leads, filename="leads_output.csv"):
    """Saves the scraped leads to a CSV file."""
    try:
        df = pd.DataFrame(leads)
        df.to_csv(filename, index=False)
        print(f"Leads data saved to CSV file: {filename}")
    except Exception as e:
        print(f"Error saving leads data to CSV: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Load credentials from config.json
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    driver = configure_driver(headless=False)
    try:
        perform_login(driver, config)
        try:
            driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true')
            print("Navigated to LinkedIn Sales Navigator search page.")
        except Exception as e:
            print(f"Error navigating to URL after login: {e}")

        # Candidate criteria input text (include good-to-have criteria if desired)
        criteria_text = """
        Looking for [Head of Sustainability] for [10] leads.
        The leads are ideally to possess a [Entry Level] level,
        have experience in [Business Consulting and Services] industry,
        with a minimum [Less than 1] years of experience.
        It is good if the leads also have:
        1. Experience in facilities procurement,
        2. Interest in waste management and circular economy,
        3. Knowledge of sustainability practices.
        """

        parsed_data = parse_candidate_criteria(criteria_text)
        print(f"Parsed candidate criteria: {parsed_data}")

        # Additional analysis for good-to-have criteria (optional)
        good_to_have_result = llm_analyze_criteria(criteria_text)
        print(f"Good-to-Have Criteria Analysis: {good_to_have_result}")

        # Check and match parsed data
        job_title_value = parsed_data.get("job title")
        seniority_value = parsed_data.get("seniority level")
        industry_value = parsed_data.get("industry")
        experience_value = parsed_data.get("years of experience")

        print(f"Job Title: {job_title_value}")
        print(f"Seniority: {seniority_value}")
        print(f"Industry: {industry_value}")
        print(f"Experience: {experience_value}")

        matched_job_title = job_title_value  # no fuzzy matching for job title
        matched_seniority = get_closest_match(seniority_value, SENIORITY)
        matched_industry = get_closest_match(industry_value, INDUSTRY, score_cutoff=70)
        matched_experience = get_closest_match(experience_value, YEAR_EXPERIENCE, score_cutoff=60)

        print("Extracted Job Title:", matched_job_title)
        print("Matched Seniority:", matched_seniority)
        print("Matched Industry:", matched_industry)
        print("Matched Years of Experience:", matched_experience)

        # Apply filters on the Sales Navigator search page
        apply_filters(driver, parsed_data, matched_seniority, matched_industry, matched_experience)

        # Scroll and scrape leads
        leads = scrape_leads(driver)
        print("Scraped Leads Data:")
        for lead in leads:
            print(lead)

        # Save the scraped leads to CSV
        timestamp = generate_timestamp()
        csv_filename = f"leads_output_{timestamp}.csv"
        save_leads_to_csv(leads, filename=csv_filename)

    finally:
        print("Service complete.")
