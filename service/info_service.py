from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from service.util_service import perform_login, configure_driver, close_overlay_if_present
import json
import traceback
import pandas as pd
import pyperclip



socials_info_list = []
emails_info_list = []
website_info_list = []
about_info_list = []
address_info_list = []
phone_info_list = []
linkedin_profile_list = []





def scrape_contact_info(session_id):
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    driver = configure_driver()

    perform_login(driver, config)

    DATA_FRAME = pd.read_csv(f"{session_id}.csv")
    LEAD_PROFILE_LINKS = DATA_FRAME['Profile Link'].tolist()

    for lead_profile in LEAD_PROFILE_LINKS:
        print(f"Getting lead info from: {lead_profile}") # More informative print
        try:
            driver.get(lead_profile)
            close_overlay_if_present(driver)
            # Wait for page to load, check for a specific element that indicates page is ready
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-x--lead-actions-bar-overflow-menu][aria-label="Open actions overflow menu"]'))) # Wait for action menu button to load
        except Exception as e:
            print(f"Error loading profile page: {lead_profile}")
            print(traceback.format_exc()) # Print full traceback for debugging
            linkedin_profile_list.append("NULL") # Still append NULL to keep lists consistent
            socials_info_list.append("NULL")
            emails_info_list.append("NULL")
            website_info_list.append("NULL")
            address_info_list.append("NULL")
            phone_info_list.append("NULL")
            about_info_list.append("NULL")
            continue # Skip to the next profile if page load fails

        # Extract Lead Linkedin link
        try:
            button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-x--lead-actions-bar-overflow-menu][aria-label="Open actions overflow menu"]')))
            button.click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[text()='Copy LinkedIn.com URL']")))
            copy_link_profile_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[text()='Copy LinkedIn.com URL']")))
            copy_link_profile_button.click()
            link_profile = pyperclip.paste()
            linkedin_profile_list.append(link_profile)
        except Exception as e:
            print(f"Error extracting LinkedIn profile URL for: {lead_profile}")
            print(traceback.format_exc())
            linkedin_profile_list.append("NULL")

        # Extract Lead contact info
        socials_string = ""
        emails_string = ""
        phones_string = ""
        website_string = ""
        address_string= ""

        try:
            contact_info_section = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'section[data-sn-view-name="lead-contact-info"]')))
            links = contact_info_section.find_elements(By.TAG_NAME, 'a')
            links = [link.get_attribute('href') for link in links if link.get_attribute('href') and "https://www.bing.com/search?" not in link.get_attribute('href')] # Added check for None href
        except Exception as e:
            print(f"Error finding contact info section for: {lead_profile}")
            print(traceback.format_exc())
            links = []

        if links:
            buttons = contact_info_section.find_elements(By.TAG_NAME, 'button')
            if buttons:
                for button in buttons:
                    if "Show all" in button.text:
                        button.click()
                        try:
                            contact_info_modal = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.artdeco-modal__content')))
                            contact_info_modal_close_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-test-modal-close-btn]')))
                            # Phone(s)
                            try:
                                phone_section = contact_info_modal.find_element(By.CSS_SELECTOR, 'section.contact-info-form__phone')
                                phone_section_links = phone_section.find_elements(By.TAG_NAME, 'a')
                                if phone_section_links:
                                    for phone_number in phone_section_links:
                                        if phone_number.get_attribute('href'): # Check if href is not None
                                            if "tel:" in str(phone_number.get_attribute('href')):
                                                phones_string = phones_string + " " + str(phone_number.get_attribute('href')).strip().replace('tel:', ' ') + ";"
                                            else:
                                                phones_string = phones_string + " " + str(phone_number.get_attribute('href')).strip().replace('tel:', ' ') + ";"
                            except:
                                pass # Keep going even if phone info fails

                            # Email(s)
                            try:
                                email_section = contact_info_modal.find_element(By.CSS_SELECTOR, 'section.contact-info-form__email')
                                email_section_links = email_section.find_elements(By.TAG_NAME, 'a')
                                if email_section_links:
                                    for email in email_section_links:
                                        if email.get_attribute('href'): # Check if href is not None
                                            if "mailto:" in str(email.get_attribute('href')):
                                                emails_string = emails_string + " " + str(email.get_attribute('href')).strip().replace('mailto:', '') + ";"
                                            else:
                                                emails_string = emails_string + " " + str(email.get_attribute('href')).strip().replace('mailto:', '') + ";"
                            except:
                                pass # Keep going even if email info fails

                            # Website(s)
                            try:
                                website_section = contact_info_modal.find_element(By.CSS_SELECTOR, 'section.contact-info-form__website')
                                website_section_links = website_section.find_elements(By.TAG_NAME, 'a')
                                if website_section_links:
                                    for website in website_section_links:
                                        if website.get_attribute('href'): # Check if href is not None
                                            website_string = website_string + " " + str(website.get_attribute('href')).strip() + ";"
                            except:
                                pass # Keep going even if website info fails


                            # Social(s)
                            try:
                                socials_section = contact_info_modal.find_element(By.CSS_SELECTOR, 'section.contact-info-form__social')
                                socials_section_links = socials_section.find_elements(By.TAG_NAME, 'a')
                                if socials_section_links:
                                    for social in socials_section_links:
                                        if social.get_attribute('href'): # Check if href is not None
                                            if "https://www.twitter.com/" in str(social.get_attribute('href')):
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                                            elif "https://www.x.com/" in str(social.get_attribute('href')):
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                                            elif "https://www.instagram.com/" in str(social.get_attribute('href')):
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                                            elif "https://www.facebook.com/" in str(social.get_attribute('href')):
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                                            elif "https://www.pinterest.com/" in str(social.get_attribute('href')):
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                                            else:
                                                socials_string = socials_string + " " + str(social.get_attribute('href')).strip() + ";"
                            except:
                                pass # Keep going even if social info fails


                            # Address(s)
                            try:
                                address_section = contact_info_modal.find_element(By.CSS_SELECTOR, 'section.contact-info-form__address')
                                address_section_links = address_section.find_elements(By.TAG_NAME, 'a')
                                if address_section_links:
                                    for address in address_section_links:
                                        if address.get_attribute('href'): # Check if href is not None
                                            address_string = address_string + " " + str(address.get_attribute('href')).strip() + ";"
                            except:
                                pass # Keep going even if address info fails

                            contact_info_modal_close_button.click()
                        except:
                            print("Modal not found or error in modal processing for: {lead_profile}") # More specific modal error
                    break # Break after clicking "Show all" button

        else:
            print(f"This user has no contact information section on their linkedin sales nav profile: {lead_profile}")

        # Check if any string is empty, if it is...set it to NULL
        socials_info_list.append(socials_string if socials_string else "NULL")
        emails_info_list.append(emails_string if emails_string else "NULL")
        website_info_list.append(website_string if website_string else "NULL")
        address_info_list.append(address_string if address_string else "NULL")
        phone_info_list.append(phones_string if phones_string else "NULL")

        # Extract Lead About info.
        try:
            about_section_header = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h1[text()='About']")))
            print(f"This user has About info: {lead_profile}")
            try:
                show_more_button = about_section_header.find_element(By.XPATH, "//button[text()='…Show more']")
                show_more_button.click()
            except:
                pass # No "Show more" button
            section = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "about-section")))
            about_info = section.text.strip().replace('Show less', '').replace('About\n', '')
            about_info_list.append(about_info)

        except Exception as e:
            print(f"This user has no About info or error extracting for: {lead_profile}")
            print(traceback.format_exc())
            about_info_list.append("NULL")


    data = {
        'Name': DATA_FRAME['Name'].tolist(),
        'Role': DATA_FRAME['Role'].tolist(),
        'About': about_info_list,
        'Linkedin URL': linkedin_profile_list,
        'Phone(s)': phone_info_list,
        'Email(s)': emails_info_list,
        'Website(s)': website_info_list,
        'Social(s)': socials_info_list,
        'Address(s)': address_info_list,
        'Geography': DATA_FRAME['Geography'].tolist(),
        'Date Added': DATA_FRAME['Date Added'].tolist(),
        'Company': DATA_FRAME['Company'].tolist(),
        'Company Linkedin URL': DATA_FRAME['Company Linkedin URL'].tolist(),
    }
    df_about_updated = pd.DataFrame(data)
    df_about_updated.to_csv('scrape_output2.csv', index=False)
    print("Data saved to scrape_output2.csv") # Confirmation message