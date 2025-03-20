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
from service.info_service import scrape_contact_info, iterasi_csv
from service.company_service import company_info
import traceback

WAIT_TIMEOUT = 30
SHORT_TIMEOUT = 10
MAX_RETRIES = 3
YEAR_EXPERIENCE = ["Less than 1 year", "1 to 2 years", "3 to 5 years", "6 to 10 years", "More than 10 years"]

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
    return None

def llm_analyze_criteria(criteria_text):
    prompt = ("Analyze the following candidate criteria text and determine which of the following 'good-to-have' criteria are applicable:\n"
              "1. Experience in facilities procurement\n"
              "2. Interest in waste management and circular economy\n"
              "3. Knowledge of sustainability practices\n\n"
              "Candidate criteria text:\n"
              f"\"{criteria_text}\"\n\n"
              "Return a JSON object with a key 'good_to_have' whose value is a list of the applicable criteria (choose from the above three) based on your analysis. "
              "Do not include any extra text.")
    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="gpt-4o")
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
    job_title_fieldset = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, "//fieldset[@data-x-search-filter='CURRENT_TITLE']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", job_title_fieldset)
    time.sleep(1)
    job_title_fieldset.click()
    job_title_input_xpath = "//fieldset[@data-x-search-filter='CURRENT_TITLE']//input[@type='text']"
    job_title_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, job_title_input_xpath)))
    job_title_input.send_keys(value)
    print(f"Typed '{value}' into the job title filter input.")
    time.sleep(1)
    include_button_xpath = f'//div[@aria-label="Include “{value}” in Current job title filter"]'
    try:
        include_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, include_button_xpath)))
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
        seniority_fieldset = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, seniority_fieldset_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", seniority_fieldset)
        time.sleep(1)
        seniority_fieldset.click()
        expand_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, expand_seniority_button_xpath)))
        expand_button.click()
        print("Clicked 'Expand' button for Seniority Level filter.")
        time.sleep(2)
        print(f"Attempting to find 'Include' button for matched seniority: '{matched_seniority}' using XPath: {include_seniority_button_xpath}")
        include_button = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, include_seniority_button_xpath)))
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
        industry_fieldset = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, industry_fieldset_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", industry_fieldset)
        time.sleep(1)
        industry_fieldset.click()
        industry_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, industry_input_xpath)))
        industry_input.send_keys(industry)
        print(f"Typed '{industry}' into the industry filter input.")
        time.sleep(1)
        include_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, include_industry_button_xpath)))
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
        fieldset = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, years_experience_fieldset_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", fieldset)
        time.sleep(1)
        fieldset.click()
        print("Waiting for Years of Experience dropdown list to be visible...")
        dropdown_list = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, years_experience_dropdown_list_xpath)))
        print("Dropdown list is visible.")
        print(f"Searching for option element for '{matched_experience}' using XPath: {years_experience_option_xpath}")
        option_element = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, years_experience_option_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
        time.sleep(1)
        option_element.click()
        print(f"Clicked years of experience option: '{matched_experience}'.")
        time.sleep(2)
    except Exception as e:
        print(f"Error applying years of experience filter: {e}")
    print(f"Filter applied for: '{matched_experience}'.\n")

def scroll_infinite_scroll_data_attribute(driver, scrollable_element=None, pause_time=10, max_attempts=15, initial_wait=5, step_wait=3):
    """
    Performs infinite scroll by repeatedly scrolling to elements with 'data-scroll-into-view' attribute.
    """
    if scrollable_element:
        print("Infinite scroll using data-scroll-into-view within specified element...")
    else:
        print("Infinite scroll using data-scroll-into-view on document body...")

    print(f"Waiting {initial_wait} seconds before starting data-attribute based infinite scroll...")
    time.sleep(initial_wait)

    attempts = 0
    last_lead_count = 0

    while attempts < max_attempts:
        scroll_elements = driver.find_elements(By.CSS_SELECTOR, "[data-scroll-into-view]") # Find all elements with the attribute
        current_lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        current_lead_count = len(current_lead_items)
        print(f"Current lead count: {current_lead_count}")

        if current_lead_count > last_lead_count:
            print("New leads loaded.")
            last_lead_count = current_lead_count
            attempts = 0  # Reset attempts counter

            if scroll_elements:
                last_scroll_element = scroll_elements[-1] # Scroll to the very last element with the data attribute
                driver.execute_script("arguments[0].scrollIntoView(true);", last_scroll_element)
                print("Scrolled to the last data-scroll-into-view element.")
            else:
                print("No data-scroll-into-view elements found to scroll to.")

        else:
            attempts += 1
            print(f"No new leads loaded, attempt {attempts}/{max_attempts}...")
            if attempts >= max_attempts:
                print("Stopping infinite scroll: Max attempts reached without new leads.")
                break

        time.sleep(step_wait)

    print("Infinite scroll using data-scroll-into-view completed.")

def scrape_leads(driver):
    print("Identifying search results container for scrolling...")
    search_results_container = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "search-results-container")))
    print("Search results container found.")
    scroll_infinite_scroll_data_attribute(driver, scrollable_element=search_results_container, pause_time=10, max_attempts=15, initial_wait=5, step_wait=3)
    print("Waiting for lead items to be present after scrolling...")
    WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")))
    print("Lead items found after scrolling.")
    print("Finished scrolling. Now scraping leads...")
    leads_data = []
    try:
        lead_items = driver.find_elements(By.CSS_SELECTOR, "li.artdeco-list__item.pl3.pv3")
        print(f"Found {len(lead_items)} lead items on the page.")
        for index, item in enumerate(lead_items):
            name = "NA"
            title = "NA"
            profile_link = "NA"
            location = "NA"
            company = "NA"
            company_link = "NA"
            for retry in range(MAX_RETRIES):
                try:
                    name_element = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-anonymize='person-name']")))
                    name = name_element.text.strip()
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Name extraction attempt {retry+1} failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Max retries for name reached, using fallback.")
                        try:
                            headshot_anchor = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']")))
                            img = headshot_anchor.find_element(By.TAG_NAME, "img")
                            alt_text = img.get_attribute("alt")
                            if alt_text:
                                name = alt_text.strip().replace("Go to ", "").replace("’s profile", "")
                        except Exception as fallback_e:
                            print(f"Lead {index+1}: Fallback name extraction failed: {fallback_e}")
                            name = "NA"
            for retry in range(MAX_RETRIES):
                try:
                    title_element = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle span[data-anonymize='title']")))
                    title = title_element.text.strip()
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Title extraction attempt {retry+1} failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Max retries for title reached, using NA.")
                        title = "NA"
            for retry in range(MAX_RETRIES):
                try:
                    profile_anchor = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.artdeco-entity-lockup__title a.ember-view")))
                    profile_link = profile_anchor.get_attribute("href")
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Profile link extraction attempt {retry+1} failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Max retries for profile link reached, using fallback.")
                        try:
                            headshot_anchor = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='headshot-photo']")))
                            href = headshot_anchor.get_attribute("href")
                            if href:
                                profile_link = "https://www.linkedin.com" + href if href.startswith("/") else href
                            else:
                                profile_link = "NA"
                        except Exception as fallback_e:
                            print(f"Lead {index+1}: Fallback profile link extraction failed: {fallback_e}")
                            profile_link = "NA"
            for retry in range(MAX_RETRIES):
                try:
                    company_element = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle a")))
                    company = company_element.text.strip()
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Company extraction attempt {retry+1} (using <a> tag) failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Fallback sequence for company...")
                        try:
                            company_element_fallback_text = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, ".//div[@class='artdeco-entity-lockup__subtitle']//span[@class='separator--middot']/following-sibling::text()[1]")))
                            company = company_element_fallback_text.get_attribute('textContent').strip().replace('See more about', '').strip()
                            break
                        except:
                            print(f"Lead {index+1}: Fallback company extraction (text after separator) failed.")
                            try:
                                company_element_fallback_button = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, ".//div[@class='artdeco-entity-lockup__subtitle']//button[@class='entity-hovercard__a11y-trigger']")))
                                company = company_element_fallback_button.get_attribute('aria-label').replace('See more about ', '').strip()
                                break
                            except Exception as final_fallback_e:
                                print(f"Lead {index+1}: Fallback company extraction (button aria-label) failed: {final_fallback_e}")
                                company = "NA"
                        if company != "NA":
                            break
                    continue
            for retry in range(MAX_RETRIES):
                try:
                    location_element = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-anonymize='location']")))
                    location = location_element.text.strip()
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Location extraction attempt {retry+1} failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Max retries for location reached, using NA.")
                        location = "NA"
            for retry in range(MAX_RETRIES):
                try:
                    company_link_element = WebDriverWait(item, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-anonymize='company-name']")))
                    company_link = company_link_element.get_attribute("href")
                    if company_link.startswith("/"):
                        company_link = "https://www.linkedin.com" + company_link
                    break
                except Exception as e:
                    print(f"Lead {index+1}: Company link extraction attempt {retry+1} failed: {e}")
                    if retry == MAX_RETRIES - 1:
                        print(f"Lead {index+1}: Max retries reached, using fallback.")
                        company_link = "NA"
            lead = {"Name": name, "Title": title, "Profile Link": profile_link, "Location": location, "Company": company, "Company Link": company_link}
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

def iterasi_csv(session_id, driver):
    # Process all profiles at once by calling scrape_contact_info a single time.
    scrape_contact_info(session_id, driver)
    # Now, read the enriched CSV and return its records.
    try:
        enriched_df = pd.read_csv('scrape_output2.csv')
        return enriched_df.to_dict(orient='records')
    except Exception as e:
        logging.error(f"Error reading enriched CSV: {e}")
        return None
    

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

    leads = scrape_leads(driver)
    print("Scraped Leads Data:")
    for lead in leads:
        print(lead)
    save_leads_to_csv(leads, filename=f"{session_id}.csv")

    leads_pro_data = iterasi_csv(session_id, driver)
    if leads_pro_data:
        save_leads_to_csv(leads_pro_data, filename=f"{session_id}_leads_pro.csv")
    else:
        print("No enriched leads data to save.")

    company_info(driver, session_id)
