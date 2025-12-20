import streamlit as st
from google import genai  # הספרייה החדשה 
import json
import os
import pypdf
import html
import time
import pandas as pd
from dotenv import load_dotenv

# --- 1. Init & Config ---
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

# יצירת ה-Client החדש פעם אחת בלבד 
client = genai.Client(api_key=API_KEY) if API_KEY else None

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .task-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 
    .badge {
        padding: 4px 8px;
        border-radius: 8px;
        color: white; 
        font-weight: bold;
        font-size: 0.8em;
    }
    .bg-Hard { background-color: #ff4b4b; }
    .bg-Medium { background-color: #ffa726; }
    .bg-Easy { background-color: #66bb6a; }
    .profile-card {
        background: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. Logic & Helpers (גרסה מעודכנת בלבד) ---

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except:
        return None

def get_initial_plan(subject, topic, context_text=None):
    if not client:
        st.error("API Client not initialized.")
        return None

    source = f"PDF Content: {context_text[:15000]}" if context_text else f"Topic: {topic}"
    
    prompt = f"""
    Gamify a study plan for {subject}: {topic}.
    Create 5 study micro-tasks sorted by difficulty (1 Hard, 2 Medium, 2 Easy).
    Source: {source}
    Return STRICT JSON:
    {{
        "tasks": [
            {{"text": "Task...", "difficulty": "Hard", "xp": 300}},
            {{"text": "Task...", "difficulty": "Medium", "xp": 150}},
            {{"text": "Task...", "difficulty": "Medium", "xp": 150}},
            {{"text": "Task...", "difficulty": "Easy", "xp": 50}},
            {{"text": "Task...", "difficulty": "Easy", "xp": 50}}
        ]
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Gemini Error: {e}")
        return None

def get_new_task(subject, topic, difficulty, context_text=None):
    if not client: return "Review notes."
    prompt = f"Create 1 new {difficulty} study task for {topic} in {subject}. Return ONLY the task text."
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.strip()
    except:
        return "Complete a practice quiz."

# --- 4. Gamification ---
BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "You are losing neurons!"),
    (300, "🧠 Brain Builder", "Building momentum..."),
    (700, "🔥 Brain Heater", "You're getting warm!"),
    (1200, "⚡ High Voltage", "You're on fire!"),
    (1800, "🧬 Neuron Party", "Can you feel it?!"),
    (2500, "🌌 GALAXY BRAIN", "Academic God Mode.")
]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    next_limit = BRAIN_LEVELS[1][0]
    for i, level in enumerate(BRAIN_LEVELS):
        if xp >= level[0]:
            current = level
            next_limit = BRAIN_LEVELS[i + 1][0] if i + 1 < len(BRAIN_LEVELS) else xp * 1.5
    return current, next_limit

# --- 5. Event Handlers ---
def handle_complete(index):
    task = st.session_state.current_tasks[index]
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1
    
    new_text = get_new_task(st.session_state.user_details['sub'], 
                            st.session_state.user_details['top'], 
                            task['difficulty'], 
                            st.session_state.user_details['pdf_text'])
    
    st.session_state.current_tasks.pop(index)
    st.session_state.current_tasks.append({"text": new_text, "difficulty": task['difficulty'], "xp": task['xp']})
    st.toast("✅ Task Completed!")

def handle_reroll(index):
    if st.session_state.xp < 20:
        st.toast("🚫 Need 20 XP!")
        return
    st.session_state.xp -= 20
    task = st.session_state.current_tasks[index]
    new_text = get_new_task(st.session_state.user_details['sub'], 
                            st.session_state.user_details['top'], 
                            task['difficulty'], 
                            st.session_state.user_details['pdf_text'])
    st.session_state.current_tasks[index]['text'] = new_text
    st.toast("🎲 Rerolled!")

def reset_session(keep_xp=True):
    st.session_state.current_tasks = []
    st.session_state.user_details = {}
    if not keep_xp:
        st.session_state.xp = 0
        st.session_state.tasks_completed = 0

# --- 6. Session State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# --- 7. Page Renderers ---
def render_profile():
    st.title("👤 Brain Profile")
    (lvl_xp, lvl_title, lvl_desc), next_xp = get_brain_status(st.session_state.xp)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total XP", st.session_state.xp)
    with c2:
        st.write(f"**Current Rank:** {lvl_title}")
        st.caption(lvl_desc)

def render_arcade():
    st.title("🎮 Arcade Mode")
    if not st.session_state.user_details:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("manual"):
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Calculus")
                if st.form_submit_button("Start Game"):
                    data = get_initial_plan(sub, top)
                    if data:
                        st.session_state.current_tasks = data.get("tasks", [])
                        st.session_state.user_details = {"sub": sub, "top": top, "pdf_text": None}
                        st.rerun()
        with col2:
            with st.form("pdf"):
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze PDF"):
                    if f:
                        txt = extract_text_from_pdf(f)
                        data = get_initial_plan("PDF Analysis", f.name, txt)
                        if data:
                            st.session_state.current_tasks = data.get("tasks", [])
                            st.session_state.user_details = {"sub": "PDF", "top": f.name, "pdf_text": txt}
                            st.rerun()
    else:
        for i, task in enumerate(st.session_state.current_tasks):
            st.markdown(f'<div class="task-card diff-{task["difficulty"]}">{task["text"]} (+{task["xp"]} XP)</div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1: st.button("Done", key=f"d{i}", on_click=handle_complete, args=(i,))
            with b2: st.button("Reroll", key=f"r{i}", on_click=handle_reroll, args=(i,))
        
        if st.button("End Mission"):
            reset_session()
            st.rerun()

# --- 8. Router ---
if not API_KEY:
    st.error("Missing API Key.")
    st.stop()

with st.sidebar:
    page = st.radio("Menu", ["🎮 Arcade Mode", "👤 Brain Profile"])

if page == "🎮 Arcade Mode": render_arcade()
else: render_profile()
