import streamlit as st
import requests
import os
import PyPDF2
import cohere
import numpy as np
from dotenv import load_dotenv
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

# Load environment variables
load_dotenv()

# Load secrets
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

# ---------------------- FUNCTIONS ----------------------
def fetch_internships(query, location, results_limit=50):
    all_results = []
    pages = (results_limit // 20) + 1
    for page in range(1, pages+1):
        url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/{page}"
        params = {
            'app_id': ADZUNA_APP_ID,
            'app_key': ADZUNA_APP_KEY,
            'what': query,
            'where': location,
            'results_per_page': 20,
            'content-type': 'application/json'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            all_results.extend(data.get('results', []))
        else:
            st.error("Failed to fetch data from Adzuna API.")
            break
    return all_results[:results_limit]

def extract_resume_text(file):
    text = ""
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    elif file.name.endswith(".txt"):
        text = file.read().decode("utf-8")
    return text

def build_user_profile(user_inputs, resume_text=""):
    profile = f"""
The candidate has a GPA of {user_inputs['gpa']}. 
Skills: {', '.join(user_inputs['skills'])}.
Education Level: {user_inputs['education']}.
Preferred Location: {user_inputs['location']}.
Preferred Industry: {', '.join(user_inputs['industry'])}.
Organization Type: {', '.join(user_inputs['org_type'])}.
Work Type: {user_inputs['work_type']}. 
Schedule: {user_inputs['schedule']}.
Desired Salary Range: ${user_inputs['salary_min']} - ${user_inputs['salary_max']}.
Resume Text: {resume_text}
"""
    return profile

def match_with_ai(user_profile, job_descriptions):
    prompts = [
        f"User Profile: {user_profile}\n\nJob Description: {desc}\n\nHow good is this match? Respond with a score between 0 (not suitable) and 1 (perfect match)."
        for desc in job_descriptions
    ]

    scores = []
    try:
        response = co.chat(
            model="command-r-plus",
            chat_history=[],
            message=prompts,
            temperature=0.2
        )
        for item in response.generations:
            try:
                score = float(item.text.strip())
                scores.append(score)
            except:
                scores.append(0.0)
    except Exception as e:
        st.error(f"Cohere AI matching failed: {str(e)}")
    return scores

def display_graph(matches):
    G = nx.Graph()
    G.add_node("You")
    for score, internship in matches[:50]:
        label = f"{internship['title']}\n{internship['company']}"
        G.add_node(label)
        G.add_edge("You", label, weight=score)
    net = Network(height="600px", width="100%", bgcolor="#222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")
    with open("graph.html", "r", encoding='utf-8') as file:
        html_content = file.read()
    components.html(html_content, height=600, width=800)

# ------------------- STREAMLIT APP -------------------
st.title("CareerNodes Phase 3: Intelligent AI Internship Matcher")

# Inputs
gpa = st.number_input("GPA", 0.0, 4.0, step=0.01)
skills_input = st.text_input("Skills (comma-separated):")
skills = [s.strip() for s in skills_input.split(",") if s.strip()]
education = st.selectbox("Education Level:", ["In High School", "High School Diploma", "In Undergrad", "Associate's Degree", "Bachelor's Degree", "In Grad School"])
location = st.text_input("Preferred Location:")
industry = st.multiselect("Preferred Industry:", ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit", "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])
org_type = st.multiselect("Organization Type:", ["Startup", "Large Company", "Small Business", "University / Research", "Government Agency", "Nonprofit", "Venture Capital", "Other"])
work_type = st.selectbox("Work Type:", ["Remote", "On-Site", "Hybrid"])
schedule = st.selectbox("Schedule:", ["Full-Time", "Part-Time"])
salary_min = st.number_input("Min Salary ($):", 0)
salary_max = st.number_input("Max Salary ($):", 0)

resume_file = st.file_uploader("Upload Resume (PDF or TXT):", type=["pdf", "txt"])
resume_text = extract_resume_text(resume_file) if resume_file else ""
if resume_file:
    st.success("Resume uploaded successfully!")

if st.button("Find Matches"):
    user_inputs = {
        "gpa": gpa,
        "skills": skills,
        "education": education,
        "location": location,
        "industry": industry,
        "org_type": org_type,
        "work_type": work_type,
        "schedule": schedule,
        "salary_min": salary_min,
        "salary_max": salary_max
    }

    user_profile = build_user_profile(user_inputs, resume_text)

    raw_internships = fetch_internships("internship", location, results_limit=50)
    job_descriptions = [job.get("description", "") for job in raw_internships]
    
    st.write("Generating AI matching scores...")
    similarity_scores = match_with_ai(user_profile, job_descriptions)

    combined_results = list(zip(similarity_scores, raw_internships))
    combined_results.sort(reverse=True, key=lambda x: x[0])

    st.subheader("Top AI Matches:")
    for score, job in combined_results:
        with st.expander(f"{job.get('title')} - {job.get('company', {}).get('display_name', '')} | Score: {score:.2f}"):
            st.write(f"Location: {job.get('location', {}).get('display_name', '')}")
            st.write(f"Salary: ${job.get('salary_min')} - ${job.get('salary_max')}")
            st.write(f"Description: {job.get('description', '')}")

    st.subheader("Visual Graph of Top Matches")
    display_graph(combined_results)
