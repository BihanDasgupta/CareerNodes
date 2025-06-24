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
import html
from pyvis.network import Network
import time

# Load environment variables
load_dotenv()

# Custom CSS for cyber-style UI
st.markdown("""
<style>
    /* Main background and container styling */
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e0e0e0;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Title styling with cyber glow effect */
    h1 {
        background: linear-gradient(45deg, #00d4ff, #0099cc, #00d4ff);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: glow 3s ease-in-out infinite alternate;
        text-align: center;
        font-weight: bold;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
        margin-bottom: 0.5rem;
    }
    
    @keyframes glow {
        from { background-position: 0% 50%; }
        to { background-position: 100% 50%; }
    }
    
    /* Subtitle styling */
    h3 {
        color: #00d4ff;
        text-align: center;
        font-weight: 300;
        margin-bottom: 2rem;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }
    
    /* Input field styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 8px !important;
        color: #e0e0e0 !important;
        padding: 10px !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #00ffff !important;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.3) !important;
        outline: none !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #00d4ff, #0099cc) !important;
        border: none !important;
        border-radius: 25px !important;
        color: #0a0a0a !important;
        font-weight: bold !important;
        padding: 12px 30px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #00ffff, #00d4ff) !important;
        box-shadow: 0 6px 20px rgba(0, 255, 255, 0.4) !important;
        transform: translateY(-2px) !important;
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        background: rgba(26, 26, 46, 0.6) !important;
        border: 2px dashed #00d4ff !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }
    
    /* Multiselect styling */
    .stMultiSelect > div > div > div {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 8px !important;
    }
    
    /* Checkbox styling */
    .stCheckbox > div > div > div {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 6px !important;
    }
    
    /* Date input styling */
    .stDateInput > div > div > input {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 8px !important;
        color: #e0e0e0 !important;
    }
    
    /* Success message styling */
    .stSuccess {
        background: rgba(0, 255, 0, 0.1) !important;
        border: 2px solid #00ff00 !important;
        border-radius: 8px !important;
        color: #00ff00 !important;
    }
    
    /* Error message styling */
    .stError {
        background: rgba(255, 0, 0, 0.1) !important;
        border: 2px solid #ff0000 !important;
        border-radius: 8px !important;
        color: #ff0000 !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 8px !important;
        color: #00d4ff !important;
        font-weight: bold !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(26, 26, 46, 0.6) !important;
        border: 1px solid #00d4ff !important;
        border-radius: 8px !important;
        margin-top: 5px !important;
    }
    
    /* Job listing cards */
    .job-card {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 15px 0 !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    
    .job-card:hover {
        border-color: #00ffff !important;
        box-shadow: 0 6px 20px rgba(0, 255, 255, 0.3) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Score display */
    .score-display {
        background: linear-gradient(45deg, #00d4ff, #0099cc) !important;
        color: #0a0a0a !important;
        padding: 8px 16px !important;
        border-radius: 20px !important;
        font-weight: bold !important;
        display: inline-block !important;
        margin: 5px 0 !important;
    }
    
    /* Link styling */
    a {
        color: #00d4ff !important;
        text-decoration: none !important;
        transition: all 0.3s ease !important;
    }
    
    a:hover {
        color: #00ffff !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5) !important;
    }
    
    /* Divider styling */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #00d4ff, transparent) !important;
        margin: 20px 0 !important;
    }
    
    /* Loading animation */
    .loading-text {
        color: #00d4ff !important;
        text-align: center !important;
        font-weight: bold !important;
        animation: pulse 2s infinite !important;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Graph container styling */
    .graph-container {
        background: rgba(26, 26, 46, 0.8) !important;
        border: 2px solid #00d4ff !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin: 20px 0 !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

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
    top_candidates = preliminary[:50]

    results = []
    for sim, internship in top_candidates:
        job_text = f"{internship['title']} at {internship['company']} located in {internship['location']}. Description: {internship['description']} Salary Range: ${internship['salary_min']}-${internship['salary_max']}"
        prompt = f"""
You are an internship matching AI given a USER PROFILE and JOB LISTING. Analyze and assign a MATCH_SCORE from 0 to 1 based on how suitable this listing is for the user. Take into account the user's GPA, skills, preferred location, education level, prior experience, preferred work type, preferred salary, preferred schedule, preferred industry, preferred organization type, desired timeline, any details from their resume, and current or intended major if provided, and how well that aligns with what both the user and job is looking for and/or requiring. Only output the score. Do not give any listings 0 unless nothing of the user data matches the job listing. In addition to your original analysis/score following the preceeding instructions, if the job listing is not hiring the user's education level or is completelyunrelated to the user's skill set and major/career path, rank it lower.

USER PROFILE:
{user_profile_text}

JOB LISTING:
{job_text}

MATCH_SCORE:
"""
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        try:
            score = float(reply.split()[0])
            score = max(0.0, min(1.0, score))
        except:
            score = 0.5  # Default to neutral if parsing fails

        explanation_prompt = f"""
You are a career advisor AI. Explain in 2-3 sentences why this job listing is a good match for you based on your profile. Be specific, professional, and helpful.

USER PROFILE:
{user_profile_text}

JOB LISTING:
{job_text}

EXPLANATION:
"""
        time.sleep(1)
        explanation_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": explanation_prompt}]
        )
        explanation = explanation_response.choices[0].message.content.strip()
        time.sleep(1)
        results.append((score, internship, explanation))

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
            "redirect_url": job.get("redirect_url", "")
        })

    user_inputs = {
        "gpa": gpa, "education": education, "school": school, "major": major,
        "skills": skills, "location": location, "industry": industry_preference,
        "org_type": org_type_preference, "schedule": schedule_preference,
        "salary_min": salary_min, "salary_max": salary_max,
        "start_date": start_date, "end_date": end_date
    }
    profile_text = create_user_profile_text(user_inputs, resume_text)
    st.markdown('<p class="loading-text">🤖 AI Matching in Progress...</p>', unsafe_allow_html=True)

    results = hybrid_analyze(profile_text, internships)

    st.subheader("\u2315 Top Matches:")
    for score, internship, explanation in results:
        # Create a job card with cyber styling
        st.markdown(f"""
        <div class="job-card">
            <h4 style="color: #00d4ff; margin-bottom: 10px;">{internship['company']} - {internship['title']}</h4>
            <div class="score-display">Match Score: {score:.3f}</div>
            <p><strong>Location:</strong> {internship['location']}</p>
            <p><strong>Salary:</strong> ${internship['salary_min']} - ${internship['salary_max']}</p>
            <p><strong>Work Type:</strong> {type_preference}</p>
            <p><strong>Schedule:</strong> {schedule_preference}</p>
            <p><strong>Industry:</strong> {', '.join(industry_preference)}</p>
            <p><strong>Org Type:</strong> {', '.join(org_type_preference)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if internship["redirect_url"]:
            st.markdown(f'<p><a href="{internship["redirect_url"]}" target="_blank">🔗 View Job Posting</a></p>', unsafe_allow_html=True)
    
        with st.expander("🤖 AI Explanation"):
            st.markdown(f'<div style="background: rgba(26, 26, 46, 0.6); padding: 15px; border-radius: 8px; border-left: 4px solid #00d4ff;">{explanation}</div>', unsafe_allow_html=True)

        with st.expander("📋 Job Description"):
            st.markdown(f'<div style="max-height:400px; overflow:auto; background: rgba(26, 26, 46, 0.6); padding: 15px; border-radius: 8px; border-left: 4px solid #00d4ff;">{internship["description"]}</div>', unsafe_allow_html=True)
 
        st.markdown('<hr>', unsafe_allow_html=True)

   G = nx.Graph()
G.add_node("You", size=30, color="#FF0000")

for score, internship, _ in results:
    node_label = f"{internship['company']} - {internship['title']}"
    G.add_node(node_label, 
               size=20 + score * 20, 
               color=f"rgba({int(255 - score*200)}, {int(score*200)}, 150, 0.9)")
    # Distance inversely proportional to score
    distance = 100 * (1 - score + 0.1)  # avoid division by zero
    G.add_edge("You", node_label, value=score * 10, length=distance)

net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
net.from_nx(G)

# Enable better physics simulation
net.toggle_physics(True)
net.set_options("""
var options = {
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -80,
      "centralGravity": 0.005,
      "springLength": 150,
      "springConstant": 0.08
    },
    "maxVelocity": 50,
    "solver": "forceAtlas2Based",
    "timestep": 0.35,
    "stabilization": {"iterations": 150}
  }
}
""")

net.save_graph("graph.html")
