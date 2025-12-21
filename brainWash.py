import streamlit as st
from google import genai
from google.genai import types
import json
import os
import pypdf
import html
import pandas as pd
from dotenv import load_dotenv

# --- 1. Init & Config ---
load_dotenv()
# הגדרה גמישה: מחפש ב-Secrets של הענן או ב-.env מקומי
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade 2.0",
    page_icon="🧠",
    layout="wide"
)

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 
    .badge { padding: 4px 8px; border-radius: 8px; color: white; font-weight: bold; font-size: 0.75em; }
    .bg-Hard { background-color: #ff4b4b; }
    .bg-Medium { background-color: #ffa726; }
    .bg-Easy { background-color: #66bb6a; }
    .profile-card { background: white; padding: 25px; border-radius: 20px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Core AI Logic (Gemini 2.0 Flash) ---

def get_ai_client():
    if not API_KEY:
        st.error("Missing API Key! Please add GOOGLE_API_KEY to Secrets.")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_response(prompt, is_json=False):
    client = get_ai_client()
    if not client: return None
    
    # שימוש בדגם הכי חדש: gemini-2.0-flash
    model_id = "gemini-2.5-flash"
    
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json" if is_json else "text/plain"
    )

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        if "429" in str(e):
            st.error("נגמרה המכסה לדקה הקרובה. גוגל מגבילה את גרסת ה-2.0. נסה שוב בעוד דקה.")
        else:
            st.error(f"AI Error: {e}")
        return None

def get_initial_plan(subject, topic, context=""):
    prompt = f"""
    Create a study plan for {subject}: {topic}. {f'Context: {context[:5000]}' if context else ''}
    Return exactly 5 tasks (1 Hard, 2 Medium, 2 Easy).
    Return ONLY JSON format:
    {{ "tasks": [
        {{"text": "Description", "difficulty": "Hard", "xp": 300}},
        {{"text": "Description", "difficulty": "Medium", "xp": 150}},
        {{"text": "Description", "difficulty": "Medium", "xp": 150}},
        {{"text": "Description", "difficulty": "Easy", "xp": 50}},
        {{"text": "Description", "difficulty": "Easy", "xp": 50}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task(subject, topic, diff):
    prompt = f"Create one {diff} study task for {subject}: {topic}. Return ONLY the task text."
    return get_ai_response(prompt) or "Review your materials."

# --- 4. State & Gamification ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

def get_rank(xp):
    if xp < 300: return "🧟 Brain Rot", "Keep building!"
    if xp < 800: return "🧠 Brain Builder", "Getting stronger!"
    return "🌌 GALAXY BRAIN", "Master Level."

# --- 5. UI Renderers ---

def render_profile():
    st.title("👤 Brain Profile")
    rank, desc = get_rank(st.session_state.xp)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="profile-card"><h2>{rank}</h2><p>{desc}</p><h3>XP: {st.session_state.xp}</h3></div>', unsafe_allow_html=True)
    with c2:
        st.metric("Completed Tasks", st.session_state.tasks_completed)

def render_arcade():
    st.title("🎮 Arcade Mode (Gemini 2.0 Flash)")
    
    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Search", "📄 PDF"])
        with t1:
            with st.form("f1"):
                sub = st.text_input("Subject")
                top = st.text_input("Topic")
                if st.form_submit_button("Start"):
                    plan = get_initial_plan(sub, top)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("f2"):
                sub_pdf = st.text_input("Subject")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze"):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan(sub_pdf, f.name, txt)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub_pdf, "top": f.name}
                            st.rerun()
    else:
        st.info(f"Mission: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{task["xp"]} XP</span><br>{html.escape(task["text"])}</div>', unsafe_allow_html=True)
            if st.button("✅ Done", key=f"btn_{i}", use_container_width=True):
                st.session_state.xp += task['xp']
                st.session_state.tasks_completed += 1
                st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                st.rerun()
        
        if st.button("🏳️ Reset"):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Navigation ---
with st.sidebar:
    st.title("🧠 BrainWash")
    page = st.radio("Menu", ["Arcade", "Profile"])

if page == "Arcade": render_arcade()
else: render_profile()

