from schema.entity.leads_summary import LeadsSummaryTable
from schema.entity.column import Column
import asyncio
from .nav4 import scraping_leads
from selenium import webdriver # Import webdriver for type hinting




job_status_dict = {}


def init():
    layout = [
        ["leadsSummaryTable"],
    ]
        
    columns = [
        Column("leadName", "Lead Name", "text"),
        Column("leadUrl", "Lead URL", "link"),
        Column("jobTitle", "Job Title", "text"),
        Column("leadEmail", "Email Contact", "email"),
        Column("companyName", "Company Name", "text"),
        Column("companyDescription", "Company Description", "text"),
        Column("relevanceScore", "Relevance Score", "text")
    ]

    leads_summary_table = LeadsSummaryTable("Leads Summary", columns)
    return {
        "definitions": leads_summary_table.to_dict(),
        "layout": layout
    }

def checkSession():
    platforms = []
    data = {
        "key": "linkedin_sales_nav",
        "name": "LinkedIn - Sales Navigator",
        "url": "https://www.linkedin.com/login?session_redirect=%2Fsales&_f=navigator",
        "timeout": 300000
    }
    platforms.append(data)
    return platforms


def start_search_leads_task(session_id: str, data: dict, driver: webdriver.Chrome):
    job_status_dict[session_id] = None
    asyncio.create_task(search_leads(session_id=session_id, data=data, driver=driver))    
    return session_id


async def search_leads(session_id: str, data: dict, driver: webdriver.Chrome): # driver is ALREADY passed to search_leads
    """
    Performs the lead search and scraping.

    Args:
        session_id: The session ID.
        data: Task-specific data.
        driver: The Selenium WebDriver instance (passed from start_search_leads_task).
    """

    try:
        scraping_leads(
            driver=driver,  # Pass the driver object as the FIRST argument!
            session_id=session_id,
            candidate_industry=data["payload"]["industry"],
            candidate_job_title=data["payload"]["jobTitle"],
            candidate_seniority_level=data["payload"]["seniorityLevel"],
            candidate_years_experience=data["payload"]["yearsOfExperience"]
        )
        job_status_dict[session_id] = None

    except Exception as e:
        job_status_dict[session_id] = "Error" # Set job status to error
        raise  # Re-raise exception to be handled by endpoint

    return {
        "sessionId": session_id,
        "data": None  # untuk di donwload
    }