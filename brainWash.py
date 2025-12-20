import os
import json
import streamlit as st
import pypdf
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

# ======================
# 1. API KEY
# ======================
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("Missing GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=API_KEY)

# ======================
# 2. MODELS + FALLBACK
# ======================
MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]

def generate_with_fallback(prompt, json_mode=False):
    last_error = None

    for model_name in MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json"
                } if json_mode else None
            )
            return response.text
        except Exception as e:
            last_error = e

    raise RuntimeError(f"All models failed. Last error: {last_error}")

# ======================
# 3. HELPERS
# ======================
def extract_text_from_pdf(uploaded_file):
    reader = pypdf.PdfReader(uploaded_file)
    return "".join(page.extract_text() or "" for page in reader.pages)

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

# ======================
# 4. STREAMLIT UI
# ======================
st.set_page_config(page_title="BrainWash Arcade", page_icon="🧠", layout="wide")

if "xp" not in st.session_state:
    st.session_state.xp = 0
if "tasks" not in st.session_state:
    st.session_state.tasks = []
if "meta" not in st.session_state:
    st.session_state.meta = {}

st.sidebar.title("🧠 BrainWash")
st.sidebar.metric("XP", st.session_state.xp)

st.title("🎮 Arcade Mode")

if not st.session_state.tasks:
    with st.form("start"):
        subject = st.text_input("Subject", "Math")
        topic = st.text_input("Topic", "Matrices")
        if st.form_submit_button("Start Game"):
            with st.spinner("Generating..."):
                data = get_initial_plan(subject, topic)
                st.session_state.tasks = data["tasks"]
                st.session_state.meta = {"subject": subject, "topic": topic}
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

        if st.button("✅ Complete", key=f"c{i}"):
            st.session_state.xp += task["xp"]
            st.session_state.tasks[i]["text"] = get_new_task(
                st.session_state.meta["subject"],
                st.session_state.meta["topic"],
                task["difficulty"]
            )
            st.rerun()

    if st.button("🏳️ End Mission"):
        st.session_state.tasks = []
        st.session_state.meta = {}
        st.rerun()
