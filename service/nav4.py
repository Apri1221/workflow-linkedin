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
from selenium.webdriver.common.action_chains import ActionChains


# -------------------------------
# Constants & Static Lists
WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3

driver = None

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

def login_to_site():
    global driver
    session_url = input("Enter the session URL: ")
    session_id = input("Enter the session ID: ")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Remote(command_executor=session_url, options=chrome_options)
        driver.session_id = session_id
        print(f"Driver initialized with session ID: {driver.session_id}")
        return True
    except Exception as e:
        print(f"Error in login_to_site: {e}")
        return False

def scroll_down_page(driver, scroll_pause_time=2, max_scrolls=5):
    """
    Scrolls down the page to load additional content.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def parse_candidate_criteria(criteria_text):
    prompt = (
        "Your task is to extract candidate search criteria from the text provided and structure it as a valid JSON object.\n"
        "The JSON object should contain the following keys:\n"
        "- 'job title':  The desired job title of the candidate.\n"
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
        '  "job title": "Head of Sustainability",\n'
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
    print(f"Raw Groq Output: {raw_output}")
    structured_data = clean_groq_output(raw_output)
    return structured_data

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

def get_closest_match(extracted_value, options_list, score_cutoff=80):
    print(f"get_closest_match called with extracted_value: {extracted_value}, type: {type(extracted_value)}")
    if extracted_value is None:
        return None

    extracted_value_str = str(extracted_value)
    print(f"After str() conversion, extracted_value_str: {extracted_value_str}, type: {type(extracted_value_str)}")
    print(f"Options list (YEAR_EXPERIENCE): {options_list}")

    best_match_tuple = process.extractOne(extracted_value_str, options_list)
    if best_match_tuple:
        best_match, score = best_match_tuple
        print(f"fuzzywuzzy result: best_match: {best_match}, score: {score}")
        if score >= score_cutoff:
            return best_match
    else:
        print("fuzzywuzzy returned None (no match found)")
    return None

def apply_job_title_filter(driver, parsed_data):
    print("Applying Job Title Filter...")
    driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true')
    time.sleep(10)
    job_title_fieldset = WebDriverWait(driver, 40).until(
        EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='CURRENT_TITLE']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", job_title_fieldset)
    time.sleep(1)
    job_title_fieldset.click()
    job_title_input_xpath = "//fieldset[@data-x-search-filter='CURRENT_TITLE']//input[@type='text']"
    job_title_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, job_title_input_xpath))
    )
    extracted_job_title = parsed_data.get("job title")
    job_title_input.send_keys(extracted_job_title)
    print(f"Typed '{extracted_job_title}' into the job title filter input.")
    time.sleep(1)
    include_button_xpath = f'//div[@aria-label="Include “{extracted_job_title}” in Current job title filter"]'
    try:
        include_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, include_button_xpath))
        )
        include_button.click()
        print(f"Clicked 'Include' for job title '{extracted_job_title}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error clicking 'Include' button for job title: {e}")

def apply_seniority_filter(driver, parsed_data, matched_seniority):
    print(f"Applying Seniority Level Filter for: '{matched_seniority}'...")
    seniority_fieldset_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']"
    expand_seniority_button_xpath = "//fieldset[@data-x-search-filter='SENIORITY_LEVEL']//button[@aria-expanded='false'][.//span[contains(text(), 'Expand')]]"
    include_seniority_button_xpath = f'//li[@role="option"]//div[@aria-label="Include “{matched_seniority}” in Seniority level filter"]'
    try:
        seniority_fieldset = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.XPATH, seniority_fieldset_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", seniority_fieldset)
        time.sleep(1)
        seniority_fieldset.click()
        expand_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, expand_seniority_button_xpath))
        )
        expand_button.click()
        print("Clicked 'Expand' button for Seniority Level filter.")
        time.sleep(2)
        print(f"Attempting to find 'Include' button for matched seniority: '{matched_seniority}' using XPath: {include_seniority_button_xpath}")
        include_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, include_seniority_button_xpath))
        )
        include_button.click()
        print(f"Clicked 'Include' button for matched seniority level '{matched_seniority}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying seniority level filter for '{matched_seniority}': {e}")

def apply_industry_filter(driver, parsed_data):
    print("Applying Industry Filter...")
    industry = parsed_data.get("industry")
    if not industry:
        print("No industry extracted, skipping filter.\n")
        return
    industry_fieldset_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']"
    industry_input_xpath = "//fieldset[@data-x-search-filter='INDUSTRY']//input[@type='text']"
    include_industry_button_xpath = f'//div[@aria-label="Include “{industry}” in Industry filter"]'
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
    except Exception as e:
        print(f"Error applying industry filter: {e}")
    print("Industry Filter Applied.\n")

def apply_years_experience_filter(driver, parsed_data, matched_experience):
    print(f"Applying Years of Experience Filter for: '{matched_experience}'...")
    years_experience_fieldset_xpath = "//fieldset[@data-x-search-filter='YEARS_AT_CURRENT_COMPANY']"
    years_experience_dropdown_list_xpath = '//ul[@role="listbox" and @aria-label="Years in current company filter suggestions"]'
    years_experience_option_xpath = f'//li[@role="option" and contains(normalize-space(.), "{matched_experience}")]/div'
    try:
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
        driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
        time.sleep(1)
        option_element.click()
        print(f"Clicked years of experience option: '{matched_experience}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying years of experience filter: {e}")
    print(f"Filter applied for: '{matched_experience}'.\n")

def scroll_until_loaded(driver, pause_time=5, max_attempts=20, scroll_increment=500, consecutive_no_change_attempts=5, nudge_scroll_amount=100, nudge_attempts=2): # Added nudge parameters
    last_count = 0
    attempts = 0
    no_change_count = 0
    scroll_position = 0 # Keep track of current scroll position

    while attempts < max_attempts:
        current_scroll_height = driver.execute_script("return document.body.scrollHeight")

        scroll_increment_js = f"window.scrollBy(0, {scroll_increment});" # Scroll by a smaller increment
        driver.execute_script(scroll_increment_js)
        scroll_position += scroll_increment # Update scroll position

        time.sleep(pause_time)
        new_scroll_height = driver.execute_script("return document.body.scrollHeight")

        lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        current_count = len(lead_items)
        print(f"Scroll attempt {attempts+1}: Found {current_count} leads, Scroll Height changed: {new_scroll_height > current_scroll_height}, Scroll Pos: {scroll_position}")

        if current_count == last_count:
            no_change_count += 1
            if no_change_count >= consecutive_no_change_attempts:
                print(f"No new leads for {consecutive_no_change_attempts} attempts.")

                # --- Nudge Scroll Attempt ---
                for nudge_attempt in range(nudge_attempts):
                    print(f"Nudge Scroll Attempt {nudge_attempt+1}/{nudge_attempts}")
                    driver.execute_script(f"window.scrollBy(0, -{nudge_scroll_amount});") # Scroll UP slightly
                    time.sleep(pause_time/2)
                    driver.execute_script(f"window.scrollBy(0, {nudge_scroll_amount});")  # Scroll DOWN again
                    time.sleep(pause_time/2)

                    lead_items_after_nudge = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
                    nudge_current_count = len(lead_items_after_nudge)
                    print(f"  Nudge attempt {nudge_attempt+1}: Lead count after nudge: {nudge_current_count}")

                    if nudge_current_count > current_count: # Check if nudge helped load new leads
                        print("  Nudge scroll loaded new leads! Resuming regular scroll.")
                        current_count = nudge_current_count # Update count, reset no_change_count, break nudge loop
                        no_change_count = 0
                        last_count = current_count
                        break # Break out of nudge attempts and continue regular scroll
                else: # else block executes if NO break in for loop (nudge didn't help)
                    print("  Nudge scroll did not load new leads; stopping scrolling.")
                    break # Break out of main while loop if nudge attempts failed

        else:
            no_change_count = 0

        last_count = current_count
        attempts += 1

        if scroll_position >= current_scroll_height and new_scroll_height == current_scroll_height:
            print("Reached end of scrollable content and no new content loaded. Stopping.")
            break


    return last_count


def scroll_down_using_keys(driver, pause_time=2, max_attempts=10):
    actions = ActionChains(driver)
    last_count = 0
    attempts = 0
    while attempts < max_attempts:
        actions.send_keys(Keys.PAGE_DOWN).perform()
        time.sleep(pause_time)
        lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        current_count = len(lead_items)
        print(f"Key scroll attempt {attempts+1}: Found {current_count} lead items")
        if current_count == last_count:
            print("No new leads loaded; stopping key scrolling.")
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
    # Try one of the scrolling methods below. You can switch between them.
    # scroll_until_loaded(driver, pause_time=3, max_attempts=10)
    scroll_down_using_keys(driver, pause_time=3, max_attempts=30)
    # Alternatively, you could use:
    # scroll_down_using_keys(driver, pause_time=2, max_attempts=10)
    print("Finished scrolling. Now scraping leads...")

    leads_data = []
    try:
        WebDriverWait(driver, 30).until(
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

            # --- Extract Name ---
            try:
                name_element = WebDriverWait(item, 10).until( # Explicit wait here!
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-anonymize='person-name']"))
                )
                name = name_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Primary name extraction failed: {e}")
                try:
                    headshot_anchor = WebDriverWait(item, 5).until( # Explicit wait for fallback too
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']"))
                    )
                    img = headshot_anchor.find_element(By.TAG_NAME, "img")
                    alt_text = img.get_attribute("alt")
                    if alt_text:
                        name = alt_text.strip().replace("Go to ", "").replace("’s profile", "")
                except Exception as e:
                    print(f"Lead {index+1}: Fallback name extraction failed: {e}")
                    name = "NA"

            # --- Extract Profile Link ---
            try:
                profile_anchor = WebDriverWait(item, 10).until( # Explicit wait here!
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.artdeco-entity-lockup__title a"))
                )
                profile_link = profile_anchor.get_attribute("href")
            except Exception as e:
                print(f"Lead {index+1}: Primary profile link extraction failed: {e}")
                try:
                    headshot_anchor = WebDriverWait(item, 5).until( # Explicit wait for fallback too
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']"))
                    )
                    href = headshot_anchor.get_attribute("href")
                    if href:
                        profile_link = "https://www.linkedin.com" + href if href.startswith("/") else href
                    else:
                        profile_link = "NA"
                except Exception as e:
                    print(f"Lead {index+1}: Fallback profile link extraction failed: {e}")
                    profile_link = "NA"

            # --- Extract Title ---
            try:
                title_element = WebDriverWait(item, 10).until( # Explicit wait here!
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-anonymize='title']"))
                )
                title = title_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Title extraction failed: {e}")
                title = "NA"

            # --- Extract Company ---
            try:
                company_element = WebDriverWait(item, 10).until( # Explicit wait here!
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='company-name']"))
                )
                company = company_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Company extraction failed: {e}")
                company = "NA"

            # --- Extract Location ---
            try:
                location_element = WebDriverWait(item, 10).until( # Explicit wait here!
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-anonymize='location']"))
                )
                location = location_element.text.strip()
            except Exception as e:
                print(f"Lead {index+1}: Location extraction failed: {e}")
                location = "NA"

            # Include the record even if key fields are missing.
            if name == "NA" and profile_link == "NA":
                print(f"Lead {index+1}: Both name and link are missing; including with defaults.")

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
    try:
        df = pd.DataFrame(leads)
        df.to_csv(filename, index=False)
        print(f"Leads data saved to CSV file: {filename}")
    except Exception as e:
        print(f"Error saving leads data to CSV: {e}")

# -------------------------------
# Main Workflow
# -------------------------------
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
        The leads are ideally to possess a [Entry Level] level
        have an experience in [Business Consulting and Services]industry
        with a minimum [Less than 1] years of experience

        It is good if the leads also have:
        1. Experience in facilities procurement
        2. Interest in waste management and circular economy
        3. Knowledge of sustainability practices
        """

        parsed_data = parse_candidate_criteria(criteria_text)
        print(f"Parsed data from Groq: {parsed_data}")

        # Check parsed data before matching
        job_title_value = parsed_data.get("job title")
        seniority_value = parsed_data.get("seniority level")
        industry_value = parsed_data.get("industry")
        experience_value = parsed_data.get("years of experience")

        print(f"Job Title: {job_title_value}")
        print(f"Seniority: {seniority_value}")
        print(f"Industry: {industry_value}")
        print(f"Experience: {experience_value}")
        print(f"YEAR_EXPERIENCE List: {YEAR_EXPERIENCE}")

        matched_job_title = job_title_value  # No matching for job title
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

        # Scroll and scrape leads
        leads = scrape_leads(driver)
        print("Scraped Leads Data:")
        for lead in leads:
            print(lead)

        save_leads_to_csv(leads, filename="leads_output.csv")
    else:
        print("Login failed, exiting.")