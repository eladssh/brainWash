import streamlit as st
import google as genai
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

# הגדרת ה-AI
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
    </style>
""", unsafe_allow_html=True)

# --- 3. Robust AI Logic (Bulletproof Version) ---

def get_ai_response(prompt, is_json=False):
    """מנסה שמות שונים של מודלים כדי לעקוף את שגיאת ה-404 בענן"""
    # רשימה של שמות מודלים אפשריים בגרסה הישנה
    model_names = ['gemini-2.5-flash', 'gemini-2.5-flash-latest', 'gemini-2.5-flash-001']
    
    config = {"response_mime_type": "application/json"} if is_json else None

    for m_name in model_names:
        try:
            model = genai.GenerativeModel(m_name)
            if config:
                response = model.generate_content(prompt, generation_config=config)
            else:
                response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # אם הגענו למודל האחרון וגם הוא נכשל
            if m_name == model_names[-1]:
                st.error(f"AI Final Error: {e}")
                return None
            continue # מנסה את המודל הבא ברשימה

def get_initial_plan(subject, topic, context_text=None):
    source = f"Context: {context_text[:5000]}" if context_text else f"Topic: {topic}"
    prompt = f"""
    Create a 5-task study plan for {subject}: {topic}. {source}
    Return ONLY JSON:
    {{ "tasks": [
        {{"text": "Task text", "difficulty": "Hard", "xp": 300}},
        {{"text": "Task text", "difficulty": "Medium", "xp": 150}},
        {{"text": "Task text", "difficulty": "Medium", "xp": 150}},
        {{"text": "Task text", "difficulty": "Easy", "xp": 50}},
        {{"text": "Task text", "difficulty": "Easy", "xp": 50}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    if res:
        try:
            return json.loads(res)
        except:
            return None
    return None

def get_new_task(subject, topic, diff):
    prompt = f"Create one {diff} study task for {subject}: {topic}. Return only the text."
    return get_ai_response(prompt) or "Review your notes!"

# --- 4. Gamification Logic ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

def get_rank(xp):
    if xp < 300: return "🧟 Brain Rot", "Need more neurons!"
    if xp < 800: return "🧠 Brain Builder", "Getting stronger!"
    if xp < 1500: return "⚡ High Voltage", "You're on fire!"
    return "🌌 GALAXY BRAIN", "Academic God Mode."

# --- 5. UI Sections ---

def render_profile():
    st.title("👤 Brain Profile")
    rank, desc = get_rank(st.session_state.xp)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="profile-card"><h1>{rank.split()[0]}</h1><h2>{rank}</h2><p>{desc}</p><h3>XP: {st.session_state.xp}</h3></div>', unsafe_allow_html=True)
    with c2:
        st.metric("Tasks Completed", st.session_state.tasks_completed)
        st.subheader("Progress History")
        chart_data = pd.DataFrame({"Day": ["Mon", "Tue", "Wed", "Today"], "XP": [0, 50, 150, st.session_state.xp]})
        st.line_chart(chart_data, x="Day", y="XP")

def render_arcade():
    st.title("🎮 Arcade Mode")
    if not st.session_state.user_details:
        t1, t2 = st.tabs(["🔍 Quick Search", "📄 PDF Upload"])
        with t1:
            with st.form("search"):
                sub = st.text_input("Subject")
                top = st.text_input("Topic")
                if st.form_submit_button("Start"):
                    with st.spinner("Generating..."):
                        plan = get_initial_plan(sub, top)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub, "top": top}
                            st.rerun()
        with t2:
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
        st.info(f"Current Mission: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{task["xp"]} XP</span><br>{html.escape(task["text"])}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ Done", key=f"d{i}", use_container_width=True):
                st.session_state.xp += task['xp']
                st.session_state.tasks_completed += 1
                st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                st.rerun()
            if c2.button("🎲 Reroll (-20)", key=f"r{i}", use_container_width=True):
                if st.session_state.xp >= 20:
                    st.session_state.xp -= 20
                    st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                    st.rerun()
        if st.button("🏳️ Reset"):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Main ---
with st.sidebar:
    st.title("🧠 BrainWash")
    choice = st.radio("Menu", ["Arcade", "Profile"])
    st.divider()
    st.write(f"XP: {st.session_state.xp}")

if not API_KEY:
    st.warning("Please set GOOGLE_API_KEY in Streamlit Secrets")
else:
    if choice == "Arcade": render_arcade()
    else: render_profile()

