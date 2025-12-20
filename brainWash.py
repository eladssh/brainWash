import streamlit as st
import google.generativeai as genai
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

if not API_KEY:
    st.error("Missing API Key! Please configure it.")
    st.stop()


st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    /* Global */
    .stApp { background-color: #f0f2f6; }

    /* --- GAME MODE STYLES --- */
    .task-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 10px solid #ddd;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .task-card:hover { transform: scale(1.01); }

    /* Difficulty Colors */
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 

    .badge {
        padding: 4px 8px;
        border-radius: 8px;
        color: white; 
        font-weight: bold;
        font-size: 0.8em;
        text-transform: uppercase;
    }
    .bg-Hard { background-color: #ff4b4b; }
    .bg-Medium { background-color: #ffa726; }
    .bg-Easy { background-color: #66bb6a; }

    /* --- PROFILE STYLES --- */
    .profile-card {
        background: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e0e0e0;
        height: 100%;
    }
    .brain-avatar { 
        font-size: 80px; 
        display: block; 
        margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }

    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }

    /* Friends List */
    .friend-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)


# --- 3. Logic & Helpers ---

def get_gemini_model():
    """Robust model finder."""
    if not API_KEY: return None
    try:
        genai.configure(api_key=API_KEY)
        preferences = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for pref in preferences:
            if pref in available: return genai.GenerativeModel(pref)
        return genai.GenerativeModel(available[0]) if available else None
    except:
        return None


def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except:
        return None


# -- API Calls --
def get_initial_plan(subject, topic, context_text=None):
    model = get_gemini_model()
    if not model: return None
    source = f"PDF Content: {context_text[:20000]}" if context_text else f"Topic: {topic}"

    prompt = f"""
    Gamify a study plan for {subject}: {topic}.
    Create 5 study micro-tasks sorted by difficulty (1 Hard, 2 Medium, 2 Easy).
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
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        return None


def get_new_task(subject, topic, difficulty, context_text=None):
    model = get_gemini_model()
    source = f"PDF: {context_text[:5000]}" if context_text else f"Topic: {topic}"
    prompt = f"Create 1 new {difficulty} study task for {topic}. Return ONLY the task text string."
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return "Review previous notes."


# --- 4. Gamification (Restored Levels) ---

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
    diff = task.get('difficulty', 'Medium')

    # Reward
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1

    if diff == "Hard":
        st.balloons()
        st.toast(f"🔥 LEGENDARY! +{task['xp']} XP")
    else:
        st.toast(f"✅ +{task['xp']} XP")

    # Infinite Mode
    c_sub = st.session_state.user_details.get('sub')
    c_top = st.session_state.user_details.get('top')
    c_text = st.session_state.user_details.get('pdf_text')

    new_text = get_new_task(c_sub, c_top, diff, c_text)

    st.session_state.current_tasks.pop(index)
    st.session_state.current_tasks.append({"text": new_text, "difficulty": diff, "xp": task['xp']})


def handle_reroll(index):
    task = st.session_state.current_tasks[index]
    cost = 20

    if st.session_state.xp < cost:
        st.toast("🚫 Not enough XP to reroll!")
        return

    st.session_state.xp -= cost

    c_sub = st.session_state.user_details.get('sub')
    c_top = st.session_state.user_details.get('top')
    c_text = st.session_state.user_details.get('pdf_text')

    with st.spinner("Rerolling..."):
        new_text = get_new_task(c_sub, c_top, task['difficulty'], c_text)
        st.session_state.current_tasks[index]['text'] = new_text
        st.toast(f"🎲 Rerolled! -{cost} XP")


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

    # Top Section: Avatar & Stats
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        # Avatar Card
        emoji = lvl_title.split()[0]
        st.markdown(f"""
        <div class="profile-card">
            <div class="brain-avatar">{emoji}</div>
            <h3>{lvl_title}</h3>
            <div style="color: #666; margin-bottom:15px;">{lvl_desc}</div>
            <div style="background:#eee; border-radius:10px; padding:5px; font-weight:bold;">
               Level {int(st.session_state.xp / 500) + 1}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        # Stats Grid
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.metric("Total XP", st.session_state.xp)
        st.divider()
        st.metric("Quests Done", st.session_state.tasks_completed)
        st.divider()
        st.metric("Current Streak", "🔥 3 Days")
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        # Friends
        st.markdown('<div class="profile-card" style="text-align:left;">', unsafe_allow_html=True)
        st.subheader("👥 Study Buddies")

        buddies = [
            {"name": "Sarah_Brains", "status": "online", "act": "Calculus"},
            {"name": "Mike_The_Wiz", "status": "online", "act": "History"},
            {"name": "Lazy_Dave", "status": "offline", "act": "2d ago"}
        ]

        for b in buddies:
            dot = "🟢" if b['status'] == 'online' else "⚪"
            st.markdown(f"""
            <div class="friend-row">
                <div>
                    <strong>{b['name']}</strong><br>
                    <span style="font-size:0.8em; color:#666;">{b['act']}</span>
                </div>
                <div style="font-size:0.8em;">{dot}</div>
            </div>
            """, unsafe_allow_html=True)
        st.button("Invite Friend", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Chart
    st.markdown("### 📈 Brain Activity")
    chart_data = pd.DataFrame({
        'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'XP': [150, 200, 450, 300, 0, 500, st.session_state.xp if st.session_state.xp > 0 else 100]
    })
    st.bar_chart(chart_data, x='Day', y='XP', color="#7F00FF")


def render_arcade():
    st.title("🎮 Arcade Mode")

    # 1. Lobby State
    if not st.session_state.user_details:
        st.info("Select a mission to begin.")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("manual"):
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Derivatives")
                if st.form_submit_button("Start Game", use_container_width=True):
                    with st.spinner("Generating Level..."):
                        data = get_initial_plan(sub, top)
                        if data:
                            st.session_state.current_tasks = data.get("tasks", [])
                            st.session_state.user_details = {"sub": sub, "top": top, "pdf_text": None}
                            st.rerun()
        with col2:
            with st.form("pdf"):
                pdf_sub = st.text_input("Subject", "History")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play", use_container_width=True):
                    if f:
                        with st.spinner("Scanning..."):
                            txt = extract_text_from_pdf(f)
                            data = get_initial_plan(pdf_sub, f.name, txt)
                            if data:
                                st.session_state.current_tasks = data.get("tasks", [])
                                st.session_state.user_details = {"sub": pdf_sub, "top": f.name, "pdf_text": txt}
                                st.rerun()

    # 2. Gameplay State
    else:
        # --- Top Bar: Progress & Status ---
        (lvl_xp, lvl_title, lvl_desc), next_xp = get_brain_status(st.session_state.xp)

        c1, c2 = st.columns([0.8, 0.2])
        with c1:
            st.write(f"**Current Rank:** {lvl_title}")
            # Progress Bar Calculation
            if next_xp > 0 and next_xp > lvl_xp:
                prog = (st.session_state.xp - lvl_xp) / (next_xp - lvl_xp)
                st.progress(max(0.0, min(1.0, prog)))
            else:
                st.progress(1.0)
        with c2:
            st.metric("XP", st.session_state.xp)

        st.divider()
        st.caption(f"Mission: {st.session_state.user_details['top']}")

        # --- Task List ---
        for i, task in enumerate(st.session_state.current_tasks):
            diff = task.get('difficulty', 'Easy')
            xp = task.get('xp', 50)
            safe_text = html.escape(task['text'])

            # HTML Card
            st.markdown(f"""
            <div class="task-card diff-{diff}">
                <span class="badge bg-{diff}">{diff} | +{xp} XP</span>
                <div style="font-size: 1.1em; color: #333; margin-top:8px;">{safe_text}</div>
            </div>
            """, unsafe_allow_html=True)

            # Buttons (Complete vs Reroll)
            b1, b2 = st.columns([1, 1])
            with b1:
                st.button("✅ Complete", key=f"done_{i}",
                          on_click=handle_complete, args=(i,),
                          use_container_width=True, type="primary")
            with b2:
                st.button("🎲 Reroll (-20 XP)", key=f"roll_{i}",
                          on_click=handle_reroll, args=(i,),
                          use_container_width=True)

            st.write("")  # Spacer

        st.divider()
        if st.button("🏳️ End Mission (Save XP)", use_container_width=True):
            reset_session(keep_xp=True)
            st.rerun()


# --- 8. Main App Router ---

if not API_KEY:
    st.error("Please configure GOOGLE_API_KEY in .env")
    st.stop()

# Sidebar Navigation
with st.sidebar:
    st.title("BrainWash")
    page = st.radio("Menu", ["🎮 Arcade Mode", "👤 Brain Profile"])

    st.divider()
    # Mini-stat in sidebar
    (_, lvl_title, _), _ = get_brain_status(st.session_state.xp)
    st.write(f"**Rank:** {lvl_title}")
    st.write(f"**XP:** {st.session_state.xp}")

if page == "🎮 Arcade Mode":
    render_arcade()
else:
    render_profile()

