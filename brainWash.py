import os
import json
import streamlit as st
import pypdf
import pandas as pd
from dotenv import load_dotenv
from google import genai

# =========================
# 0. FORCE AI STUDIO (NO VERTEX)
# =========================
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"

# =========================
# 1. API KEY
# =========================
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("Missing GOOGLE_API_KEY")
    st.stop()

client = genai.Client(api_key=API_KEY)

# =========================
# 2. PAGE CONFIG
# =========================
st.set_page_config(
    page_title="BrainWash Arcade",
    page_icon="🧠",
    layout="wide"
)

# =========================
# 3. MODELS + FALLBACK
# =========================
MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-1.0-pro"
]

def generate_with_fallback(prompt, json_mode=False):
    last_error = None

    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json"} if json_mode else None
            )
            return response.text
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All models failed. Last error: {last_error}")

# =========================
# 4. HELPERS
# =========================
def extract_text_from_pdf(uploaded_file):
    try:
        reader = pypdf.PdfReader(uploaded_file)
        return "".join(page.extract_text() or "" for page in reader.pages)
    except:
        return ""

def get_initial_plan(subject, topic, context=None):
    source = context[:8000] if context else topic

    prompt = f"""
Gamify a study plan.

Subject: {subject}
Topic: {topic}
Source: {source}

Create exactly 5 tasks:
1 Hard (300 XP)
2 Medium (150 XP)
2 Easy (50 XP)

Return ONLY valid JSON:
{{
  "tasks": [
    {{"text": "...", "difficulty": "Hard", "xp": 300}},
    {{"text": "...", "difficulty": "Medium", "xp": 150}},
    {{"text": "...", "difficulty": "Medium", "xp": 150}},
    {{"text": "...", "difficulty": "Easy", "xp": 50}},
    {{"text": "...", "difficulty": "Easy", "xp": 50}}
  ]
}}
"""

    raw = generate_with_fallback(prompt, json_mode=True)
    return json.loads(raw)

def get_new_task(subject, topic, difficulty):
    prompt = f"""
Create ONE {difficulty} study task.
Subject: {subject}
Topic: {topic}
Return only the task text.
"""
    return generate_with_fallback(prompt).strip()

# =========================
# 5. GAME STATE
# =========================
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "meta" not in st.session_state:
    st.session_state.meta = {}

# =========================
# 6. UI
# =========================
st.sidebar.title("🧠 BrainWash")
st.sidebar.metric("XP", st.session_state.xp)

page = st.sidebar.radio("Menu", ["🎮 Arcade", "👤 Profile"])

# =========================
# 7. PROFILE
# =========================
if page == "👤 Profile":
    st.title("👤 Brain Profile")
    st.metric("Total XP", st.session_state.xp)
    st.progress(min(st.session_state.xp / 2500, 1.0))
    st.stop()

# =========================
# 8. ARCADE
# =========================
st.title("🎮 Arcade Mode")

if not st.session_state.tasks:
    col1, col2 = st.columns(2)

    with col1:
        with st.form("manual"):
            st.subheader("Manual Mission")
            subject = st.text_input("Subject", "Math")
            topic = st.text_input("Topic", "Matrices")

            if st.form_submit_button("Start Game"):
                with st.spinner("Generating mission..."):
                    data = get_initial_plan(subject, topic)
                    st.session_state.tasks = data["tasks"]
                    st.session_state.meta = {"subject": subject, "topic": topic}
                    st.rerun()

    with col2:
        with st.form("pdf"):
            st.subheader("PDF Mission")
            subject = st.text_input("PDF Subject", "History")
            pdf = st.file_uploader("Upload PDF", type="pdf")

            if st.form_submit_button("Analyze & Play") and pdf:
                with st.spinner("Reading PDF..."):
                    text = extract_text_from_pdf(pdf)
                    data = get_initial_plan(subject, pdf.name, text)
                    st.session_state.tasks = data["tasks"]
                    st.session_state.meta = {"subject": subject, "topic": pdf.name}
                    st.rerun()

else:
    for i, task in enumerate(st.session_state.tasks):
        st.markdown(
            f"""
<div style="background:white;padding:16px;border-radius:12px;margin-bottom:10px">
<b>{task['difficulty']}</b> | +{task['xp']} XP  
<br>{task['text']}
</div>
""",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)

        if c1.button("✅ Complete", key=f"c{i}"):
            st.session_state.xp += task["xp"]
            new_text = get_new_task(
                st.session_state.meta["subject"],
                st.session_state.meta["topic"],
                task["difficulty"],
            )
            st.session_state.tasks[i]["text"] = new_text
            st.toast(f"+{task['xp']} XP")
            st.rerun()

        if c2.button("🎲 Reroll (-20 XP)", key=f"r{i}") and st.session_state.xp >= 20:
            st.session_state.xp -= 20
            st.session_state.tasks[i]["text"] = get_new_task(
                st.session_state.meta["subject"],
                st.session_state.meta["topic"],
                task["difficulty"],
            )
            st.rerun()

    if st.button("🏳️ End Mission"):
        st.session_state.tasks = []
        st.session_state.meta = {}
        st.rerun()
