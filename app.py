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
import datetime

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
        f"Desired Internship Period: {user_inputs['start_date']} to {user_inputs['end_date']}",
        f"Resume: {resume_text if resume_text else 'No resume provided'}"
    ]
    return "\n".join(profile_parts)

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

If the JOB LISTING contains a timeline that falls fully or partially within the user's desired internship period, score higher. If the internship is fully outside of the user's specified period, score lower or zero depending on relevance.

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

        extracted = {}
        for field in ["EXTRACTED_GPA", "EXTRACTED_EDUCATION", "EXTRACTED_SKILLS",
                      "EXTRACTED_WORK_TYPE", "EXTRACTED_SCHEDULE",
                      "EXTRACTED_INDUSTRY", "EXTRACTED_ORGANIZATION", "EXTRACTED_PRIOR_EXPERIENCES", "EXTRACTED_LOCATION", "EXTRACTED_SALARY_RANGE", "EXTRACTED_TIMELINE"]:
            line = [l for l in lines if l.startswith(field)][0]
            extracted[field] = line.split(":")[1].strip()
        
        return score, extracted
    except:
        return 0.0, {
            "EXTRACTED_GPA": "N/A",
            "EXTRACTED_EDUCATION": "N/A",
            "EXTRACTED_SKILLS": "N/A",
            "EXTRACTED_WORK_TYPE": "N/A",
            "EXTRACTED_SCHEDULE": "N/A",
            "EXTRACTED_INDUSTRY": "N/A",
            "EXTRACTED_ORGANIZATION": "N/A",
            "EXTRACTED_PRIOR_EXPERIENCES": "N/A",
            "EXTRACTED_LOCATION": "N/A",
            "EXTRACTED_SALARY_RANGE": "N/A",
            "EXTRACTED_TIMELINE": "N/A"
        }

# UI
st.title("CareerNodes: AI-Powered Internship Graph Matcher")

gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01)
education = st.selectbox("Education Level", [
    "High School Junior", "High School Senior", "High School Diploma",
    "Undergrad Freshman", "Undergrad Sophomore", "Undergrad Junior",
    "Undergrad Senior", "Bachelor's Degree", "Associates Degree", "Grad Student"])
school = st.text_input("Current School (College or High School)")
skills_input = st.text_input("Skills (comma-separated)")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
type_preference = st.selectbox("Work Type", ["Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location")
industry_preference = st.multiselect("Industry", ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit", "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])
org_type_preference = st.multiselect("Organization Type", ["Startup", "Large Company", "Small Business", "University / Research", "Government Agency", "Nonprofit", "Venture Capital", "Other"])
schedule_preference = st.selectbox("Schedule", ["Full-Time", "Part-Time"])
salary_min = st.number_input("Min Annual Salary ($)", min_value=0)
salary_max = st.number_input("Max Annual Salary ($)", min_value=0)

start_date = st.date_input("Desired Internship Start Date", value=datetime.date.today())
end_date = st.date_input("Desired Internship End Date", value=datetime.date.today() + datetime.timedelta(days=90))

resume_file = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = extract_text_from_resume(resume_file) if resume_file else ""
if resume_file: st.success("Resume uploaded!")

resume_excerpt = ""
if resume_text:
    experience_index = resume_text.lower().find("experience")
    if experience_index != -1:
        resume_excerpt = resume_text[experience_index:experience_index + 3000]
    else:
        resume_excerpt = resume_text[:3000]
else:
    resume_excerpt = "No resume provided"

if st.button("Find Matches"):
    internships_raw = fetch_internships("internship", location)
    internships = []
    for job in internships_raw:
        internships.append({
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "title": job.get("title", "Unknown Title"),
            "description": job.get("description", ""),
            "location": job.get("location", {}).get("display_name", "Unknown Location"),
            "salary_min": job.get("salary_min") or 0,
            "salary_max": job.get("salary_max") or 0,
        })

    user_inputs = {
        "gpa": gpa, "education": education, "school": school,
        "skills": skills, "location": location, "industry": industry_preference,
        "org_type": org_type_preference, "schedule": schedule_preference,
        "salary_min": salary_min, "salary_max": salary_max,
        "start_date": str(start_date), "end_date": str(end_date)
    }

    profile_text = create_user_profile_text(user_inputs, resume_excerpt)
    st.write("\u2661 AI Matching in Progress...")

    education_hierarchy = [
        "High School Junior", "High School Senior", "High School Diploma",
        "Undergrad Freshman", "Undergrad Sophomore", "Undergrad Junior",
        "Undergrad Senior", "Associates Degree", "Bachelor's Degree", "Grad Student"
    ]

    results = []
    for internship in internships:
        job_location = internship["location"].lower()
        if location.lower() not in job_location and "remote" not in job_location:
            continue
        
        job_text = (
            f"{internship['title']} at {internship['company']} located in {internship['location']}. "
            f"Description: {internship['description']} Salary Range: ${internship['salary_min']}-${internship['salary_max']}"
        )
        score, extracted = analyze_and_score(profile_text, job_text)
        internship["extracted"] = extracted

        extracted_edu = extracted["EXTRACTED_EDUCATION"].strip()
        extracted_gpa = extracted["EXTRACTED_GPA"].strip()
        extracted_industry = extracted["EXTRACTED_INDUSTRY"].strip().lower()
        extracted_skills = extracted["EXTRACTED_SKILLS"].strip().lower()

        if extracted_edu != "No Preferred Education Level Listed":
            try:
                if education_hierarchy.index(extracted_edu) > education_hierarchy.index(education):
                    continue
            except:
                pass

        if extracted_gpa != "No GPA Requirement Listed.":
            try:
                if float(extracted_gpa) > gpa:
                    continue
            except:
                pass

        if extracted_industry != "" and extracted_industry != "n/a":
            if not any(user_industry.lower() in extracted_industry for user_industry in industry_preference):
                continue

        if len(skills) > 0:
            skill_match = any(skill in extracted_skills for skill in skills)
            if not skill_match:
                continue

        results.append((score, internship))

    results.sort(reverse=True, key=lambda x: x[0])
    
    st.subheader("\u2315 Top Matches:")
    for score, internship in results:
        st.markdown(f"**{internship['company']} - {internship['title']}**")
        st.write(f"Score: {score:.3f}")
        st.write(f"Location: {internship['location']}")
        st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
        with st.expander("Full Description"):
            st.write(internship['description'])
        with st.expander("Extracted Details"):
            for k,v in internship['extracted'].items():
                st.write(f"{k.replace('EXTRACTED_', '')}: {v}")
        st.write("---")

    G = nx.Graph()
    G.add_node("You")
    for score, internship in results[:50]:
        node = f"{internship['company']}\n{internship['title']}"
        G.add_node(node)
        G.add_edge("You", node, weight=score)
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read()
        components.html(source_code, height=650, width=900)
