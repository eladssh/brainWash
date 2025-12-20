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
API_KEY = os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS Styles ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
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

    .badge {
        padding: 4px 8px;
        border-radius: 8px;
        color: white; 
        font-weight: bold;
        font-size: 0.75em;
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
        height: 100%;
    }
    .brain-avatar { font-size: 70px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Core Logic (Fixed to Gemini 1.5 Flash) ---

def get_gemini_model():
    """Directly using gemini-1.5-flash for stability."""
    if not API_KEY:
        return None
    try:
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except:
        return None

def get_initial_plan(subject, topic, context_text=None):
    model = get_gemini_model()
    if not model: return None
    
    # context_text helps the AI tailor tasks to the PDF content
    source_info = f"Based on this content: {context_text[:10000]}" if context_text else f"Topic: {topic}"
    
    prompt = f"""
    You are a gamification expert. Create a study plan for {subject}: {topic}.
    {source_info}
    Create 5 micro-tasks sorted by difficulty (1 Hard, 2 Medium, 2 Easy).
    Return ONLY a JSON object:
    {{
        "tasks": [
            {{"text": "Short task description", "difficulty": "Hard", "xp": 300}},
            ...
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
    prompt = f"Create one {difficulty} study task for {subject} on the topic {topic}. Return only the task text."
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return "Review the main concepts again."

# --- 4. Gamification Data ---

BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "You are losing neurons!"),
    (300, "🧠 Brain Builder", "Building momentum..."),
    (800, "🔥 Brain Heater", "You're getting warm!"),
    (1500, "⚡ High Voltage", "You're on fire!"),
    (2500, "🌌 GALAXY BRAIN", "Academic God Mode.")
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
    st.toast(f"✅ Completed! +{task['xp']} XP")
    
    # Replace with new task
    details = st.session_state.user_details
    new_text = get_new_task(details['sub'], details['top'], task['difficulty'], details.get('pdf_text'))
    st.session_state.current_tasks[index]['text'] = new_text

def handle_reroll(index):
    if st.session_state.xp < 20:
        st.error("Not enough XP!")
        return
    st.session_state.xp -= 20
    task = st.session_state.current_tasks[index]
    details = st.session_state.user_details
    new_text = get_new_task(details['sub'], details['top'], task['difficulty'], details.get('pdf_text'))
    st.session_state.current_tasks[index]['text'] = new_text
    st.toast("🎲 Task Rerolled! (-20 XP)")

# --- 7. UI Components ---

def render_profile():
    st.header("👤 Your Brain Profile")
    (xp_req, title, desc), next_xp = get_brain_status(st.session_state.xp)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class="profile-card">
            <div class="brain-avatar">{title.split()[0]}</div>
            <h2>{title}</h2>
            <p>{desc}</p>
            <hr>
            <h4>Current XP: {st.session_state.xp}</h4>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Stats & Activity")
        st.metric("Tasks Finished", st.session_state.tasks_completed)
        
        # Simple progress to next level
        progress = (st.session_state.xp - xp_req) / (next_xp - xp_req)
        st.write(f"Progress to next level:")
        st.progress(min(max(progress, 0.0), 1.0))
        st.caption(f"{st.session_state.xp} / {next_xp} XP")

def render_arcade():
    st.header("🎮 Study Arcade")

    if not st.session_state.user_details:
        # LOBBY: Choice between Search and Upload
        tab1, tab2 = st.tabs(["🔍 Quick Search", "📄 Upload PDF"])
        
        with tab1:
            with st.form("quick_start"):
                sub = st.text_input("Subject", placeholder="e.g. Biology")
                top = st.text_input("Topic", placeholder="e.g. Photosynthesis")
                if st.form_submit_button("Generate Mission", use_container_width=True):
                    with st.spinner("Generating..."):
                        data = get_initial_plan(sub, top)
                        if data:
                            st.session_state.current_tasks = data['tasks']
                            st.session_state.user_details = {"sub": sub, "top": top}
                            st.rerun()

        with tab2:
            with st.form("pdf_start"):
                sub_pdf = st.text_input("Subject", placeholder="e.g. History")
                uploaded_file = st.file_uploader("Drop your summary/book here", type="pdf")
                if st.form_submit_button("Analyze & Play", use_container_width=True):
                    if uploaded_file:
                        with st.spinner("Reading PDF..."):
                            text = extract_text_from_pdf(uploaded_file)
                            data = get_initial_plan(sub_pdf, uploaded_file.name, text)
                            if data:
                                st.session_state.current_tasks = data['tasks']
                                st.session_state.user_details = {"sub": sub_pdf, "top": uploaded_file.name, "pdf_text": text}
                                st.rerun()
    else:
        # GAMEPLAY
        st.info(f"Currently Studying: **{st.session_state.user_details['top']}**")
        
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f"""
            <div class="task-card diff-{d}">
                <span class="badge bg-{d}">{d} | +{task['xp']} XP</span>
                <p style="margin-top:10px; font-weight:500;">{html.escape(task['text'])}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.button("✅ Complete", key=f"c_{i}", on_click=handle_complete, args=(i,), use_container_width=True)
            c2.button("🎲 Reroll (-20)", key=f"r_{i}", on_click=handle_reroll, args=(i,), use_container_width=True)

        if st.button("🏳️ Finish Session", use_container_width=True):
            st.session_state.user_details = {}
            st.session_state.current_tasks = []
            st.rerun()

# --- 8. Main Router ---
if not API_KEY:
    st.warning("Please add GOOGLE_API_KEY to your .env file")
else:
    with st.sidebar:
        st.title("🧠 BrainWash")
        choice = st.radio("Navigation", ["Arcade Mode", "My Profile"])
        st.divider()
        st.write(f"**XP:** {st.session_state.xp}")
        st.write(f"**Tasks:** {st.session_state.tasks_completed}")

    if choice == "Arcade Mode":
        render_arcade()
    else:
        render_profile()
