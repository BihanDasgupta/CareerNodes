import streamlit as st
import requests
import os
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from dotenv import load_dotenv
import PyPDF2
import cohere
import numpy as np
import time

# Load environment variables
load_dotenv()

# Load API keys
if "adzuna" in st.secrets:
    ADZUNA_APP_ID = st.secrets["adzuna"]["app_id"]
    ADZUNA_APP_KEY = st.secrets["adzuna"]["app_key"]
else:
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

if "cohere" in st.secrets:
    COHERE_API_KEY = st.secrets["cohere"]["api_key"]
else:
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

ADZUNA_COUNTRY = "us"
co = cohere.Client(COHERE_API_KEY)


def fetch_internships(query, location, results_limit=50):
    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params = {
        'app_id': ADZUNA_APP_ID,
        'app_key': ADZUNA_APP_KEY,
        'what': query,
        'where': location,
        'results_per_page': results_limit,
        'content-type': 'application/json'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('results', [])
    else:
        st.error("Failed to fetch data from Adzuna API.")
        return []


def extract_text_from_resume(file):
    text = ""
    if file.name.endswith(".txt"):
        text = file.read().decode("utf-8")
    elif file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


def create_user_profile_text(user_inputs, resume_text):
    profile_parts = [
        f"GPA: {user_inputs['gpa']}",
        f"Education Level: {user_inputs['education']}",
        f"School: {user_inputs['school']}",
        f"Skills: {', '.join(user_inputs['skills'])}",
        f"Preferred Location: {user_inputs['location']}",
        f"Preferred Industry: {', '.join(user_inputs['industry'])}",
        f"Preferred Org Type: {', '.join(user_inputs['org_type'])}",
        f"Preferred Schedule: {user_inputs['schedule']}",
        f"Desired Salary: ${user_inputs['salary_min']} - ${user_inputs['salary_max']}",
        f"Resume: {resume_text if resume_text else 'No resume provided'}"
    ]
    return "\n".join(profile_parts)


def fast_filter(internships, user_inputs):
    # Quick rule-based filtering BEFORE Cohere
    filtered = []
    for job in internships:
        loc = job.get("location", {}).get("display_name", "").lower()
        if user_inputs['location'].lower() not in loc and "remote" not in loc:
            continue

        desc = job.get("description", "").lower()
        skill_match = any(skill.lower() in desc for skill in user_inputs['skills'])
        industry_match = any(ind.lower() in desc for ind in user_inputs['industry'])

        if skill_match or industry_match:
            filtered.append(job)
    return filtered


def analyze_and_score(user_profile_text, job_text):
    prompt = f"""
You are an internship matching AI given a USER PROFILE and JOB LISTING, and you are tasked with finding the best JOB LISTING matches for the given USER PROFILE.

FIRST, extract from the JOB LISTING (if available):
- Required or preferred GPA
- Required or preferred education level
- Required or preferred skill keywords
- Required or preferred prior experiences
- Location (city, state, country)
- Salary range if paid 
- Work Type (remote, hybrid, onsite)
- Schedule (full-time, part-time)
- Industry category (Tech, Finance, Healthcare, etc.)
- Organization type (Startup, Large Company, Nonprofit, Government, etc.)
- Timeline (Start date or month, End date or month)

SECOND, compare these extracted attributes against the USER PROFILE. Return a matching score between 0 and 1. 
In your scoring, truly consider all of the factors that the user provides in the USER PROFILE and how good of a fit you think the internship would be based on what is in the JOB LISTING. Perform a thorough analysis in your scoring with the purpose of providing the user with the best possible matches for an internship.
If the USER PROFILE contains anything that does not match a requirement in the JOB LISTING (i.e. user does not have required education level), give the JOB LISTING a score of 0. If the JOB LISTING contains anything that does not meet a requirement in the USER PROFILE (i.e. the job is remote but user is looking for onsite), give it a lower score, not necessarily 0 but not high either.
The results must be as catered to the user's needs as possible all the while meeting the internship's requirements. 

USER PROFILE:
{user_profile_text}

JOB LISTING:
{job_text}

Return output in exactly this format:

MATCH_SCORE: <score between 0 and 1>
EXTRACTED_GPA: <value or 'No GPA Requirement Listed.'>
EXTRACTED_EDUCATION: <value or 'No Preferred Education Level Listed'>
EXTRACTED_SKILLS: <value or 'No required/preferred skills listed.'>
EXTRACTED_PRIOR_EXPERIENCES: <value or 'No required/preferred prior experiences listed.'>
EXTRACTED_LOCATION: <value or 'Remote or No Location Listed.'>
EXTRACTED_SALARY_RANGE: <value or 'Unpaid or No Salary Range Listed.'>
EXTRACTED_WORK_TYPE: <value>
EXTRACTED_SCHEDULE: <value>
EXTRACTED_INDUSTRY: <value>
EXTRACTED_ORGANIZATION: <value>
EXTRACTED_TIMELINE: <value or 'No start/end date specified.'>
"""

    response = co.chat(model="command-r-plus", message=prompt)
    reply = response.text.strip()

    try:
        lines = reply.split("\n")
        score_line = [l for l in lines if l.startswith("MATCH_SCORE:")][0]
        score = float(score_line.split(":")[1].strip())
        score = max(0.0, min(1.0, score))
        return score
    except:
        return 0.0


# UI starts
st.title("CareerNodes: AI-Powered Internship Graph Matcher")

# Collect user inputs

# Same as before — keep your UI exactly as you have it (omitted for brevity)

# Resume upload as before (omitted for brevity)

if st.button("Find Matches"):
    internships_raw = fetch_internships("internship", location)

    # Fast pre-filter to drastically reduce Cohere API calls
    internships_filtered = fast_filter(internships_raw, {
        'location': location,
        'skills': skills,
        'industry': industry_preference
    })

    user_inputs = {
        "gpa": gpa, "education": education, "school": school,
        "skills": skills, "location": location, "industry": industry_preference,
        "org_type": org_type_preference, "schedule": schedule_preference,
        "salary_min": salary_min, "salary_max": salary_max
    }
    profile_text = create_user_profile_text(user_inputs, resume_excerpt)
    st.write("♡ AI Matching in Progress...")

    results = []

    for job in internships_filtered:
        job_text = f"{job['title']} at {job['company'].get('display_name', '')} located in {job['location'].get('display_name', '')}. Description: {job['description']}"
        score = analyze_and_score(profile_text, job_text)
        results.append((score, job))
        time.sleep(0.5)  # very light rate limit protection

    results.sort(reverse=True, key=lambda x: x[0])
    st.subheader("⌕ Top Matches:")

    for score, internship in results[:10]:
        st.markdown(f"**{internship['company']['display_name']} - {internship['title']}**")
        st.write(f"Score: {score:.3f}")
        st.write(f"Location: {internship['location']['display_name']}")
        st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
        st.write("---")
