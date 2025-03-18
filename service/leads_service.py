from schema.entity.leads_summary import LeadsSummaryTable
from schema.entity.column import Column
import asyncio
from .nav4 import scrape_leads


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


def start_search_leads_task(session_id, data):
    job_status_dict[session_id] = None
    asyncio.create_task(search_leads(session_id=session_id, data=data))
    return session_id


async def search_leads(session_id, data):
    scrape_leads(session_id, data["payload"]["industry"], data["payload"]["jobTitle"], data["payload"]["seniorityLevel"], data["payload"]["yearsOfExperience"])
    job_status_dict[session_id] = None

    return {
        "sessionId": session_id,
        "data": None  # untuk di donwload
    }