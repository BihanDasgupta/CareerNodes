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
from sklearn.metrics.pairwise import cosine_similarity

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

# Functions
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
        f"Skills: {', '.join(user_inputs['skills'])}",
        f"Preferred Location: {user_inputs['location']}",
        f"Preferred Industry: {', '.join(user_inputs['industry'])}",
        f"Preferred Org Type: {', '.join(user_inputs['org_type'])}",
        f"Preferred Schedule: {user_inputs['schedule']}",
        f"Desired Salary: ${user_inputs['salary_min']} - ${user_inputs['salary_max']}",
        f"Resume: {resume_text if resume_text else 'No resume provided'}"
    ]
    return "\n".join(profile_parts)

def ai_match_score(user_profile_text, job_text):
    prompt = f"""
You are an internship matching assistant.
Given the following USER PROFILE and JOB LISTING, evaluate how well this internship matches the user. Consider all of the factors provided to you in the USER PROFILE including both what the user is looking for and what requirements the user meets, and how well the JOB LISTING matches those factors based on both what it requires, is looking for, and has to offer.
Return a score ONLY between 0 and 1, where 1 means perfect match and 0 means not suitable at all.

USER PROFILE:
{user_profile_text}

JOB LISTING:
{job_text}

Only return the score as a decimal between 0 and 1.
"""
    
    response = co.chat(model="command-r-plus", message=prompt)
    reply = response.text.strip()
    try:
        score = float(reply)
        score = max(0.0, min(1.0, score))
    except:
        score = 0.0
    return score

# Streamlit UI
st.title("CareerNodes: AI-Powered Graphical Internship Matcher")

gpa = st.number_input("Enter your GPA", min_value=0.0, max_value=4.0, step=0.01)
education = st.selectbox("Education Level", ["In High School", "High School Diploma", "In Undergrad", "Associate's Degree", "Bachelor's Degree", "In Grad School"])
skills_input = st.text_input("Enter your skills (comma-separated):")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
type_preference = st.selectbox("Preferred Work Type", ["Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location (City, State or Remote):")
industry_preference = st.multiselect("Preferred Industry", ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit","Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])
org_type_preference = st.multiselect("Preferred Organization Type", ["Startup", "Large Company (Enterprise)", "Small Business", "University / Research Institution", "Government Agency", "Nonprofit Organization", "Venture Capital / Accelerator", "Other"])
schedule_preference = st.selectbox("Preferred Work Schedule", ["Full-Time", "Part-Time"])
salary_min = st.number_input("Minimum desired salary ($)", min_value=0)
salary_max = st.number_input("Maximum desired salary ($)", min_value=0)

resume_file = st.file_uploader("Upload your resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = ""
if resume_file:
    resume_text = extract_text_from_resume(resume_file)
    st.write("Resume successfully uploaded!")
    st.write(resume_text[:1000])

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
        "gpa": gpa,
        "education": education,
        "skills": skills,
        "location": location,
        "industry": industry_preference,
        "org_type": org_type_preference,
        "schedule": schedule_preference,
        "salary_min": salary_min,
        "salary_max": salary_max
    }

    user_profile_text = create_user_profile_text(user_inputs, resume_text)
    st.write("♡ Finding your perfect match...")

    results = []
    for internship in internships:
        job_text = f"{internship['title']} at {internship['company']} in {internship['location']}. Description: {internship['description']}. Salary: ${internship['salary_min']} - ${internship['salary_max']}"
        score = ai_match_score(user_profile_text, job_text)
        results.append((score, internship))

    results.sort(reverse=True, key=lambda x: x[0])

    st.subheader("⌕ Top Matches:")
    scrollable = st.container()
    with scrollable:
        for similarity, internship in results:
            st.markdown(f"**{internship['company']} - {internship['title']}**")
            st.write(f"Similarity Score: {similarity:.3f}")
            st.write(f"Location: {internship['location']}")
            st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
            with st.expander("Full Description"):
                st.write(internship['description'])
            st.write("---")

    # Graph Visualization with top 50 matches
    G = nx.Graph()
    G.add_node("You")
    for similarity, internship in results[:50]:
        node_label = f"{internship['company']}\n{internship['title']}"
        G.add_node(node_label)
        G.add_edge("You", node_label, weight=similarity)

    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read()
        components.html(source_code, height=650, width=900)
