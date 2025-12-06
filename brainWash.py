import streamlit as st
import google.generativeai as genai
import json
import os
import pypdf
import random
import html  # <--- NEW: Imported to fix the error
from dotenv import load_dotenv

# --- 1. Load Environment Variables ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# --- 2. Page Configuration ---
st.set_page_config(
    page_title="NeuroQuest: Arcade Mode",
    page_icon="🎮",
    layout="centered"
)

# --- 3. Custom CSS (Arcade Light Theme) ---
st.markdown("""
    <style>
    /* Global Styles */
    .stApp {
        background-color: #f4f6f9;
        color: #2c3e50;
    }

    /* Avatar Container */
    .avatar-box {
        text-align: center;
        padding: 30px;
        background: linear-gradient(135deg, #7F00FF 0%, #E100FF 100%);
        border-radius: 25px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 10px 25px rgba(127, 0, 255, 0.3);
        border: 4px solid white;
    }
    .avatar-emoji { 
        font-size: 80px; 
        display: block; 
        filter: drop-shadow(0 5px 5px rgba(0,0,0,0.2));
        animation: bounce 2s infinite; 
    }

    /* Task Cards */
    .task-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left-width: 8px;
        border-left-style: solid;
        color: #333; /* Ensure text is dark */
    }

    /* Difficulty Colors */
    .diff-hard { border-left-color: #FFD700; } /* Gold */
    .diff-med { border-left-color: #3498db; }  /* Blue */
    .diff-easy { border-left-color: #2ecc71; } /* Green */

    .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        color: white;
        margin-bottom: 8px;
    }
    .badge-hard { background-color: #FFD700; color: #5c4d00; }
    .badge-med { background-color: #3498db; }
    .badge-easy { background-color: #2ecc71; }

    /* Button Styling Override */
    div.stButton > button {
        border-radius: 10px;
        font-weight: bold;
        border: none;
    }

    /* Animations */
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    </style>
""", unsafe_allow_html=True)


# --- 4. Logic & Helpers ---

def get_valid_model():
    try:
        genai.configure(api_key=API_KEY)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return m.name
    except:
        return None
    return None


def clean_json_text(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()


def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return None


# -- API: Initial Plan (5 Tasks sorted) --
def get_initial_plan(subject, topic, context_text=None):
    model_name = get_valid_model()
    if not model_name: return json.dumps({"error": "No valid Gemini models found."})

    model = genai.GenerativeModel(model_name)

    if context_text:
        source_material = f"PDF Content (Summarized): {context_text[:30000]}"
    else:
        source_material = f"Topic: {topic}"

    # Strict JSON prompt for 5 tasks
    prompt = f"""
    Gamify a study plan for Subject: {subject} based on: {source_material}.

    Generate exactly 5 study micro-tasks sorted by difficulty:
    - 1 Hard Task (Complex application/synthesis)
    - 2 Medium Tasks (Explanation/Connection)
    - 2 Easy Tasks (Definition/Recall)

    Also suggest 2 habits and 2 goals.

    Return JSON ONLY with this structure:
    {{
        "tasks": [
            {{"text": "task description...", "difficulty": "Hard", "xp": 300}},
            {{"text": "task description...", "difficulty": "Medium", "xp": 150}},
            {{"text": "task description...", "difficulty": "Medium", "xp": 150}},
            {{"text": "task description...", "difficulty": "Easy", "xp": 50}},
            {{"text": "task description...", "difficulty": "Easy", "xp": 50}}
        ],
        "habits": ["habit1", "habit2"],
        "goals": ["goal1", "goal2"]
    }}
    """
    try:
        response = model.generate_content(prompt)
        return clean_json_text(response.text)
    except Exception as e:
        return json.dumps({"error": str(e)})


# -- API: Replacement Task (Maintains difficulty) --
def get_single_new_task(subject, topic, difficulty, context_text=None):
    model_name = get_valid_model()
    if not model_name: return "Review material (Error)"
    model = genai.GenerativeModel(model_name)

    diff_prompt = ""
    if difficulty == "Hard":
        diff_prompt = "Create a complex, difficult task."
    elif difficulty == "Medium":
        diff_prompt = "Create a moderate difficulty task."
    else:
        diff_prompt = "Create a simple, easy task."

    source = f"PDF content: {context_text[:5000]}" if context_text else f"Topic: {topic}"

    prompt = f"""
    {diff_prompt}
    Context: {source}.
    Return ONLY the task text string. No JSON.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Review your notes."


# --- 5. Gamification Logic ---
def get_brain_status(xp):
    if xp < 300:
        return "🧟", "Brain Rot", "You are losing neurons! Stop skipping!"
    elif xp < 700:
        return "🧠", "Brain Builder", "Building momentum..."
    elif xp < 1000:
        return "🔥", "Brain heater", "you getting there..."
    elif xp < 1200:
        return "⚡", "High Voltage", "You're on fire!"
    elif xp < 1600:
        return "🧬", "Neuron party", "can you feel it yet?"
    elif xp < 2000:
        return "🔮", "Master Mind", "Unstoppable force."
    else:
        return "🌌", "GALAXY BRAIN", "Academic God Mode."



def get_leaderboard(user_xp):
    data = [
        {"name": "Study_Wiz_99", "xp": 4200},
        {"name": "Focus_Ninja", "xp": 2800},
        {"name": "NoScroll_Dave", "xp": 1200},
        {"name": "YOU", "xp": user_xp}
    ]
    return sorted(data, key=lambda x: x['xp'], reverse=True)


# --- 6. Event Handlers ---
def handle_task_action(index, action):
    task = st.session_state.current_tasks[index]

    # 1. Update XP
    if action == "complete":
        st.session_state.xp += task['xp']
        st.toast(f"🎉 +{task['xp']} XP! Quest Complete!")
    elif action == "delete":
        penalty = int(task['xp'] / 2)
        st.session_state.xp = max(0, st.session_state.xp - penalty)
        st.toast(f"💨 Skipped... -{penalty} XP penalty.")

    # 2. Get Context
    c_sub = st.session_state.user_details.get('sub')
    c_top = st.session_state.user_details.get('top')
    c_text = st.session_state.user_details.get('pdf_text')

    # 3. Replace Task (Same Difficulty)
    with st.spinner("Generating new quest..."):
        new_text = get_single_new_task(c_sub, c_top, task['difficulty'], c_text)
        # Update text but keep metadata (difficulty/xp) same
        st.session_state.current_tasks[index]['text'] = new_text


def reset_session(keep_xp=True):
    st.session_state.current_tasks = []
    st.session_state.user_details = {}
    if not keep_xp:
        st.session_state.xp = 0


# --- 7. Session State ---
if "xp" not in st.session_state: st.session_state.xp = 0
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "show_leaderboard" not in st.session_state: st.session_state.show_leaderboard = False

# --- 8. UI Layout ---

st.title("🎮 NeuroQuest Arcade")

if not API_KEY:
    st.error("❌ API Key not found! Check `.env`.")
    st.stop()

# --- TOP BAR ---
col_av, col_btn = st.columns([0.7, 0.3])

with col_av:
    emoji, title, desc = get_brain_status(st.session_state.xp)
    st.markdown(f"""
        <div class="avatar-box">
            <div class="avatar-emoji">{emoji}</div>
            <div style="font-size:24px; font-weight:bold;">{title}</div>
            <div style="opacity:0.9;">{desc}</div>
            <div style="font-size:20px; font-weight:bold; margin-top:10px; background:rgba(0,0,0,0.2); border-radius:10px; padding:5px;">
                ⭐ {st.session_state.xp} XP
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.write("")
    st.write("")
    if st.button("🏆 Leaderboard", use_container_width=True):
        st.session_state.show_leaderboard = not st.session_state.show_leaderboard

# --- LEADERBOARD ---
if st.session_state.show_leaderboard:
    st.info("🏆 **Global Leaderboard**")
    leaderboard = get_leaderboard(st.session_state.xp)
    for idx, player in enumerate(leaderboard):
        is_user = " (You)" if player['name'] == "YOU" else ""
        icon = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "👤"
        st.write(f"**{icon} #{idx + 1} {player['name']}{is_user}** — {player['xp']} XP")
    st.divider()

# --- MAIN GAME LOOP ---

# STATE 1: LOBBY (Input)
if not st.session_state.user_details:
    st.markdown("### 🕹️ Select Your Mission")

    tab1, tab2 = st.tabs(["📝 Custom Topic", "📂 Upload Data"])

    with tab1:
        with st.form("manual_form"):
            sub = st.text_input("Subject", placeholder="History")
            top = st.text_input("Topic", placeholder="Roman Empire")
            submit_manual = st.form_submit_button("Start Game")

    with tab2:
        with st.form("pdf_form"):
            pdf_sub = st.text_input("Subject", placeholder="Biology")
            uploaded_file = st.file_uploader("Upload PDF", type="pdf")
            submit_pdf = st.form_submit_button("Analyze & Play")

    # Processing
    final_sub, final_top, final_text = None, None, None
    start_game = False

    if submit_manual and sub and top:
        final_sub, final_top = sub, top
        start_game = True

    if submit_pdf and uploaded_file and pdf_sub:
        with st.spinner("Scanning file..."):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                final_sub = pdf_sub
                final_top = uploaded_file.name
                final_text = text
                start_game = True
            else:
                st.error("Corrupted PDF.")

    if start_game:
        with st.spinner("Generating Level 1..."):
            raw = get_initial_plan(final_sub, final_top, final_text)
            try:
                data = json.loads(raw)
                st.session_state.current_tasks = data.get("tasks", [])
                st.session_state.habits = data.get("habits", [])
                st.session_state.goals = data.get("goals", [])
                st.session_state.user_details = {"sub": final_sub, "top": final_top, "pdf_text": final_text}
                st.rerun()
            except:
                st.error("Server Error. Try again.")

# STATE 2: GAMEPLAY
else:
    c_topic = st.session_state.user_details['top']
    st.markdown(f"### ⚔️ Current Quest: {c_topic}")

    # Render Tasks
    for i, task in enumerate(st.session_state.current_tasks):

        # Determine styling based on difficulty
        diff = task.get('difficulty', 'Easy')
        xp = task.get('xp', 50)

        if diff == "Hard":
            css_class = "diff-hard"
            badge_class = "badge-hard"
            icon = "🔥"
        elif diff == "Medium":
            css_class = "diff-med"
            badge_class = "badge-med"
            icon = "⚔️"
        else:
            css_class = "diff-easy"
            badge_class = "badge-easy"
            icon = "🛡️"

        # SANITIZE TEXT TO PREVENT INVALID CHARACTER ERROR
        safe_text = html.escape(task['text'])

        # HTML Card
        st.markdown(f"""
        <div class="task-card {css_class}">
            <span class="badge {badge_class}">{icon} {diff} | +{xp} XP</span>
            <div style="font-size: 1.1em; font-weight: 500; margin-top: 5px;">
                {safe_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Actions
        c1, c2, spacer = st.columns([0.2, 0.2, 0.6])
        with c1:
            st.button("✅ Claim XP", key=f"c_{i}", on_click=handle_task_action, args=(i, "complete"))
        with c2:
            st.button("🗑️ Reroll", key=f"s_{i}", on_click=handle_task_action, args=(i, "delete"), help="Costs 50% XP")

    st.divider()

    # Footer
    with st.expander("🎒 Inventory (Habits & Goals)"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🛡️ Buffs (Habits)**")
            for h in st.session_state.habits: st.write(f"- {h}")
        with c2:
            st.markdown("**🎯 Side Quests (Goals)**")
            for g in st.session_state.goals: st.write(f"- {g}")

    # Controls
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    if b1.button("🔄 New Mission (Keep XP)", use_container_width=True):
        reset_session(keep_xp=True)
        st.rerun()
    if b2.button("💀 Game Over (Reset All)", type="primary", use_container_width=True):
        reset_session(keep_xp=False)
        st.rerun()