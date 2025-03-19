from schema.entity.leads_summary import LeadsSummaryTable
from schema.entity.column import Column
import asyncio
from .nav4 import main_scrape_leads
from .info_service import scrape_contact_info
from selenium import webdriver


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


async def search_leads(session_id: str, data: dict, driver: webdriver.Chrome):
    """Performs the lead search and scraping."""
    # logger.info(f"search_leads: Starting lead scraping for session_id: {session_id}")

    try:
        main_scrape_leads(
            session_id=session_id, # Pass session_id 
            driver=driver, # **Pass the driver argument!**
            industry=data["payload"]["industry"], 
            job_title=data["payload"]["jobTitle"], 
            seniority_level=data["payload"]["seniorityLevel"], 
            years_of_experience=data["payload"]["yearsOfExperience"] # Pass years_of_experience
        )
        job_status_dict[session_id] = None
        # logger.info(f"search_leads: Lead scraping COMPLETED for session_id: {session_id}")

    except Exception as e:
        # logger.error(f"search_leads: Error during lead scraping for session_id {session_id}: {e}", exc_info=True)
        job_status_dict[session_id] = "Error"
        raise  # Re-raise exception to be handled by endpoint

    return {
        "sessionId": session_id,
        "data": None  # for download later
    }