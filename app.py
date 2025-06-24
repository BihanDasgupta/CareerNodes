import streamlit as st
import requests
import os
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from dotenv import load_dotenv
import PyPDF2
import openai
import numpy as np
import datetime
import re

# Load environment variables
load_dotenv()

# Load API keys
if "adzuna" in st.secrets:
    ADZUNA_APP_ID = st.secrets["adzuna"]["app_id"]
    ADZUNA_APP_KEY = st.secrets["adzuna"]["app_key"]
else:
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

if "openai" in st.secrets:
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
else:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
ADZUNA_COUNTRY = "us"

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

def hybrid_analyze(user_profile_text, internships):
    profile_embed = openai.embeddings.create(
        input=user_profile_text,
        model="text-embedding-ada-002"
    ).data[0].embedding

    job_texts = [f"{i['title']} at {i['company']} located in {i['location']}. {i['description']}" for i in internships]
    job_embeds = []
    for jt in job_texts:
        embed = openai.embeddings.create(
            input=jt,
            model="text-embedding-ada-002"
        ).data[0].embedding
        job_embeds.append(embed)

    similarities = np.dot(np.array(job_embeds), np.array(profile_embed))
    preliminary = []
    for sim, internship in zip(similarities, internships):
        preliminary.append((sim, internship))
    preliminary.sort(reverse=True, key=lambda x: x[0])
    top_candidates = preliminary[:10]

    results = []
    for sim, internship in top_candidates:
        job_text = f"{internship['title']} at {internship['company']} located in {internship['location']}. Description: {internship['description']} Salary Range: ${internship['salary_min']}-${internship['salary_max']}"
        prompt = f"""
You are an internship matching AI given a USER PROFILE and JOB LISTING. Extract the following fields and assign a MATCH_SCORE from 0 to 1.

- Required GPA
- Required education
- Required skills
- Prior experiences
- Location
- Salary
- Work type
- Schedule
- Industry
- Organization type
- Timeline
- Major

If user does not meet a strict requirement, assign score 0.0. Otherwise, score from 0 to 1 considering all factors.

Return in this format strictly:
MATCH_SCORE: <score>
EXTRACTED_GPA: <value>
EXTRACTED_EDUCATION: <value>
EXTRACTED_SKILLS: <value>
EXTRACTED_PRIOR_EXPERIENCES: <value>
EXTRACTED_LOCATION: <value>
EXTRACTED_SALARY: <value>
EXTRACTED_WORK_TYPE: <value>
EXTRACTED_SCHEDULE: <value>
EXTRACTED_INDUSTRY: <value>
EXTRACTED_ORGANIZATION: <value>
EXTRACTED_TIMELINE: <value>
EXTRACTED_MAJOR: <value>

USER PROFILE:
{user_profile_text}

JOB LISTING:
{job_text}
"""
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()

        score_match = re.search(r"MATCH_SCORE:\s*(\d+(\.\d+)?)", reply)
        score = float(score_match.group(1)) if score_match else 0.0

        extracted = {}
        fields = ["GPA", "EDUCATION", "SKILLS", "PRIOR_EXPERIENCES", "LOCATION", "SALARY", "WORK_TYPE",
                  "SCHEDULE", "INDUSTRY", "ORGANIZATION", "TIMELINE", "MAJOR"]
        for field in fields:
            match = re.search(rf"EXTRACTED_{field}:\s*(.*)", reply)
            extracted[field] = match.group(1).strip() if match else "Not Found"

        results.append((score, internship, extracted))

    results.sort(reverse=True, key=lambda x: x[0])
    return results

# UI
st.title("\u273e CareerNodes")
st.subheader("\u2764 A Graphical Internship Matchmaker Powered by AI")

gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, value=None)
if gpa == 0.0: gpa = None
education = st.selectbox("Education Level", ["Choose an option", "High School Junior", "High School Senior", "High School Diploma", "Undergrad Freshman", "Undergrad Sophomore", "Undergrad Junior", "Undergrad Senior", "Bachelor's Degree", "Associates Degree", "Grad Student"])
school = st.text_input("Current School (College or High School)")
major = st.text_input("Current Major or Intended Major")
skills_input = st.text_input("Skills (comma-separated)")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
type_preference = st.selectbox("Work Type", ["Choose an option", "Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location")
industry_preference = st.multiselect("Industry", ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit", "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])
org_type_preference = st.multiselect("Organization Type", ["Startup", "Large Company", "Small Business", "University / Research", "Government Agency", "Nonprofit", "Venture Capital", "Other"])
schedule_preference = st.selectbox("Schedule", ["Choose an option", "Full-Time", "Part-Time"])
salary_min = st.number_input("Min Annual Salary ($)", min_value=0, value=None)
salary_max = st.number_input("Max Annual Salary ($)", min_value=0, value=None)
if salary_min == 0: salary_min = None
if salary_max == 0: salary_max = None

use_calendar = st.checkbox("Specify Preferred Internship Timeline", value=False)
if use_calendar:
    start_date = st.date_input("Preferred Timeline (Start)", value=datetime.date.today())
    end_date = st.date_input("Preferred Timeline (End)", value=datetime.date.today() + datetime.timedelta(days=90))
else:
    start_date = "No preferred date"
    end_date = "No preferred date"

resume_file = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = extract_text_from_resume(resume_file) if resume_file else ""
if resume_file: st.success("Resume uploaded!")

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
    st.write("\u2661 AI Matching in Progress...")

    results = hybrid_analyze(profile_text, internships)

    st.subheader("\u2315 Top Matches:")
    for score, internship, extracted in results:
        st.markdown(f"**{internship['company']} - {internship['title']}**")
        st.write(f"Score: {score:.3f}")
        st.write(f"Location: {internship['location']}")
        st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
        with st.expander("Full Description"):
            st.write(internship['description'])
        with st.expander("Extracted Information"):
            for k, v in extracted.items():
                st.write(f"{k}: {v}")
        st.write("---")

    G = nx.Graph()
    G.add_node("You")
    for score, internship, _ in results:
        node = f"{internship['company']}\n{internship['title']}"
        G.add_node(node)
        G.add_edge("You", node, weight=score)
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read()
        components.html(source_code, height=650, width=900)
