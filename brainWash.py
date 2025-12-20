import streamlit as st
from google import genai  # הספרייה החדשה
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
    layout="wide"
)

# --- 2. CSS Styles (נשאר ללא שינוי) ---
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

# --- 3. Core Logic (Updated to google-genai) ---

def get_client():
    """אתחול הלקוח החדש של גוגל"""
    if not API_KEY:
        return None
    return genai.Client(api_key=API_KEY)

def get_initial_plan(subject, topic, context_text=None):
    client = get_client()
    if not client: return None
    
    source_info = f"Context: {context_text[:10000]}" if context_text else f"Topic: {topic}"
    
    prompt = f"Create a 5-task study plan for {subject}: {topic}. {source_info}. Return JSON with 'tasks' list (text, difficulty, xp)."

    try:
        # שים לב: כאן הורדנו את הקידומת models/ והשתמשנו בשם נקי
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        # אם זה נכשל שוב, ננסה את הגרסה היציבה הספציפית
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash-001', 
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            return json.loads(response.text)
        except:
            st.error(f"AI Final Error: {e}")
            return None

def get_new_task(subject, topic, difficulty, context_text=None):
    client = get_client()
    if not client: return "Review concepts."
    prompt = f"Create one {difficulty} study task for {subject} on {topic}. Return only the text."
    try:
        # שימוש בשם דגם ללא קידומת
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        return response.text.strip()
    except:
        return "Task generation failed. Keep going!"

# --- 4. Gamification Logic (נשאר ללא שינוי) ---
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

# --- 6. Helpers ---
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in pdf_reader.pages])
    except: return None

def handle_complete(index):
    task = st.session_state.current_tasks[index]
    st.session_state.xp += task['xp']
    st.session_state.tasks_completed += 1
    if task['difficulty'] == "Hard": st.balloons()
    st.toast(f"✅ +{task['xp']} XP!")
    
    # Reroll that specific task slot
    details = st.session_state.user_details
    new_text = get_new_task(details['sub'], details['top'], task['difficulty'], details.get('pdf_text'))
    st.session_state.current_tasks[index]['text'] = new_text

# --- 7. UI Sections ---

def render_profile():
    st.header("👤 Your Brain Profile")
    (xp_req, title, desc), next_xp = get_brain_status(st.session_state.xp)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f'<div class="profile-card"><h1>{title.split()[0]}</h1><h2>{title}</h2><p>{desc}</p><h3>XP: {st.session_state.xp}</h3></div>', unsafe_allow_html=True)
    with col2:
        st.metric("Tasks Completed", st.session_state.tasks_completed)
        prog = (st.session_state.xp - xp_req) / (next_xp - xp_req)
        st.write("Progress to next level:")
        st.progress(min(max(prog, 0.0), 1.0))

def render_arcade():
    st.header("🎮 Study Arcade")
    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Quick Search", "📄 PDF Mission"])
        with t1:
            with st.form("f1"):
                sub = st.text_input("Subject")
                top = st.text_input("Topic")
                if st.form_submit_button("Start"):
                    data = get_initial_plan(sub, top)
                    if data:
                        st.session_state.current_tasks = data['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("f2"):
                sub_pdf = st.text_input("Subject")
                file = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze"):
                    if file:
                        txt = extract_text_from_pdf(file)
                        data = get_initial_plan(sub_pdf, file.name, txt)
                        if data:
                            st.session_state.current_tasks = data['tasks']
                            st.session_state.user_details = {"sub": sub_pdf, "top": file.name, "pdf_text": txt}
                            st.rerun()
    else:
        st.info(f"Mission: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{task["xp"]}</span><br>{html.escape(task["text"])}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.button("✅ Done", key=f"c{i}", on_click=handle_complete, args=(i,))
            if c2.button("🎲 Reroll (-20)", key=f"r{i}"):
                if st.session_state.xp >= 20:
                    st.session_state.xp -= 20
                    st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                    st.rerun()

# --- 8. Main ---
with st.sidebar:
    st.title("🧠 BrainWash")
    choice = st.radio("Menu", ["Arcade", "Profile"])
if choice == "Arcade": render_arcade()
else: render_profile()

