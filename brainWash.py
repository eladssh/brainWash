import streamlit as st
from google import genai
from google.genai import types
import json
import os
import pypdf
import html
import pandas as pd
import time
from dotenv import load_dotenv

# --- 1. Init & Config ---
load_dotenv()
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide"
)

# --- 2. CSS Styles (תיקון סופי לאחידות וגלישה) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    /* קוביות לבנות אחידות לפרופיל */
    .white-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6; 
        margin-bottom: 20px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        height: 380px; /* גובה קשיח לאחידות */
    }
    
    .scrollable-content {
        overflow-y: auto;
        flex-grow: 1;
        padding-right: 5px;
    }

    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 15px;
    }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 

    .badge-card { 
        background: white; padding: 15px; border-radius: 15px;
        border: 1px solid #eef2f6; text-align: center; height: 180px;
    }
    .badge-icon { font-size: 40px; }
    .locked { filter: grayscale(100%); opacity: 0.3; }

    .brain-avatar { 
        font-size: 70px; display: block; margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    .friend-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 0; border-bottom: 1px solid #f8f9fa;
        font-size: 0.95em;
        word-break: break-word;
    }
    .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; margin-left: 10px;}
    .online { background-color: #66bb6a; }
    .offline { background-color: #bdbdbd; }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI Core ---
def get_ai_client():
    if not API_KEY:
        st.error("Missing API Key!")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_response(prompt, is_json=False):
    client = get_ai_client()
    if not client: return None
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json" if is_json else "text/plain"
    )
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=config)
        return response.text.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_initial_plan(subject, topic, context=""):
    # פרומפט שמדגיש את המפתח "text"
    prompt = f"""
    Create a study plan for {subject}: {topic}. {f'Context: {context[:5000]}' if context else ''}
    Return 5 tasks (1 Hard, 2 Medium, 2 Easy).
    Return ONLY JSON in this format:
    {{ "tasks": [
        {{"text": "detailed task description", "difficulty": "Hard", "xp": 300, "solution": "brief solution"}},
        ...
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    try:
        return json.loads(res)
    except:
        return None

def get_new_task_json(subject, topic, diff):
    prompt = f"Create one {diff} study task for {subject}: {topic}. Return JSON: {{'text': '...', 'solution': '...'}}"
    res = get_ai_response(prompt, is_json=True)
    try:
        return json.loads(res)
    except:
        return {"text": "Review your notes.", "solution": "Look at the material again."}

# --- 4. Logic & State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "user_name" not in st.session_state: st.session_state.user_name = "Player 1"

ACHIEVEMENTS = [
    {"id": "first", "name": "The Initiate", "emoji": "🥉", "req": 100, "desc": "100 XP Earned"},
    {"id": "pro", "name": "Scholar", "emoji": "🥈", "req": 10, "type": "tasks", "desc": "10 Quests Done"},
    {"id": "master", "name": "Sage", "emoji": "🥇", "req": 1500, "desc": "1,500 XP Earned"}
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
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f'<div class="white-card"><div class="brain-avatar">🧠</div><h2>{st.session_state.user_name}</h2><h4 style="color:#7F00FF;">{lvl_title}</h4><p>Level {int(st.session_state.xp / 500) + 1}</p></div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div class="white-card"><h3>📊 Statistics</h3><div style="text-align:left; margin-top:30px;"><p><strong>Total XP:</strong> {st.session_state.xp}</p><p><strong>Quests:</strong> {st.session_state.tasks_completed}</p><p><strong>Streak:</strong> 🔥 3 Days</p></div></div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="white-card"><h3>👥 Buddies</h3><div class="scrollable-content">', unsafe_allow_html=True)
        friends = [("Sarah_Brains", "online"), ("Mike_The_Wiz", "online"), ("Lazy_Dave", "offline")]
        for name, status in friends:
            dot = "online" if status == "online" else "offline"
            st.markdown(f'<div class="friend-row"><span>{name}</span><span class="status-dot {dot}"></span></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.button("➕ Add Buddy", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("⏲️ Focus Mode")
    with st.expander("Launch Deep Work Timer"):
        mins = st.slider("Minutes", 5, 120, 25)
        c1, c2 = st.columns(2)
        if c1.button("🚀 Start", use_container_width=True, type="primary"):
            p = st.empty()
            stop = c2.button("🛑 Stop", use_container_width=True)
            for s in range(mins * 60, 0, -1):
                if stop: st.rerun()
                m, sc = divmod(s, 60)
                p.metric("Time", f"{m:02d}:{sc:02d}")
                time.sleep(1)
            st.balloons()
            st.session_state.xp += 50
            st.rerun()

def render_arcade():
    st.title("🎮 Arcade Mode")
    (lvl_xp, lvl_title), nxt = get_brain_status(st.session_state.xp)
    st.progress(min((st.session_state.xp - lvl_xp) / (nxt - lvl_xp), 1.0))
    st.write(f"Rank: **{lvl_title}**")

    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Search", "📄 PDF"])
        with t1:
            with st.form("f1"):
                sub, top = st.text_input("Subject"), st.text_input("Topic")
                if st.form_submit_button("Start"):
                    plan = get_initial_plan(sub, top)
                    if plan and 'tasks' in plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("f2"):
                f = st.file_uploader("PDF", type="pdf")
                if st.form_submit_button("Analyze"):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan("PDF", f.name, txt)
                        if plan and 'tasks' in plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": "PDF", "top": f.name}
                            st.rerun()
    else:
        for i, task in enumerate(st.session_state.current_tasks):
            # טיפול ב-no task text: בדיקה של כמה מפתחות אפשריים
            t_text = task.get('text') or task.get('Description') or task.get('task') or "Learn more about this topic."
            d, xp = task.get('difficulty', 'Medium'), task.get('xp', 50)
            
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{xp} XP</span><br>{html.escape(t_text)}</div>', unsafe_allow_html=True)
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
            with st.expander("💡 Solution"):
                st.write(task.get('solution', 'Check your notes!'))

        if st.button("🏳️ Reset"):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Router ---
with st.sidebar:
    st.title("🧠 BrainWash")
    st.write(f"User: **{st.session_state.user_name}**")
    (lx, lt), nxt = get_brain_status(st.session_state.xp)
    st.progress(min((st.session_state.xp - lx) / (nxt - lx), 1.0))
    st.write(f"Rank: {lt}")
    page = st.radio("Menu", ["Arcade", "Profile"])

if page == "Arcade": render_arcade()
else: render_profile()
