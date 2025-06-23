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

# --- Load environment variables ---
load_dotenv()

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

# --- Functions ---
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
        f"Preferred Work Type: {user_inputs['type']}",
        f"Preferred Schedule: {user_inputs['schedule']}",
        f"Desired Salary: ${user_inputs['salary_min']} - ${user_inputs['salary_max']}",
        f"Resume: {resume_text}"
    ]
    return "\n".join(profile_parts)

def embed_text(text):
    if not text.strip():
        st.error("No valid text to embed.")
        return None
    response = co.embed(texts=[text], model="embed-english-v3.0", input_type="search_document")
    return np.array(response.embeddings)

def calculate_similarity(user_embedding, job_embedding):
    return cosine_similarity(user_embedding, job_embedding)[0][0]

# --- Streamlit App ---
st.title("CareerNodes: AI-Powered Internship Matcher (Phase 3)")

# User Inputs
gpa = st.number_input("Enter your GPA", min_value=0.0, max_value=4.0, step=0.01)
skills_input = st.text_input("Enter your skills (comma-separated):")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]

education = st.selectbox("Your Education Level", [
    "In High School", "High School Diploma", "In Undergrad", "Associate's Degree",
    "Bachelor's Degree", "In Grad School"])

type_preference = st.selectbox("Preferred Work Type", ["Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location (City, State or Remote):")

industry_preference = st.multiselect("Preferred Industry", [
    "Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit",
    "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"])

org_type_preference = st.multiselect("Preferred Organization Type", [
    "Startup", "Large Company (Enterprise)", "Small Business", 
    "University / Research Institution", "Government Agency", 
    "Nonprofit Organization", "Venture Capital / Accelerator", "Other"])

schedule_preference = st.selectbox("Preferred Work Schedule", ["Full-Time", "Part-Time"])
salary_min = st.number_input("Minimum desired salary ($)", min_value=0)
salary_max = st.number_input("Maximum desired salary ($)", min_value=0)

# Resume Upload
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
        "skills": skills,
        "location": location,
        "industry": industry_preference,
        "org_type": org_type_preference,
        "schedule": schedule_preference,
        "type": type_preference,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "education": education
    }

    user_profile_text = create_user_profile_text(user_inputs, resume_text)
    st.write("Generating embeddings and matching...")

    user_embedding = embed_text(user_profile_text)
    results = []

    for internship in internships:
        job_text = f"Job Title: {internship['title']}\nCompany: {internship['company']}\nLocation: {internship['location']}\nDescription: {internship['description']}"
        job_embedding = embed_text(job_text)
        similarity = calculate_similarity(user_embedding, job_embedding)
        results.append((similarity, internship))

    results.sort(reverse=True, key=lambda x: x[0])

    st.subheader("Top AI-Powered Matches:")
    for similarity, internship in results:
        with st.expander(f"{internship['company']} - {internship['title']} (Similarity: {similarity:.2f})"):
            st.write(f"Location: {internship['location']}")
            st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
            st.write("Description:")
            st.write(internship['description'])

    # Graph visualization
    G = nx.Graph()
    G.add_node("You")
    for similarity, internship in results[:50]:
        node_label = f"{internship['company']}\n{internship['title']}"
        G.add_node(node_label)
        G.add_edge("You", node_label, weight=similarity)

    net = Network(height="700px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read()
        components.html(source_code, height=700, width=1000, scrolling=True)
