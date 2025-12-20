import streamlit as st
import google.generativeai as genai
import json
import os
import pypdf
import html
import pandas as pd
from dotenv import load_dotenv

# --- 1. Init & Config ---
load_dotenv()
# בענן זה יימשך מה-Secrets, בלוקאל מקובץ ה-.env
API_KEY = os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# הגדרת ה-AI (גרסה ישנה ויציבה)
if API_KEY:
    genai.configure(api_key=API_KEY)

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
    .profile-card { background: white; padding: 25px; border-radius: 20px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .brain-avatar { font-size: 70px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Core AI Logic (Legacy Syntax) ---

def get_ai_response(prompt, is_json=False):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if is_json:
            response = model.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_initial_plan(subject, topic, context_text=None):
    source_info = f"Context from PDF: {context_text[:8000]}" if context_text else f"Topic: {topic}"
    prompt = f"""
    Create a gamified study plan for {subject}: {topic}. {source_info}
    Return 5 tasks (1 Hard, 2 Medium, 2 Easy).
    Return ONLY STRICT JSON:
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
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task(subject, topic, difficulty):
    prompt = f"Create one {difficulty} study task for {subject}: {topic}. Return only the task text."
    return get_ai_response(prompt) or "Review your materials."

# --- 4. Gamification Logic ---

BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "Time to build some neurons!"),
    (300, "🧠 Brain Builder", "You're getting the hang of it."),
    (800, "🔥 Brain Heater", "Things are getting serious!"),
    (1500, "⚡ High Voltage", "Pure academic energy!"),
    (2500, "🌌 GALAXY BRAIN", "You've reached peak intelligence.")
]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    next_limit = BRAIN_LEVELS[1][0]
    for i, level in enumerate(BRAIN_LEVELS):
        if xp >= level[0]:
            current = level
            next_limit = BRAIN_LEVELS[i+1][0] if i+1 < len(BRAIN_LEVELS) else xp + 500
    return current, next_limit

# --- 5. State Management ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# --- 6. Handlers ---
def handle_complete(index):
    task = st.session_state.current_tasks[index]
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1
    if task['difficulty'] == "Hard": st.balloons()
    st.toast(f"✅ +{task['xp']} XP!")
    
    # Reroll the finished task
    details = st.session_state.user_details
    new_text = get_new_task(details['sub'], details['top'], task['difficulty'])
    st.session_state.current_tasks[index]['text'] = new_text

def handle_reroll(index):
    if st.session_state.xp < 20:
        st.error("Not enough XP!")
        return
    st.session_state.xp -= 20
    task = st.session_state.current_tasks[index]
    details = st.session_state.user_details
    new_text = get_new_task(details['sub'], details['top'], task['difficulty'])
    st.session_state.current_tasks[index]['text'] = new_text
    st.toast("🎲 Rerolled! (-20 XP)")

# --- 7. UI Sections ---

def render_profile():
    st.title("👤 Brain Profile")
    (xp_req, title, desc), next_xp = get_brain_status(st.session_state.xp)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class="profile-card">
            <div class="brain-avatar">{title.split()[0]}</div>
            <h2>{title}</h2>
            <p>{desc}</p>
            <hr>
            <h4>XP: {st.session_state.xp}</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Your Stats")
        st.metric("Quests Finished", st.session_state.tasks_completed)
        prog = (st.session_state.xp - xp_req) / (next_xp - xp_req)
        st.write(f"Level Progress:")
        st.progress(min(max(prog, 0.0), 1.0))
        st.caption(f"{st.session_state.xp} / {next_xp} XP to next rank")

def render_arcade():
    st.title("🎮 Arcade Mode")

    if not st.session_state.user_details:
        tab1, tab2 = st.tabs(["🔍 Quick Search", "📄 PDF Mission"])
        
        with tab1:
            with st.form("search"):
                sub = st.text_input("Subject", placeholder="Biology...")
                top = st.text_input("Topic", placeholder="Evolution...")
                if st.form_submit_button("Start Mission"):
                    with st.spinner("Generating..."):
                        plan = get_initial_plan(sub, top)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub, "top": top}
                            st.rerun()
        
        with tab2:
            with st.form("pdf"):
                sub_pdf = st.text_input("Subject")
                file = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze PDF"):
                    if file:
                        with st.spinner("Reading PDF..."):
                            reader = pypdf.PdfReader(file)
                            txt = "".join([p.extract_text() for p in reader.pages])
                            plan = get_initial_plan(sub_pdf, file.name, txt)
                            if plan:
                                st.session_state.current_tasks = plan['tasks']
                                st.session_state.user_details = {"sub": sub_pdf, "top": file.name}
                                st.rerun()
    else:
        st.info(f"Mission: **{st.session_state.user_details['top']}**")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f"""
            <div class="task-card diff-{d}">
                <span class="badge bg-{d}">{d} | +{task['xp']} XP</span>
                <p style="margin-top:10px;">{html.escape(task['text'])}</p>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.button("✅ Done", key=f"c{i}", on_click=handle_complete, args=(i,), use_container_width=True)
            c2.button("🎲 Reroll (-20)", key=f"r{i}", on_click=handle_reroll, args=(i,), use_container_width=True)
        
        st.divider()
        if st.button("🏳️ Reset Mission", use_container_width=True):
            st.session_state.user_details = {}
            st.session_state.current_tasks = []
            st.rerun()

# --- 8. Main Router ---
with st.sidebar:
    st.title("🧠 BrainWash")
    choice = st.radio("Navigation", ["Arcade Mode", "My Profile"])
    st.divider()
    st.write(f"XP: {st.session_state.xp}")

if not API_KEY:
    st.warning("API Key missing! Please set GOOGLE_API_KEY in Secrets or .env")
else:
    if choice == "Arcade Mode":
        render_arcade()
    else:
        render_profile()
