from groq import Groq
import csv
import json
import re
import os
import time
from fuzzywuzzy import process
from dotenv import load_dotenv
import logging



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

YEAR_EXPERIENCE = ["Less than 1 year","1-2 years","3-5 years","6-10 years","More than 10 years"]

INDUSTRY = [
    "Accounting", "Airlines & Aviation", "Alternative Dispute Resolution", "Alternative Medicine", "Animation",
    "Apparel & Fashion", "Architecture & Planning", "Arts & Crafts", "Automotive", "Aviation & Aerospace",
    "Banking", "Biotechnology", "Broadcast Media", "Building Materials", "Business Supplies & Equipment",
    "Capital Markets", "Chemicals", "Civic & Social Organization", "Civil Engineering", "Commercial Real Estate",
    "Computer & Network Security", "Computer Games", "Computer Hardware", "Computer Networking", "Computer Software",
    "Construction", "Consumer Electronics", "Consumer Goods", "Consumer Services", "Cosmetics"
]



def clean_groq_output(raw_text):
    """
    Extract the JSON substring from the raw Groq output.
    Returns a JSON object as a dictionary, or None if extraction fails.
    """
    try:
        # Use regex to extract the JSON object.
        json_match = re.search(r'({.*})', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)
        else:
            logging.warning("No JSON object found in Groq output.") # Log if no JSON found
            return None  # Return None if no JSON found
    except json.JSONDecodeError as e:
        logging.error(f"JSONDecodeError cleaning Groq output: {e}") # Log JSON decode error
        logging.debug(f"Raw Groq output that failed to parse: {raw_text}") # Log raw text for debugging
        return None  # Return None if JSON parsing fails
    except Exception as e:
        logging.exception("Unexpected error cleaning Groq output:") # Log unexpected errors with traceback
        return None

def parse_candidate_criteria(criteria_text):
    """
    Send candidate criteria to the LLM via Groq and return structured search parameters.
    Expected output JSON includes keys: 'function', 'seniority level', 'industry', 'years of experience'.
    """
    prompt = (
        "Your task is to extract candidate search criteria from the text provided and structure it as a valid JSON object.\n"
        "The JSON object should contain the following keys:\n"
        "- 'function':  The job function or area of expertise the candidate should have.\n"
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
        '  "function": "Engineering",\n'
        '  "seniority level": "Experienced Manager",\n'
        '  "industry": "Accounting",\n'
        '  "years of experience": "3"\n'
        "}\n"
    )

    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    raw_output = response.choices[0].message.content
    structured_data = clean_groq_output(raw_output)
    return structured_data

def get_closest_match(extracted_value, options_list, score_cutoff=80):
    """
    Finds the closest match for an extracted value from a list of options using fuzzy matching.
    (This function definition is correct as you had it before)
    """
    if not extracted_value:
        return None
    best_match, score = process.extractOne(extracted_value, options_list)
    if score >= score_cutoff:
        return best_match
    else:
        return None


# input user

criteria_text = """
Looking for [Head of Sustainability] for [10] leads
The leads are ideally to possess a [Manager] level
have an experience in [Waste management, Circular economy]industry
with a minimum [3] years of experience

It is good if the leads also have:
1. Experience in facilities procurement
2. Interest in waste management and circular economy
3. Knowledge of sustainability practices
"""
parsed_data = parse_candidate_criteria(criteria_text)

print(json.dumps(parsed_data, indent=2))