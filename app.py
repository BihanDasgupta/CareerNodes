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

# UI
st.markdown("""
<style>
/* Main container styling */
.main .block-container {
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    padding: 2rem;
    position: relative;
    overflow: visible !important;
}

/* Cyberpunk margin/corner nodes and subtle grid */
.main .block-container::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 1;
    background: 
        radial-gradient(circle at 30px 30px, #00d4ff 0 7px, transparent 8px),
        radial-gradient(circle at calc(100vw - 30px) 30px, #ff00ff 0 7px, transparent 8px),
        radial-gradient(circle at 30px calc(100vh - 30px), #00ff88 0 7px, transparent 8px),
        radial-gradient(circle at calc(100vw - 30px) calc(100vh - 30px), #00d4ff 0 7px, transparent 8px),
        linear-gradient(90deg, transparent 0%, #00d4ff 1px, transparent 1px) 0 0 / 50px 50px,
        linear-gradient(0deg, transparent 0%, #00d4ff 1px, transparent 1px) 0 0 / 50px 50px;
    opacity: 0.3;
}

.main .block-container::after {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 1;
    background: 
        radial-gradient(circle at 50px 50px, #ff00ff 3px, transparent 3px),
        radial-gradient(circle at calc(100% - 50px) 50px, #00ff88 3px, transparent 3px),
        radial-gradient(circle at 50px calc(100% - 50px), #00d4ff 3px, transparent 3px),
        radial-gradient(circle at calc(100% - 50px) calc(100% - 50px), #ff00ff 3px, transparent 3px);
    opacity: 0.4;
}

.main .block-container > * {
    position: relative;
    z-index: 2;
}

/* Title and subtitle styling */
h1 {
    text-align: center !important;
    background: linear-gradient(45deg, #00d4ff, #ff00ff, #00ff88);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 3rem !important;
    font-weight: 700 !important;
    text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
    animation: gradientShift 3s ease-in-out infinite;
    margin-bottom: 0.5rem !important;
    position: relative;
    z-index: 3;
}

h3 {
    text-align: center !important;
    font-size: 1.1rem !important;
    color: #b0b0b0 !important;
    font-weight: 300 !important;
    letter-spacing: 2px !important;
    margin-bottom: 2rem !important;
    position: relative;
    z-index: 3;
}

@keyframes gradientShift {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Form container styling */
.stForm {
    background: rgba(26, 26, 46, 0.9) !important;
    border: 1px solid #00d4ff !important;
    border-radius: 15px !important;
    padding: 2rem !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2) !important;
    margin: 1rem 0 !important;
    position: relative;
    z-index: 3;
    overflow: visible !important;
}

/* Label styling */
.stForm label {
    color: #00d4ff !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    margin-bottom: 0.5rem !important;
    position: relative;
    z-index: 4;
}

/* Text input styling */
.stTextInput > div > div > input {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stTextInput > div > div > input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
    background: rgba(10, 10, 10, 0.95) !important;
    z-index: 5;
}

.stTextInput > div > div > input::placeholder {
    color: #666 !important;
}

/* Number input styling */
.stNumberInput > div > div > input {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stNumberInput > div > div > input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
    background: rgba(10, 10, 10, 0.95) !important;
    z-index: 5;
}

/* Selectbox styling */
.stSelectbox > div > div > div {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stSelectbox > div > div > div:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
    background: rgba(10, 10, 10, 0.95) !important;
    z-index: 5;
}

/* Multiselect styling */
.stMultiSelect > div > div > div {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stMultiSelect > div > div > div:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
    background: rgba(10, 10, 10, 0.95) !important;
    z-index: 5;
}

/* Checkbox styling */
.stCheckbox > div > div {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stCheckbox > div > div:focus-within {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}

/* Date input styling */
.stDateInput > div > div > input {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stDateInput > div > div > input:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
    background: rgba(10, 10, 10, 0.95) !important;
    z-index: 5;
}

/* File uploader styling */
.stFileUploader > div > div {
    background: rgba(10, 10, 10, 0.9) !important;
    border: 2px solid #333 !important;
    border-radius: 8px !important;
    padding: 20px !important;
    transition: all 0.3s ease !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

.stFileUploader > div > div:hover {
    border-color: #00d4ff !important;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.3) !important;
}

/* Button styling */
.stButton > button {
    background: linear-gradient(45deg, #00d4ff, #0099cc) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #000 !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    font-size: 1rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3) !important;
    position: relative;
    z-index: 4;
}

.stButton > button:hover {
    background: linear-gradient(45deg, #0099cc, #00d4ff) !important;
    box-shadow: 0 6px 20px rgba(0, 212, 255, 0.5) !important;
    transform: translateY(-2px) !important;
}

/* Success message styling */
.stSuccess {
    background: rgba(0, 255, 136, 0.1) !important;
    border: 1px solid #00ff88 !important;
    border-radius: 8px !important;
    color: #00ff88 !important;
    padding: 12px 16px !important;
    position: relative;
    z-index: 4;
}

/* Results styling */
.stExpander > div > div {
    background: rgba(26, 26, 46, 0.9) !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    margin: 8px 0 !important;
    position: relative;
    z-index: 4;
    overflow: visible !important;
}

/* Graph container styling */
.stIframe {
    border: 2px solid #00d4ff !important;
    border-radius: 15px !important;
    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2) !important;
    margin: 2rem 0 !important;
    position: relative;
    z-index: 4;
}

/* Section headers */
h2 {
    color: #00d4ff !important;
    font-size: 1.5rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    margin: 2rem 0 1rem 0 !important;
    text-align: center !important;
    position: relative;
    z-index: 3;
}

p, div {
    color: #e0e0e0 !important;
    position: relative;
    z-index: 3;
}

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(10, 10, 10, 0.8);
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(45deg, #00d4ff, #0099cc);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(45deg, #0099cc, #00d4ff);
}
</style>
""", unsafe_allow_html=True)

st.title("✎ᝰ. CareerNodes ılıılı")
st.subheader("❤︎ A Graphical Internship Matchmaker Powered by AI ılılıılııılı")

gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, step=0.01, format="%0.2f", value=None)
if gpa == 0.0:
    gpa = None
education = st.selectbox("Education Level", [
    "Choose an option",
    "High School Junior", "High School Senior", "High School Diploma",
    "Undergrad Freshman", "Undergrad Sophomore", "Undergrad Junior",
    "Undergrad Senior", "Bachelor's Degree", "Associates Degree", "Grad Student"])
school = st.text_input("Current School (College or High School)", placeholder="Type an answer...")
major = st.text_input("Current Major or Intended Major", placeholder="Type an answer...")
skills_input = st.text_input("Skills (comma-separated)", placeholder="Type an answer...")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
type_preference = st.selectbox("Work Type", [
    "Choose an option",
    "Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location", placeholder="Type an answer...")
industry_preference = st.multiselect("Industry", ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit", "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])
org_type_preference = st.multiselect("Organization Type", ["Startup", "Large Company", "Small Business", "University / Research", "Government Agency", "Nonprofit", "Venture Capital", "Other"])
schedule_preference = st.selectbox("Schedule", [
    "Choose an option",
    "Full-Time", "Part-Time"])
salary_min = st.number_input("Min Annual Salary ($)", min_value=0, value=None)
salary_max = st.number_input("Max Annual Salary ($)", min_value=0, value=None)
if salary_min == 0: salary_min = None
if salary_max == 0: salary_max = None

# Calendar timeline selection
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
