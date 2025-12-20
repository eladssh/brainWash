import streamlit as st
import google.generativeai as genai
import json
import os
import pypdf
import html
import pandas as pd
from dotenv import load_dotenv

# --- 1. Init & Config ---
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("Missing API Key!")
    st.stop()

st.set_page_config(page_title="BrainWash: Arcade", page_icon="🧠", layout="wide")

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 
    </style>
""", unsafe_allow_html=True)

# --- 3. Logic & Helpers ---

def get_initial_plan(subject, topic, context_text=None):
    # שימוש במודל יציב עם שם מפורש
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    source = f"PDF: {context_text[:10000]}" if context_text else f"Topic: {topic}"
    prompt = f"Gamify a study plan for {subject}: {topic}. Create 5 tasks (1 Hard, 2 Medium, 2 Easy). Source: {source}. Return JSON: {{'tasks': [{{'text': '...', 'difficulty': '...', 'xp': 100}}]}}"

    try:
        # כאן אנחנו מוודאים שהתשובה היא JSON תקין
        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Gemini Error: {e}")
        return None

def get_new_task(subject, topic, difficulty, context_text=None):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"One new {difficulty} study task for {topic}. Just the text."
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return "Complete a practice question."

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except: return None

# --- 4. Gamification Logic ---
BRAIN_LEVELS = [(0, "🧟 Brain Rot"), (300, "🧠 Builder"), (700, "🔥 Heater"), (1200, "⚡ Voltage")]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    for level in BRAIN_LEVELS:
        if xp >= level[0]: current = level
    return current

# --- 5. Event Handlers ---
def handle_complete(index):
    task = st.session_state.current_tasks[index]
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1
    new_text = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], task['difficulty'])
    st.session_state.current_tasks[index] = {"text": new_text, "difficulty": task['difficulty'], "xp": task['xp']}
    st.toast("XP Gained! 🧠")

# --- 6. Session State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# --- 7. Render ---
with st.sidebar:
    st.title("BrainWash")
    page = st.radio("Menu", ["Arcade", "Profile"])
    st.metric("My XP", st.session_state.xp)

if page == "Arcade":
    if not st.session_state.user_details:
        with st.form("start"):
            sub = st.text_input("Subject", "Math")
            top = st.text_input("Topic", "Matrices")
            if st.form_submit_button("Start Mission"):
                data = get_initial_plan(sub, top)
                if data:
                    st.session_state.current_tasks = data['tasks']
                    st.session_state.user_details = {"sub": sub, "top": top}
                    st.rerun()
    else:
        for i, task in enumerate(st.session_state.current_tasks):
            st.markdown(f"<div class='task-card diff-{task['difficulty']}'>{task['text']}</div>", unsafe_allow_html=True)
            st.button("Complete", key=f"btn{i}", on_click=handle_complete, args=(i,))
        if st.button("End Game"):
            st.session_state.user_details = {}
            st.rerun()
else:
    st.title("User Profile")
    status = get_brain_status(st.session_state.xp)
    st.header(f"Rank: {status[1]}")
    st.write(f"Total XP: {st.session_state.xp}")
