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
        f"GPA: {user_inputs['gpa'] if user_inputs['gpa'] is not None else 'No GPA Provided'}",
        f"Education Level: {user_inputs['education']}",
        f"School: {user_inputs['school']}",
        f"Current Major or Intended Major: {user_inputs['major'] if user_inputs['major'] else 'No Major Provided'}",
        f"Skills: {', '.join(user_inputs['skills'])}",
        f"Preferred Location: {user_inputs['location']}",
        f"Preferred Industry: {', '.join(user_inputs['industry'])}",
        f"Preferred Org Type: {', '.join(user_inputs['org_type'])}",
        f"Preferred Schedule: {user_inputs['schedule']}",
        f"Desired Salary: {user_inputs['salary_min']} - {user_inputs['salary_max']}",
        f"Preferred Timeline Start: {user_inputs['start_date']}",
        f"Preferred Timeline End: {user_inputs['end_date']}",
        f"Resume: {resume_text if resume_text else 'No resume provided'}"
    ]
    return "\n".join(profile_parts)

def truncate_text(text, max_chars=4000):
    return text if len(text) <= max_chars else text[:max_chars]

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
- Intended Major or Field of Study

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
EXTRACTED_MAJOR: <value or 'No specific major requirement listed.'>
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
                      "EXTRACTED_WORK_TYPE", "EXTRACTED_SCHEDULE", "EXTRACTED_INDUSTRY",
                      "EXTRACTED_ORGANIZATION", "EXTRACTED_PRIOR_EXPERIENCES",
                      "EXTRACTED_LOCATION", "EXTRACTED_SALARY_RANGE", "EXTRACTED_TIMELINE",
                      "EXTRACTED_MAJOR"]:
            line = [l for l in lines if l.startswith(field)][0]
            extracted[field] = line.split(":")[1].strip()
        return score, extracted
    except:
        return 0.0, {}

# UI preserved as is (skipping here to save space — you can copy your same UI code directly)

# Main execution
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
        "gpa": gpa, "education": education, "school": school, "major": major,
        "skills": skills, "location": location, "industry": industry_preference,
        "org_type": org_type_preference, "schedule": schedule_preference,
        "salary_min": salary_min, "salary_max": salary_max,
        "start_date": start_date, "end_date": end_date
    }

    profile_text = create_user_profile_text(user_inputs, resume_text)
    truncated_profile_text = truncate_text(profile_text)

    st.write("\u2661 AI Pre-Filtering in Progress...")

    # Get embeddings for profile and jobs
    profile_embed = co.embed(texts=[truncated_profile_text], model="embed-english-v3.0").embeddings[0]
    job_texts = [f"{i['title']} at {i['company']}. {i['description']}" for i in internships]
    truncated_job_texts = [truncate_text(j) for j in job_texts]
    job_embeds = co.embed(texts=truncated_job_texts, model="embed-english-v3.0").embeddings

    # Compute cosine similarity quickly
    def cosine_sim(a, b):
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    prelim_results = []
    for i, job_embed in enumerate(job_embeds):
        sim = cosine_sim(profile_embed, job_embed)
        prelim_results.append((sim, internships[i]))

    # Sort prelim results and only fully process top 20
    prelim_results.sort(reverse=True, key=lambda x: x[0])
    top_candidates = prelim_results[:20]

    st.write("\u2661 AI Full Matching in Progress...")

    results = []
    for _, internship in top_candidates:
        job_text = f"{internship['title']} at {internship['company']} located in {internship['location']}. Description: {internship['description']} Salary Range: ${internship['salary_min']}-${internship['salary_max']}"
        score, extracted = analyze_and_score(profile_text, job_text)
        internship["extracted"] = extracted
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
            for k, v in internship['extracted'].items():
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
