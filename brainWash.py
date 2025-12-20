import streamlit as st
import json
import os
import pypdf
import time
from dotenv import load_dotenv
from google import genai

# =========================
# 1. Init & Config
# =========================
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("Missing API Key! Please configure it in Secrets.")
    st.stop()

# אתחול הקליינט
client = genai.Client(api_key=API_KEY)

# רשימת מודלים - שמנו את 1.5 פלאש כראשון כי הוא הכי יציב לענן
MODELS = ["gemini-1.5-flash", "gemini-1.5-flash-8b"]

# =========================
# 2. Robust AI Call
# =========================
def call_ai(prompt, expect_json=False, system_instruction=None):
    """קריאה ל-AI עם טיפול בשגיאות ומנגנון המתנה"""
    last_error = None
    
    # הגדרות פורמט
    config = {}
    if expect_json:
        config["response_mime_type"] = "application/json"
    if system_instruction:
        config["system_instruction"] = system_instruction

    for model_name in MODELS:
        for attempt in range(2): # 2 ניסיונות לכל מודל
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                last_error = e
                # אם זו שגיאת עומס (429), נחכה קצת
                if "429" in str(e):
                    time.sleep(5) 
                    continue
                # שגיאות אחרות - ננסה את המודל הבא
                break 
                
    st.error(f"AI Error: כל המודלים נכשלו. שגיאה אחרונה: {last_error}")
    return None

# =========================
# 3. Helpers & Caching
# =========================
def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        return "".join(page.extract_text() or "" for page in pdf_reader.pages)
    except:
        return None

@st.cache_data(show_spinner="🧠 Generating mission plan...")
def get_initial_plan(subject, topic, context_text=None):
    """יוצר תוכנית - פונקציה זו שמורה ב-Cache כדי לא לבזבז קריאות"""
    source = context_text[:5000] if context_text else topic
    
    sys_msg = "You are a study assistant. Return ONLY a JSON object with 5 tasks: 1 Hard, 2 Medium, 2 Easy."
    prompt = f"Subject: {subject}, Topic: {topic}. Based on this: {source}. Format: {{'tasks': [{{'text': '...', 'difficulty': '...', 'xp': ...}}]}}"
    
    raw = call_ai(prompt, expect_json=True, system_instruction=sys_msg)
    if raw:
        try:
            return json.loads(raw)
        except:
            return None
    return None

def get_new_task(subject, topic, difficulty):
    """יוצר משימה בודדת - ללא Cache כדי לקבל גיוון בכל רול"""
    prompt = f"Create 1 NEW {difficulty} study task for {subject}: {topic}. Return only the text."
    res = call_ai(prompt)
    return res.strip() if res else "Review the core concepts once more."

# =========================
# 4. Streamlit UI & State
# =========================
st.set_page_config(page_title="BrainWash", page_icon="🧠", layout="wide")

# (כאן נכנס ה-CSS שלך כפי שהיה מקודם...)
st.markdown("""<style> .task-card { background: white; padding: 20px; border-radius: 12px; border-left: 10px solid #ddd; margin-bottom: 15px; } .diff-Hard { border-left-color: #ff4b4b; } .diff-Medium { border-left-color: #ffa726; } .diff-Easy { border-left-color: #66bb6a; } </style>""", unsafe_allow_html=True)

if "xp" not in st.session_state: st.session_state.xp = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}

# =========================
# 5. Renderers
# =========================
def handle_complete(i):
    task = st.session_state.current_tasks[i]
    st.session_state.xp += task['xp']
    with st.spinner("Generating next challenge..."):
        new_txt = get_new_task(st.session_state.user_details['sub'], st.session_state.user_details['top'], task['difficulty'])
        st.session_state.current_tasks[i]['text'] = new_txt
    st.toast("XP Earned! 🚀")

def render_arcade():
    if not st.session_state.user_details:
        with st.form("start_game"):
            sub = st.text_input("Subject", "Linear Algebra")
            top = st.text_input("Topic", "Matrices")
            f = st.file_uploader("Optional: Upload PDF", type="pdf")
            if st.form_submit_button("Start Mission"):
                txt = extract_text_from_pdf(f) if f else None
                data = get_initial_plan(sub, top, txt)
                if data:
                    st.session_state.current_tasks = data['tasks']
                    st.session_state.user_details = {"sub": sub, "top": top}
                    st.rerun()
    else:
        st.subheader(f"Working on: {st.session_state.user_details['top']}")
        for i, task in enumerate(st.session_state.current_tasks):
            st.markdown(f"<div class='task-card diff-{task['difficulty']}'><b>{task['difficulty']}</b> | {task['xp']} XP<br>{task['text']}</div>", unsafe_allow_html=True)
            st.button("✅ Done", key=f"d{i}", on_click=handle_complete, args=(i,))
        
        if st.button("🏳️ End Mission"):
            st.session_state.user_details = {}
            st.rerun()

# Router
page = st.sidebar.radio("Navigate", ["Arcade", "Profile"])
st.sidebar.write(f"Total XP: {st.session_state.xp}")
if st.sidebar.button("Reset Cache"): st.cache_data.clear()

if page == "Arcade": render_arcade()
else: st.write("Profile stats coming soon!")
