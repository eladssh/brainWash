import streamlit as st
from google import genai
from google.genai import types
import json
import os
import pypdf
import html
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv

# --- 1. Init & Config ---
load_dotenv()
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide"
)

# --- 2. CSS Styles (מעודכן לאחידות מלאה) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    /* קוביות עיצוב לבנות - אחידות לכל הפרופיל */
    .white-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6; 
        margin-bottom: 20px;
        text-align: center;
        min-height: 320px; /* מבטיח גובה אחיד לקוביות העליונות */
    }
    
    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 

    .badge-card { text-align: center; padding: 10px; }
    .badge-icon { font-size: 45px; margin-bottom: 5px; }
    .locked { filter: grayscale(100%); opacity: 0.3; }

    .brain-avatar { 
        font-size: 80px; display: block; margin-bottom: 15px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-15px); }
    }

    .friend-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 0; border-bottom: 1px solid #f8f9fa;
    }
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; }
    .online { background-color: #66bb6a; }
    .offline { background-color: #bdbdbd; }
    
    .intro-text {
        background: linear-gradient(90deg, #7F00FF 0%, #E100FF 100%);
        color: white; padding: 25px; border-radius: 20px; margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI Core (ללא שינוי כפי שביקשת) ---
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
    prompt = f"Create a study plan for {subject}: {topic}. Context: {context[:5000]} Return 5 tasks (1 Hard, 2 Medium, 2 Easy) with solutions in JSON format."
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task_json(subject, topic, diff):
    prompt = f"Create one new {diff} study task for {subject}: {topic}. Include a brief solution. Return JSON: {{'text': '...', 'solution': '...'}}"
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else {"text": "Review materials", "solution": "Check notes."}

# --- 4. Logic & State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "user_name" not in st.session_state: st.session_state.user_name = "Player 1"

ACHIEVEMENTS = [
    {"id": "first", "name": "The Initiate", "emoji": "🥉", "req": 100, "desc": "100 XP Earned"},
    {"id": "pro", "name": "Scholar", "emoji": "🥈", "req": 10, "type": "tasks", "desc": "10 Quests Done"},
    {"id": "master", "name": "Sage", "emoji": "🥇", "req": 1500, "desc": "1,500 XP Earned"},
    {"id": "god", "name": "Galaxy Brain", "emoji": "🌌", "req": 5000, "desc": "5,000 XP Earned"}
]

def get_brain_status(xp):
    levels = [(0, "🧟 Brain Rot"), (300, "🧠 Builder"), (800, "🔥 Heater"), (1500, "⚡ Voltage"), (2500, "🌌 GALAXY BRAIN")]
    current = levels[0]
    next_limit = levels[1][0]
    for i, level in enumerate(levels):
        if xp >= level[0]:
            current = level
            next_limit = levels[i+1][0] if i+1 < len(levels) else xp * 1.5
    return current, next_limit

# --- 5. UI Renderers ---

def render_profile():
    st.title("👤 Brain Profile")
    
    with st.expander("📝 Edit Identity"):
        st.session_state.user_name = st.text_input("Username", st.session_state.user_name)

    (lvl_xp, lvl_title), next_lim = get_brain_status(st.session_state.xp)
    
    # שלוש הקוביות העליונות בעיצוב זהה ואחיד
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="white-card">
                <div class="brain-avatar">🧠</div>
                <h2 style="margin:0;">{st.session_state.user_name}</h2>
                <h4 style="color: #7F00FF; margin-top:5px;">{lvl_title}</h4>
                <p>Level {int(st.session_state.xp / 500) + 1}</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="white-card">
                <h3 style="margin-top:0;">📊 Statistics</h3>
                <div style="text-align:left; margin-top:30px; font-size:1.1em;">
                    <p><strong>Total XP:</strong> {st.session_state.xp}</p>
                    <p><strong>Quests Done:</strong> {st.session_state.tasks_completed}</p>
                    <p><strong>Day Streak:</strong> 🔥 3 Days</p>
                    <p><strong>Global Rank:</strong> #1,240</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="white-card"><h3 style="margin-top:0;">👥 Buddies</h3>', unsafe_allow_html=True)
        friends = [("Sarah_Brains", "online"), ("Mike_The_Wiz", "online"), ("Lazy_Dave", "offline")]
        for name, status in friends:
            dot = "online" if status == "online" else "offline"
            st.markdown(f'<div class="friend-row"><span>{name}</span><span class="status-dot {dot}"></span></div>', unsafe_allow_html=True)
        st.write("")
        st.button("➕ Add Buddy", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # מערכת תגים (Achievements)
    st.subheader("🏆 Achievements")
    badge_cols = st.columns(len(ACHIEVEMENTS))
    for i, ach in enumerate(ACHIEVEMENTS):
        is_locked = True
        if ach.get("type") == "tasks":
            if st.session_state.tasks_completed >= ach["req"]: is_locked = False
        else:
            if st.session_state.xp >= ach["req"]: is_locked = False
        with badge_cols[i]:
            status = "locked" if is_locked else ""
            st.markdown(f"""
                <div class="white-card badge-card {status}" style="min-height:180px;">
                    <div class="badge-icon">{ach['emoji']}</div>
                    <strong>{ach['name']}</strong><br><small>{ach['desc']}</small>
                </div>
            """, unsafe_allow_html=True)

    # Focus Mode (Timer) עם כפתור עצירה
    st.divider()
    st.subheader("⏲️ Focus Mode")
    with st.expander("Start Deep Work Session"):
        focus_mins = st.slider("Select Duration (Minutes)", 5, 120, 25)
        
        c_start, c_stop = st.columns(2)
        start_trigger = c_start.button("🚀 Start Timer", use_container_width=True, type="primary")
        stop_trigger = c_stop.button("🛑 Stop & Reset", use_container_width=True)

        if start_trigger:
            placeholder = st.empty()
            for seconds in range(focus_mins * 60, 0, -1):
                # בדיקה אם המשתמש לחץ על עצירה (ב-Streamlit זה יגרום ל-Rerun)
                if stop_trigger:
                    st.rerun()
                
                mins, secs = divmod(seconds, 60)
                placeholder.metric("Concentration Remaining", f"{mins:02d}:{secs:02d}")
                time.sleep(1)
            
            st.balloons()
            st.success("Session Complete! +50 Focus XP")
            st.session_state.xp += 50
            st.rerun()

def render_arcade():
    st.markdown("""
        <div class="intro-text">
            <h2 style="margin:0;">Welcome to BrainWash Arcade 🎮</h2>
            <p style="margin-bottom:0;">Turn your study materials into an RPG adventure. Upload a PDF or search a topic to generate active learning quests. 
            Earn XP, unlock ranks, and master your subjects!</p>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Search", "📄 PDF Scan"])
        with t1:
            with st.form("manual"):
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Matrices")
                if st.form_submit_button("Launch Mission", use_container_width=True):
                    plan = get_initial_plan(sub, top)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("pdf"):
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play", use_container_width=True):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan("PDF Study", f.name, txt)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": "PDF", "top": f.name}
                            st.rerun()
    else:
        st.subheader(f"📍 Objective: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d, xp = task['difficulty'], task['xp']
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{xp} XP</span><br>{html.escape(task["text"])}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Success", key=f"d{i}", use_container_width=True, type="primary"):
                    st.session_state.xp += xp
                    st.session_state.tasks_completed += 1
                    new = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                    st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                    st.rerun()
            with c2:
                if st.button("🎲 Reroll", key=f"r{i}", use_container_width=True):
                    if st.session_state.xp >= 20:
                        st.session_state.xp -= 20
                        new = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                        st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                        st.rerun()
            with st.expander("💡 View Solution"):
                st.write(task.get('solution', 'Check your notes!'))

        if st.button("🏳️ Reset Session", use_container_width=True):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Sidebar & Router ---
with st.sidebar:
    st.title("🧠 BrainWash")
    st.write(f"Logged in as: **{st.session_state.user_name}**")
    
    (lvl_xp, lvl_title), next_limit = get_brain_status(st.session_state.xp)
    sidebar_prog = min((st.session_state.xp - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.write(f"Rank Progress: **{lvl_title}**")
    st.progress(sidebar_prog)
    
    st.divider()
    page = st.radio("Navigation", ["Arcade", "Profile"])

if page == "Arcade": render_arcade()
else: render_profile()
