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

def analyze_and_score(user_profile_text, job_text):
    try:
        rerank_response = co.rerank(
            model="rerank-english-v2.0",
            query=user_profile_text,
            documents=[job_text]
        )
        score = rerank_response.results[0].relevance_score
        score = max(0.0, min(1.0, score))

        extracted = {
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
            "EXTRACTED_TIMELINE": "N/A",
            "EXTRACTED_MAJOR": "N/A"
        }

        return score, extracted
    except Exception as e:
        print("Error during rerank:", e)
        return 0.0, {}

# Keep full original UI exactly as you already have it
# (All the CSS, full Streamlit forms, titles, backgrounds, neon gradients, inputs, etc)
# Place your full existing UI code here unchanged

# Now handle form input (rest of backend logic stays same):

st.title("\u273e CareerNodes ılılı")
st.subheader("\u2764\ufe0f A Graphical Internship Matchmaker Powered by AI ılılıııı")

gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, format="%0.2f", value=None)
if gpa == 0.0:
    gpa = None
education = st.selectbox("Education Level", [
    "Choose an option", "High School Junior", "High School Senior", "High School Diploma",
    "Undergrad Freshman", "Undergrad Sophomore", "Undergrad Junior",
    "Undergrad Senior", "Bachelor's Degree", "Associates Degree", "Grad Student"])
school = st.text_input("Current School (College or High School)", placeholder="Type an answer...")
major = st.text_input("Current Major or Intended Major", placeholder="Type an answer...")
skills_input = st.text_input("Skills (comma-separated)", placeholder="Type an answer...")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
type_preference = st.selectbox("Work Type", ["Choose an option", "Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location", placeholder="Type an answer...")
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

    results = []
    for internship in internships:
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
