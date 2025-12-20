import streamlit as st
from google import genai
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
    # הגדרה של הספרייה היציבה
    client = genai.Client(api_key=API_KEY)
else:
    st.error("Missing API Key! Please configure it in Secrets.")
    st.stop()

st.set_page_config(page_title="BrainWash: Arcade", page_icon="🧠", layout="wide")

# --- 2. CSS Styles (משוחזר במלואו) ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .task-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 10px solid #ddd;
        margin-bottom: 15px; transition: transform 0.2s;
    }
    .task-card:hover { transform: scale(1.01); }
    .diff-Hard { border-left-color: #ff4b4b; } 
    .diff-Medium { border-left-color: #ffa726; } 
    .diff-Easy { border-left-color: #66bb6a; } 
    .badge {
        padding: 4px 8px; border-radius: 8px; color: white; 
        font-weight: bold; font-size: 0.8em; text-transform: uppercase;
    }
    .bg-Hard { background-color: #ff4b4b; }
    .bg-Medium { background-color: #ffa726; }
    .bg-Easy { background-color: #66bb6a; }
    .profile-card {
        background: white; padding: 25px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center;
    }
    .brain-avatar { 
        font-size: 80px; display: block; margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-10px); } }
    </style>
""", unsafe_allow_html=True)

# --- 3. Logic & Helpers ---

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except: return None

def get_initial_plan(subject, topic, context_text=None):
    try:
        source = f"PDF Content: {context_text[:10000]}" if context_text else f"Topic: {topic}"

        prompt = f"""
        Gamify a study plan for {subject}: {topic}.
        Create 5 study micro-tasks sorted by difficulty (1 Hard, 2 Medium, 2 Easy).
        Source: {source}
        Return ONLY a JSON object:
        {{
            "tasks": [
                {{"text": "Task description", "difficulty": "Hard", "xp": 300}},
                {{"text": "Task description", "difficulty": "Medium", "xp": 150}},
                {{"text": "Task description", "difficulty": "Medium", "xp": 150}},
                {{"text": "Task description", "difficulty": "Easy", "xp": 50}},
                {{"text": "Task description", "difficulty": "Easy", "xp": 50}}
            ]
        }}
        """

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )

        return json.loads(response.text)

    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_new_task(subject, topic, difficulty, context_text=None):
    try:
        prompt = f"Create 1 new {difficulty} study task for {topic} in {subject}. Return ONLY the task text."

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        return response.text.strip()
    except:
        return "Complete a quick review of the main topic."


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
            next_limit = BRAIN_LEVELS[i+1][0] if i+1 < len(BRAIN_LEVELS) else xp * 1.5
    return current, next_limit

# --- 5. Event Handlers ---
def handle_complete(index):
    task = st.session_state.current_tasks[index]
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1
    
    with st.spinner("Generating next task..."):
        new_text = get_new_task(
            st.session_state.user_details['sub'], 
            st.session_state.user_details['top'], 
            task['difficulty'], 
            st.session_state.user_details.get('pdf_text')
        )
        st.session_state.current_tasks[index] = {"text": new_text, "difficulty": task['difficulty'], "xp": task['xp']}
    
    if task['difficulty'] == "Hard": st.balloons()
    st.toast(f"✅ +{task['xp']} XP!")

def handle_reroll(index):
    if st.session_state.xp < 20:
        st.toast("🚫 Need 20 XP")
        return
    st.session_state.xp -= 20
    task = st.session_state.current_tasks[index]
    with st.spinner("Rerolling..."):
        new_text = get_new_task(
            st.session_state.user_details['sub'], 
            st.session_state.user_details['top'], 
            task['difficulty'], 
            st.session_state.user_details.get('pdf_text')
        )
        st.session_state.current_tasks[index]['text'] = new_text
    st.toast("🎲 Rerolled! -20 XP")

# --- 6. Session State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# --- 7. Page Renderers ---
def render_profile():
    st.title("👤 Brain Profile")
    (lvl_xp, lvl_title, lvl_desc), next_xp = get_brain_status(st.session_state.xp)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="profile-card"><div class="brain-avatar">{lvl_title.split()[0]}</div>
        <h3>{lvl_title}</h3><p>{lvl_desc}</p></div>""", unsafe_allow_html=True)
    with c2:
        st.metric("Total XP", st.session_state.xp)
    with c3:
        prog = (st.session_state.xp - lvl_xp) / (next_xp - lvl_xp) if next_xp > lvl_xp else 1.0
        st.progress(min(max(prog, 0.0), 1.0))

def render_arcade():
    st.title("🎮 Arcade Mode")
    if not st.session_state.user_details:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("manual"):
                st.subheader("Manual Mission")
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Matrices")
                if st.form_submit_button("Start Game"):
                    with st.spinner("Generating..."):
                        data = get_initial_plan(sub, top)
                        if data:
                            st.session_state.current_tasks = data['tasks']
                            st.session_state.user_details = {"sub": sub, "top": top}
                            st.rerun()
        with col2:
            with st.form("pdf_form"):
                st.subheader("PDF Mission")
                pdf_sub = st.text_input("Subject", "History")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play"):
                    if f:
                        with st.spinner("Reading PDF..."):
                            txt = extract_text_from_pdf(f)
                            data = get_initial_plan(pdf_sub, f.name, txt)
                            if data:
                                st.session_state.current_tasks = data['tasks']
                                st.session_state.user_details = {"sub": pdf_sub, "top": f.name, "pdf_text": txt}
                                st.rerun()
    else:
        for i, task in enumerate(st.session_state.current_tasks):
            diff = task['difficulty']
            st.markdown(f"""<div class="task-card diff-{diff}">
                <span class="badge bg-{diff}">{diff} | +{task['xp']} XP</span>
                <p style="margin-top:10px;">{task['text']}</p></div>""", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1: st.button("✅ Complete", key=f"c{i}", on_click=handle_complete, args=(i,), use_container_width=True)
            with b2: st.button("🎲 Reroll", key=f"r{i}", on_click=handle_reroll, args=(i,), use_container_width=True)
        if st.button("🏳️ End Mission"):
            st.session_state.user_details = {}
            st.session_state.current_tasks = []
            st.rerun()

# --- 8. Router ---
with st.sidebar:
    st.title("BrainWash")
    page = st.radio("Menu", ["🎮 Arcade Mode", "👤 Profile"])
    st.divider()
    st.write(f"**XP:** {st.session_state.xp}")

if page == "🎮 Arcade Mode": render_arcade()
else: render_profile()

