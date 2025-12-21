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
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide"
)

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 10px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 
    .badge { padding: 5px 10px; border-radius: 8px; color: white; font-weight: bold; font-size: 0.8em; }
    .bg-Hard { background-color: #ff4b4b; }
    .bg-Medium { background-color: #ffa726; }
    .bg-Easy { background-color: #66bb6a; }
    .profile-card { background: white; padding: 25px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI Core (לא נגענו בהגדרות המודל) ---
def get_ai_client():
    if not API_KEY:
        st.error("Missing API Key!")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_response(prompt, is_json=False):
    client = get_ai_client()
    if not client: return None
    model_id = "gemini-2.5-flash"
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json" if is_json else "text/plain"
    )
    try:
        response = client.models.generate_content(model=model_id, contents=prompt, config=config)
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_initial_plan(subject, topic, context=""):
    # עדכון הפרומפט לבקשת פתרון (Solution)
    prompt = f"""
    Create a study plan for {subject}: {topic}. {f'Context: {context[:5000]}' if context else ''}
    Return exactly 5 tasks (1 Hard, 2 Medium, 2 Easy). 
    For each task, provide a "solution" which is a brief answer or explanation.
    Return ONLY JSON:
    {{ "tasks": [
        {{"text": "Task...", "difficulty": "Hard", "xp": 300, "solution": "The answer is..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "Explanation..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "Explanation..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "Explanation..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "Explanation..."}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task_json(subject, topic, diff):
    # פונקציה חדשה שמחזירה אובייקט JSON הכולל פתרון
    prompt = f"""
    Create one new {diff} study task for {subject}: {topic}. 
    Provide the task text and a brief solution.
    Return ONLY JSON: {{ "text": "...", "solution": "..." }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else {"text": "Review materials", "solution": "Check your notes."}

# --- 4. Gamification Logic ---
BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "Building neurons..."),
    (300, "🧠 Brain Builder", "Foundation set!"),
    (800, "🔥 Brain Heater", "Getting warm!"),
    (1500, "⚡ High Voltage", "Sparking intelligence!"),
    (2500, "🌌 GALAXY BRAIN", "Master of the Universe.")
]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    next_limit = BRAIN_LEVELS[1][0]
    for i, level in enumerate(BRAIN_LEVELS):
        if xp >= level[0]:
            current = level
            next_limit = BRAIN_LEVELS[i+1][0] if i+1 < len(BRAIN_LEVELS) else xp * 1.5
    return current, next_limit

# --- 5. Session State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# --- 6. UI Renderers ---

def render_profile():
    st.title("👤 Brain Profile")
    (lvl_xp, lvl_title, lvl_desc), _ = get_brain_status(st.session_state.xp)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="profile-card"><h2>{lvl_title}</h2><p>{lvl_desc}</p><h3>XP: {st.session_state.xp}</h3></div>', unsafe_allow_html=True)
    with c2:
        st.metric("Tasks Completed", st.session_state.tasks_completed)
        st.metric("Current Level", int(st.session_state.xp / 500) + 1)

def render_arcade():
    st.title("🎮 Arcade Mode")
    
    # XP Bar
    (lvl_xp, lvl_title, _), next_limit = get_brain_status(st.session_state.xp)
    prog = min((st.session_state.xp - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.write(f"**Rank:** {lvl_title}")
    st.progress(prog)

    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Search", "📄 PDF Analysis"])
        with t1:
            with st.form("f1"):
                sub = st.text_input("Subject", "History")
                top = st.text_input("Topic", "World War II")
                if st.form_submit_button("Start Mission", use_container_width=True):
                    plan = get_initial_plan(sub, top)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("f2"):
                sub_pdf = st.text_input("Subject")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play", use_container_width=True):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan(sub_pdf, f.name, txt)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub_pdf, "top": f.name, "pdf_text": txt}
                            st.rerun()
    else:
        st.subheader(f"Mission: {st.session_state.user_details['top']}")
        
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            xp_reward = task['xp']
            
            # כרטיס המשימה
            st.markdown(f"""
                <div class="task-card diff-{d}">
                    <span class="badge bg-{d}">{d} | +{xp_reward} XP</span>
                    <div style="font-size: 1.1em; margin-top:10px;">{html.escape(task['text'])}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # כפתורים
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ I Succeeded!", key=f"done_{i}", use_container_width=True, type="primary"):
                    st.session_state.xp += xp_reward
                    st.session_state.tasks_completed += 1
                    with st.spinner("Fetching new challenge..."):
                        new_data = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                        st.session_state.current_tasks[i] = {**new_data, "difficulty": d, "xp": xp_reward}
                    st.toast(f"Legendary! +{xp_reward} XP")
                    if d == "Hard": st.balloons()
                    st.rerun()
            with c2:
                if st.button("🎲 Reroll (-20 XP)", key=f"roll_{i}", use_container_width=True):
                    if st.session_state.xp >= 20:
                        st.session_state.xp -= 20
                        with st.spinner("Rerolling task..."):
                            new_data = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                            st.session_state.current_tasks[i] = {**new_data, "difficulty": d, "xp": xp_reward}
                        st.rerun()
                    else:
                        st.toast("Not enough XP!")
            
            # הצגת פתרון (החלונית הנפתחת)
            with st.expander("💡 View Solution"):
                st.write(task.get('solution', 'No solution provided for this task.'))
            st.write("") # מרווח

        if st.button("🏳️ End Mission", use_container_width=True):
            st.session_state.user_details = {}
            st.rerun()

# --- 7. Sidebar ---
with st.sidebar:
    st.title("🧠 BrainWash")
    page = st.radio("Go to", ["Arcade", "Profile"])
    st.divider()
    st.write(f"**Current XP:** {st.session_state.xp}")

if page == "Arcade": render_arcade()
else: render_profile()
