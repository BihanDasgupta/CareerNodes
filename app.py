import streamlit as st
import requests
import re
import os
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from dotenv import load_dotenv
import PyPDF2

# --- Install these packages if not installed ---
# pip install python-dotenv
# pip install streamlit requests pyvis networkx PyPDF2

# --- Run with: streamlit run app.py ---

# --- API CONFIG ---
load_dotenv()  # Load local .env if exists

if "adzuna" in st.secrets:
    ADZUNA_APP_ID = st.secrets["adzuna"]["app_id"]
    ADZUNA_APP_KEY = st.secrets["adzuna"]["app_key"]
else:
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
    ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

ADZUNA_COUNTRY = "us"

# --- Functions ---
def fetch_internships(query, location, results_limit=20):
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

def extract_skills(description):
    keywords = re.findall(r'\b[A-Za-z]{3,}\b', description.lower())
    return list(set(keywords))

def calculate_score(user, internship):
    score = 0
    skill_matches = set(user['skills']) & set(internship['skills'])
    score += len(skill_matches) * 3

    if user['gpa'] >= internship['gpa']:
        score += 5
    if user['type'] == internship['type']:
        score += 3
    if user['schedule'] == internship['schedule']:
        score += 3
    if internship['industry'] in user['industry']:
        score += 4
    if internship['org_type'] in user['org_type']:
        score += 4
    if internship['salary_min'] >= user['salary_min'] and internship['salary_max'] <= user['salary_max']:
        score += 3
    if user['location'].lower() in internship['location'].lower():
        score += 3
    return score

# --- Streamlit App ---
st.title("CareerNodes: Graphical Internship Matcher")

# User Inputs
gpa = st.number_input("Enter your GPA", min_value=0.0, max_value=4.0, step=0.01)
skills_input = st.text_input("Enter your skills (comma-separated):")
skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]

type_preference = st.selectbox("Preferred Work Type", ["Remote", "On-Site", "Hybrid"])
location = st.text_input("Preferred Location (City, State or Remote):")

industry_preference = st.multiselect(
    "Preferred Industry",
    ["Tech", "Finance", "Healthcare", "Education", "Government", "Nonprofit",
     "Consulting", "Manufacturing", "Media", "Energy", "Legal", "Other"]
)

org_type_preference = st.multiselect(
    "Preferred Organization Type",
    ["Startup", "Large Company (Enterprise)", "Small Business", 
     "University / Research Institution", "Government Agency", 
     "Nonprofit Organization", "Venture Capital / Accelerator", "Other"]
)

schedule_preference = st.selectbox("Preferred Work Schedule", ["Full-Time", "Part-Time"])
salary_min = st.number_input("Minimum desired salary ($)", min_value=0)
salary_max = st.number_input("Maximum desired salary ($)", min_value=0)

# Resume Upload
resume_file = st.file_uploader("Upload your resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = ""
if resume_file:
    if resume_file.name.endswith(".txt"):
        resume_text = resume_file.read().decode("utf-8")
    elif resume_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(resume_file)
        for page in pdf_reader.pages:
            resume_text += page.extract_text()
    st.write("Resume successfully uploaded!")
    st.write(resume_text[:500])

# Extract skills from resume text
resume_skills = re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower())
resume_skills = list(set(resume_skills))
skills += resume_skills

if st.button("Find Matches"):
    internships_raw = fetch_internships("internship", location)
    internships = []
    for job in internships_raw:
        description = job.get("description", "")
        extracted_skills = extract_skills(description)
        internships.append({
            "company": job.get("company", {}).get("display_name", "Unknown"),
            "title": job.get("title", "Unknown Title"),
            "skills": extracted_skills,
            "gpa": 0.0,
            "type": type_preference,
            "location": job.get("location", {}).get("display_name", "Unknown Location"),
            "industry": "Unknown",
            "org_type": "Unknown",
            "schedule": schedule_preference,
            "salary_min": job.get("salary_min") or 0,
            "salary_max": job.get("salary_max") or 0,
            "description": description
        })

    user = {
        "gpa": gpa,
        "skills": skills,
        "type": type_preference,
        "location": location,
        "industry": industry_preference,
        "org_type": org_type_preference,
        "schedule": schedule_preference,
        "salary_min": salary_min,
        "salary_max": salary_max
    }

    results = []
    for internship in internships:
        score = calculate_score(user, internship)
        results.append((score, internship))

    results.sort(reverse=True, key=lambda x: x[0])

    st.subheader("Top Matches:")
    for score, internship in results:
        st.markdown(f"**{internship['company']} - {internship['title']}**")
        st.write(f"Score: {score}")
        st.write(f"Location: {internship['location']}")
        st.write(f"Salary: ${internship['salary_min']} - ${internship['salary_max']}")
        st.write(f"Description: {internship['description'][:300]}...")
        st.write("---")

    # Graph visualization
    G = nx.Graph()
    G.add_node("You")
    for score, internship in results[:5]:
        node_label = f"{internship['company']}\n{internship['title']}"
        G.add_node(node_label)
        G.add_edge("You", node_label, weight=score)

    net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)
    net.save_graph("graph.html")

    with open("graph.html", "r", encoding='utf-8') as HtmlFile:
        source_code = HtmlFile.read() 
        components.html(source_code, height=550, width=800)
