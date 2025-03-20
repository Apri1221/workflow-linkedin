import os
import re
import time  # Consider removing if not used elsewhere
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import pyperclip
import traceback
import logging
from selenium.common.exceptions import NoSuchElementException, TimeoutException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def company_info(driver, session_id):
    """
    Scrapes company information (overview, headquarters, website) from LinkedIn
    company profiles listed in the 'scrape_output2.csv' file (output of info_service).
    Expects a Selenium WebDriver instance and session_id as input.
    """
    # Reset lists for storing scraped data
    company_headquarters_list = []
    company_overview_list = []
    company_website_list = []

    csv_filepath = 'scrape_output2.csv'
    try:
        DATA_FRAME = pd.read_csv(csv_filepath)
        if 'Company Link' in DATA_FRAME.columns:
            company_links = DATA_FRAME['Company Link'].tolist()
        else:
            logging.error("Expected column 'Company Link' not found in the DataFrame.")
            return
    except FileNotFoundError:
        logging.error(f"FileNotFoundError: {csv_filepath} not found. Cannot proceed with company info scraping.")
        return

    counter = 1
    for company_profile in company_links:
        logging.info(f'Getting company {counter} data from: {company_profile}')
        headquarters = "NULL"
        overview = "NULL"
        website = "NULL"

        if pd.isna(company_profile):
            company_headquarters_list.append(headquarters)
            company_overview_list.append(overview)
            company_website_list.append(website)
            counter += 1
            continue

        try:
            driver.get(company_profile)
            # Wait for the company overview element to be present
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'p[data-anonymize="company-blurb"]'))
            )
            
            # Attempt to click the "Show more" button to expand the overview
            try:
                expand_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-expand-button][data-control-name='read_more_description']"))
                )
                expand_button.click()
                logging.info("Show more button clicked successfully to expand company overview.")
                # Allow some time for expanded content to load
                time.sleep(1)
            except Exception as e:
                logging.warning("Show more button not found or could not be clicked: " + str(e))
            
            # Extract Company Overview
            try:
                overview_element = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'p[data-anonymize="company-blurb"]'))
                )
                overview = overview_element.text.strip()
                logging.info("Company Overview extracted.")
            except Exception as e_overview:
                overview = "NULL"
                logging.error(f"Error extracting Company Overview for {company_profile}: {e_overview}")
                logging.error(traceback.format_exc())
            
            # Modal logic for Headquarters and Website
            try:
                read_more_modal_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-control-name='read_more_description']"))
                )
                read_more_modal_button.click()
                company_details_modal = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-labelledby="company-details-panel__header"]'))
                )
                # Extract Headquarters
                try:
                    headquarters_element = company_details_modal.find_element(By.CSS_SELECTOR, 'dd.company-details-panel-headquarters')
                    headquarters = headquarters_element.text.strip()
                except NoSuchElementException:
                    logging.warning(f"Headquarters element not found in modal for {company_profile}")
                except Exception as e_hq:
                    logging.error(f"Error extracting Headquarters for {company_profile} (modal): {e_hq}")
                    logging.error(traceback.format_exc())
                # Extract Website
                try:
                    website_element = company_details_modal.find_element(By.CSS_SELECTOR, 'a.company-details-panel-website')
                    website = website_element.get_attribute('href')
                except NoSuchElementException:
                    logging.warning(f"Website element not found in modal for {company_profile}")
                except Exception as e_website:
                    logging.error(f"Error extracting Website for {company_profile} (modal): {e_website}")
                    logging.error(traceback.format_exc())
            except TimeoutException:
                logging.warning(f"Timeout interacting with Company Details Modal for {company_profile}")
            except NoSuchElementException:
                logging.warning(f"Modal elements not found for Company Details for {company_profile}")
            except Exception as e_modal:
                logging.error(f"Error interacting with Company Details Modal for {company_profile}: {e_modal}")
                logging.error(traceback.format_exc())
        except Exception as e_profile_load:
            logging.error(f"Error loading company profile page: {company_profile}")
            logging.error(traceback.format_exc())

        company_headquarters_list.append(headquarters)
        company_overview_list.append(overview)
        company_website_list.append(website)
        counter += 1

    # Merge the scraped company info with the leads_pro CSV
    try:
        leads_pro_df = pd.read_csv(f"{session_id}_leads_pro.csv")
    except FileNotFoundError:
        logging.error(f"FileNotFoundError: {session_id}_leads_pro.csv not found. Company info merge skipped.")
        return

    if leads_pro_df.empty:
        logging.warning(f"Warning: {session_id}_leads_pro.csv is empty. Company info merge skipped.")
        return

    if (len(company_overview_list) == len(leads_pro_df) and 
        len(company_headquarters_list) == len(leads_pro_df) and 
        len(company_website_list) == len(leads_pro_df)):
        leads_pro_df['Company Overview'] = company_overview_list
        leads_pro_df['Company Headquarters'] = company_headquarters_list
        leads_pro_df['Company Website'] = company_website_list
    else:
        logging.error("Error: Length mismatch between company info lists and leads DataFrame. Company info merge failed.")
        logging.error(f"Lengths: Overview={len(company_overview_list)}, Headquarters={len(company_headquarters_list)}, Website={len(company_website_list)}, DataFrame={len(leads_pro_df)}")
        return

    leads_pro_df.to_csv(f"{session_id}_leads_pro_company_info.csv", index=False)
    logging.info(f"Company data saved and merged into {session_id}_leads_pro_company_info.csv")
