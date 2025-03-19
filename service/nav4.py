import csv
import json
import re
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from dotenv import load_dotenv
from fuzzywuzzy import process
from utils.constant import StaticValue
from service.util_service import perform_login, configure_driver, close_overlay_if_present
from openai import OpenAI
import logging
import pandas as pd
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys



WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3

YEAR_EXPERIENCE = ["Less than 1 year", "1 to 2 years", "3 to 5 years", "6 to 10 years", "More than 10 years"]
# -------------------------------
# Utility Functions

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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o",  # or your preferred model
    )
    raw_output = response.choices[0].message.content
    logging.info(f"Raw LLM Good-to-Have Output: {raw_output}")
    try:
        return json.loads(raw_output)
    except Exception as e:
        logging.error(f"Error parsing LLM output for good-to-have criteria: {e}")
        return {"good_to_have": []}

def apply_job_title_filter(driver, value):
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
    job_title_input.send_keys(value)
    print(f"Typed '{value}' into the job title filter input.")
    time.sleep(1)
    include_button_xpath = f'//div[@aria-label="Include “{value}” in Current job title filter"]'
    try:
        include_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, include_button_xpath))
        )
        include_button.click()
        print(f"Clicked 'Include' for job title '{value}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error clicking 'Include' button for job title: {e}")


def apply_seniority_filter(driver, matched_seniority):
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

def apply_industry_filter(driver, value):
    print("Applying Industry Filter...")
    industry = value
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

def apply_years_experience_filter(driver, matched_experience):
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


# -----------------------
# Main Workflow
def main_scrape_leads(session_id, driver, industry, job_title, seniority_level, years_of_experience, debug=False):

    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    try:
        driver.get('https://www.linkedin.com/sales/search/people?viewAllFilters=true')
        close_overlay_if_present(driver)
        print("Successfully navigated to LinkedIn Sales Navigator search page.")
    except Exception as e:
        print(f"Error navigating to URL after login: {e}")

    job_title_value = job_title
    seniority_value = seniority_level
    industry_value = industry
    experience_value = years_of_experience

    matched_seniority = get_closest_match(seniority_value, StaticValue().SENIORITY_LEVEL.values())
    matched_experience = get_closest_match(experience_value, StaticValue().YEARS_OF_EXPERIENCE.values(), score_cutoff=60)

    apply_job_title_filter(driver, job_title_value)
    apply_seniority_filter(driver, matched_seniority)
    apply_years_experience_filter(driver, matched_experience)
    apply_industry_filter(driver, industry_value)

    # Scroll and scrape leads
    leads = scrape_leads(driver)
    print("Scraped Leads Data:")
    for lead in leads:
        print(lead)


    save_leads_to_csv(leads, filename=f"{session_id}.csv")


