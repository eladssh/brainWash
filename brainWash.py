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
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    /* קוביות לבנות אחידות לכל חלקי הפרופיל */
    .white-card {
        background: white; 
        padding: 25px; 
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6; 
        text-align: center;
        height: 400px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    .white-card h3 {
        margin: 0 0 15px 0;
        flex-shrink: 0;
    }
    
    .scrollable-content {
        overflow-y: auto;
        overflow-x: hidden;
        flex-grow: 1;
        text-align: left;
        padding-right: 5px;
    }

    .stat-box {
        background: #f8f9fa; 
        border-radius: 12px; 
        padding: 15px;
        margin-bottom: 10px; 
        border: 1px solid #eee;
        word-wrap: break-word;
    }

    .brain-avatar { 
        font-size: 70px; 
        display: block; 
        margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    .friend-row {
        display: flex; 
        align-items: center; 
        justify-content: space-between;
        padding: 10px 0; 
        border-bottom: 1px solid #f8f9fa;
        font-size: 0.9em;
        word-wrap: break-word;
    }
    
    .friend-row > div {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .status-dot { 
        height: 10px; 
        width: 10px; 
        border-radius: 50%; 
        display: inline-block; 
        flex-shrink: 0;
        margin-left: 10px;
    }
    .online { background-color: #66bb6a; }
    .offline { background-color: #bdbdbd; }

    .task-card {
        background: white; 
        padding: 20px; 
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); 
        border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; }
    
    .badge-card { 
        background: white; 
        padding: 15px; 
        border-radius: 15px;
        border: 1px solid #eef2f6; 
        text-align: center; 
        height: 180px;
    }
    .badge-icon { font-size: 40px; }
    .locked { filter: grayscale(100%); opacity: 0.3; }

    .intro-banner {
        background: linear-gradient(90deg, #7F00FF 0%, #E100FF 100%);
        color: white; 
        padding: 25px; 
        border-radius: 20px; 
        margin-bottom: 30px;
    }
    
    /* תיקון לכפתורים בתוך white-card */
    .white-card .stButton {
        margin-top: auto;
        flex-shrink: 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI Core (הפונקציות המקוריות שלך - ללא שינוי) ---
def get_ai_client():
    if not API_KEY:
        st.error("Missing API Key!")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_response(prompt, is_json=False):
    client = get_ai_client()
    if not client: return None
    model_id = "gemini-2.5-flash"  # המודל המקורי שלך
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
    prompt = f"""
    Create a study plan for {subject}: {topic}. {f'Context: {context[:5000]}' if context else ''}
    Return exactly 5 tasks (1 Hard, 2 Medium, 2 Easy).
    Each task MUST have a brief "solution".
    Return ONLY JSON:
    {{ "tasks": [
        {{"text": "Task...", "difficulty": "Hard", "xp": 300, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "..."}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task_json(subject, topic, diff):
    prompt = f"Create one new {diff} study task for {subject}: {topic}. Include a brief solution. Return ONLY JSON: {{'text': '...', 'solution': '...'}}"
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else {"text": "Review materials", "solution": "No solution available."}

# --- 4. Logic & State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "user_name" not in st.session_state: st.session_state.user_name = "Player 1"

BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "Time to study!"),
    (300, "🧠 Brain Builder", "Foundation set."),
    (800, "🔥 Brain Heater", "Getting warm!"),
    (1500, "⚡ High Voltage", "Sparking intelligence!"),
    (2500, "🌌 GALAXY BRAIN", "Universal Wisdom.")
]

ACHIEVEMENTS = [
    {"id": "first", "name": "The Initiate", "emoji": "🥉", "req": 100, "desc": "100 XP Earned"},
    {"id": "pro", "name": "Scholar", "emoji": "🥈", "req": 10, "type": "tasks", "desc": "10 Quests Done"},
    {"id": "master", "name": "Sage", "emoji": "🥇", "req": 1500, "desc": "1,500 XP Earned"},
    {"id": "god", "name": "Galaxy Brain", "emoji": "🌌", "req": 5000, "desc": "5,000 XP Earned"}
]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    next_limit = BRAIN_LEVELS[1][0]
    for i, level in enumerate(BRAIN_LEVELS):
        if xp >= level[0]:
            current = level
            next_limit = BRAIN_LEVELS[i+1][0] if i+1 < len(BRAIN_LEVELS) else xp * 1.5
    return current, next_limit

# --- 5. UI Renderers ---
def render_profile():
    st.title("👤 Brain Profile")
    
    with st.expander("📝 Edit Profile"):
        new_name = st.text_input("Username", st.session_state.user_name)
        if st.button("Save Changes"):
            st.session_state.user_name = new_name
            st.rerun()

    (lvl_xp, lvl_title, lvl_desc), next_limit = get_brain_status(st.session_state.xp)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        emoji = lvl_title.split()[0]
        st.markdown(f"""
            <div class="white-card">
                <div class="brain-avatar">{emoji}</div>
                <h2>{st.session_state.user_name}</h2>
                <h4 style="color: #7F00FF;">{lvl_title}</h4>
                <p>{lvl_desc}</p>
                <div style="background:#eee; padding:5px; border-radius:10px;">Level {int(st.session_state.xp / 500) + 1}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="white-card">
                <h3>📊 Statistics</h3>
                <div class="scrollable-content">
                    <div class="stat-box"><strong>Total XP:</strong> {st.session_state.xp}</div>
                    <div class="stat-box"><strong>Tasks Done:</strong> {st.session_state.tasks_completed}</div>
                    <div class="stat-box"><strong>Day Streak:</strong> 🔥 3 Days</div>
                    <div class="stat-box"><strong>Global Rank:</strong> #1,240</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="white-card"><h3>👥 Study Buddies</h3><div class="scrollable-content">', unsafe_allow_html=True)
        friends = [
            ("Sarah_Brains", "online", "Physics"),
            ("Mike_The_Wiz", "online", "Algebra"),
            ("Lazy_Dave", "offline", "Last seen 2d ago")
        ]
        for name, status, activity in friends:
            dot_class = "online" if status == "online" else "offline"
            st.markdown(f"""
                <div class="friend-row">
                    <div>
                        <strong>{name}</strong><br><small>{activity}</small>
                    </div>
                    <span class="status-dot {dot_class}"></span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.button("➕ Add Friend", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    
    # Achievements Section
    st.subheader("🏆 Achievements")
    badge_cols = st.columns(len(ACHIEVEMENTS))
    for i, ach in enumerate(ACHIEVEMENTS):
        is_locked = True
        if ach.get("type") == "tasks":
            if st.session_state.tasks_completed >= ach["req"]: 
                is_locked = False
        else:
            if st.session_state.xp >= ach["req"]: 
                is_locked = False
        
        with badge_cols[i]:
            status = "locked" if is_locked else ""
            st.markdown(f"""
                <div class="badge-card {status}">
                    <div class="badge-icon">{ach["emoji"]}</div>
                    <strong>{ach["name"]}</strong><br>
                    <small>{ach["desc"]}</small>
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    
    # Focus Mode Timer
    st.subheader("⏲️ Focus Mode")
    with st.expander("Start Deep Work Session"):
        focus_mins = st.slider("Select Duration (Minutes)", 5, 120, 25)
        c1, c2 = st.columns(2)
        if c1.button("🚀 Start Timer", use_container_width=True, type="primary"):
            p = st.empty()
            stop_button_placeholder = c2.empty()
            for s in range(focus_mins * 60, 0, -1):
                if stop_button_placeholder.button("🛑 Stop & Reset", key=f"stop_{s}", use_container_width=True):
                    st.rerun()
                m, sc = divmod(s, 60)
                p.metric("Time Remaining", f"{m:02d}:{sc:02d}")
                time.sleep(1)
            st.balloons()
            st.session_state.xp += 50
            st.rerun()
    
    st.divider()
    st.subheader("📈 Learning Progress")
    chart_data = pd.DataFrame({
        'Week': ['W1', 'W2', 'W3', 'W4'], 
        'XP': [400, 700, 500, st.session_state.xp]
    })
    st.line_chart(chart_data, x='Week', y='XP', color="#7F00FF")

def render_arcade():
    # Intro Banner
    st.markdown("""
        <div class="intro-banner">
            <h2>Welcome to BrainWash Arcade 🎮</h2>
            <p>Turn study materials into active quests. Earn XP, unlock ranks, and master subjects!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Progress Bar Header
    (lvl_xp, lvl_title, _), next_limit = get_brain_status(st.session_state.xp)
    prog = min((st.session_state.xp - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.write(f"**Rank:** {lvl_title} ({st.session_state.xp} XP)")
    st.progress(prog)

    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Subject Search", "📄 PDF Scan"])
        with t1:
            with st.form("manual"):
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Matrices")
                if st.form_submit_button("Start Mission"):
                    plan = get_initial_plan(sub, top)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("pdf"):
                sub_p = st.text_input("Subject")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play"):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan(sub_p, f.name, txt)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub_p, "top": f.name, "pdf_text": txt}
                            st.rerun()
    else:
        st.caption(f"Mission: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            xp = task['xp']
            st.markdown(f"""
                <div class="task-card diff-{d}">
                    <span class="badge bg-{d}">{d} | +{xp} XP</span>
                    <div style="margin-top:10px;">{html.escape(task['text'])}</div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Done", key=f"d{i}", use_container_width=True, type="primary"):
                    st.session_state.xp += xp
                    st.session_state.tasks_completed += 1
                    with st.spinner("New task..."):
                        new = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                        st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                    st.rerun()
            with c2:
                if st.button("🎲 Reroll (-20)", key=f"r{i}", use_container_width=True):
                    if st.session_state.xp >= 20:
                        st.session_state.xp -= 20
                        with st.spinner("Rerolling..."):
                            new = get_new_task_json(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                            st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                        st.rerun()
            
            with st.expander("💡 Show Solution"):
                st.write(task.get('solution', 'No solution found.'))
        
        if st.button("🏳️ Reset Session"):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Sidebar with Progress ---
with st.sidebar:
    st.title("🧠 BrainWash")
    st.write(f"Hello, **{st.session_state.user_name}**!")
    
    # הצגת התקדמות ב-Sidebar
    (lvl_xp, lvl_title, _), next_limit = get_brain_status(st.session_state.xp)
    st.write(f"Rank: **{lvl_title}**")
    prog = min((st.session_state.xp - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.progress(prog)
    
    st.divider()
    page = st.radio("Menu", ["Arcade", "Profile"])

# --- 7. Router ---
if page == "Arcade": 
    render_arcade()
else: 
    render_profile()

