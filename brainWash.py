import streamlit as st
from google import genai
import json
import os
import pypdf
import html
import pandas as pd
from dotenv import load_dotenv

# --- 1. Init & Config ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

st.set_page_config(page_title="BrainWash", page_icon="🧠", layout="wide")

# --- 2. CSS ---
st.markdown("""
    <style>
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
    </style>
""", unsafe_allow_html=True)

# --- 3. Robust AI Logic ---

def get_ai_response(prompt, is_json=False):
    """מנסה שמות שונים של מודלים כדי לעקוף את שגיאת ה-404"""
    if not API_KEY:
        st.error("Missing API Key")
        return None
    
    client = genai.Client(api_key=API_KEY)
    
    # רשימת שמות אפשריים למודל - אחד מהם חייב לעבוד
    model_variants = ['gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-1.5-flash-latest']
    
    config = {'response_mime_type': 'application/json'} if is_json else None

    for model_name in model_variants:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception:
            continue # מנסה את השם הבא ברשימה
            
    st.error("כל המודלים נכשלו. וודא שה-API Key תקין ופעיל.")
    return None

def get_initial_plan(subject, topic, context=""):
    prompt = f"""
    Create a 5-task study plan for {subject}: {topic}. {f'Context: {context[:5000]}' if context else ''}
    Return ONLY JSON:
    {{ "tasks": [
        {{"text": "Description", "difficulty": "Hard", "xp": 300}},
        {{"text": "Description", "difficulty": "Medium", "xp": 150}},
        {{"text": "Description", "difficulty": "Medium", "xp": 150}},
        {{"text": "Description", "difficulty": "Easy", "xp": 50}},
        {{"text": "Description", "difficulty": "Easy", "xp": 50}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task(subject, topic, diff):
    prompt = f"Create one {diff} study task for {subject}: {topic}. Return only the text."
    return get_ai_response(prompt) or "Stay focused and keep studying!"

# --- 4. Gamification ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "tasks_completed" not in st.session_state: st.session_state.tasks_completed = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

def get_rank(xp):
    if xp < 300: return "🧟 Brain Rot", "Need more neurons..."
    if xp < 800: return "🧠 Brain Builder", "Getting stronger!"
    if xp < 1500: return "⚡ High Voltage", "You are on fire!"
    return "🌌 GALAXY BRAIN", "Master of the universe."

# --- 5. UI Sections ---

def render_profile():
    st.title("👤 Brain Profile")
    rank, desc = get_rank(st.session_state.xp)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total XP", st.session_state.xp)
        st.write(f"**Rank:** {rank}")
        st.caption(desc)
    with c2:
        st.metric("Tasks Completed", st.session_state.tasks_completed)
    
    # XP Graph
    st.subheader("Progress History")
    chart_data = pd.DataFrame({"Day": ["Mon", "Tue", "Wed", "Today"], "XP": [0, 50, 150, st.session_state.xp]})
    st.line_chart(chart_data, x="Day", y="XP")

def render_arcade():
    st.title("🎮 Arcade Mode")
    
    if not st.session_state.user_details:
        tab1, tab2 = st.tabs(["🔍 Search", "📄 PDF Upload"])
        
        with tab1:
            with st.form("search_form"):
                sub = st.text_input("Subject")
                top = st.text_input("Topic")
                if st.form_submit_button("Start Mission"):
                    with st.spinner("Generating..."):
                        plan = get_initial_plan(sub, top)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub, "top": top}
                            st.rerun()
        with tab2:
            with st.form("pdf_form"):
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
                                st.session_state.user_details = {"sub": sub_pdf, "top": file.name, "ctx": txt}
                                st.rerun()
    else:
        # Gameplay
        st.info(f"Mission: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            st.markdown(f'<div class="task-card diff-{d}"><span class="badge bg-{d}">{d} | +{task["xp"]}</span><br>{html.escape(task["text"])}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅ Complete", key=f"done_{i}"):
                st.session_state.xp += task['xp']
                st.session_state.tasks_completed += 1
                st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                st.rerun()
            if c2.button("🎲 Reroll (-20)", key=f"roll_{i}"):
                if st.session_state.xp >= 20:
                    st.session_state.xp -= 20
                    st.session_state.current_tasks[i]['text'] = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], d)
                    st.rerun()
        
        if st.button("🏳️ Reset Mission"):
            st.session_state.user_details = {}
            st.rerun()

# --- 6. Router ---
with st.sidebar:
    st.title("🧠 BrainWash")
    page = st.radio("Navigate", ["Arcade", "Profile"])
    st.divider()
    st.write(f"XP: {st.session_state.xp}")

if page == "Arcade": render_arcade()
else: render_profile()
