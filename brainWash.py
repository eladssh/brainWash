import streamlit as st
from google import genai
from google.genai import types
import json
import os
import pypdf
import html
import pandas as pd
import time
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import sqlite3
from pathlib import Path

# --- 1. Database Setup ---
DB_PATH = Path("brainwash.db")

def init_database():
    """Initialize SQLite database with User and TaskCompletion tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            total_xp INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            daily_goal INTEGER DEFAULT 3,
            streak_days INTEGER DEFAULT 0,
            last_activity_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            subjects_interested TEXT,
            learning_style TEXT,
            weekly_commitment INTEGER DEFAULT 3
        )
    """)
    
    # TaskCompletion table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TaskCompletion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            xp_earned INTEGER NOT NULL,
            subject TEXT,
            topic TEXT,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    conn.commit()
    conn.close()

def get_or_create_user(username, onboarding_data=None):
    """Get existing user or create new one"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user and onboarding_data:
        cursor.execute("""
            INSERT INTO User (username, subjects_interested, learning_style, weekly_commitment, daily_goal)
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            onboarding_data.get('subjects', ''),
            onboarding_data.get('style', ''),
            onboarding_data.get('commitment', 3),
            onboarding_data.get('daily_goal', 3)
        ))
        conn.commit()
        cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
        user = cursor.fetchone()
    
    conn.close()
    return user

def update_user_stats(username, xp_gained=0, task_completed=False):
    """Update user XP, tasks, and streak"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current user data
    cursor.execute("SELECT id, total_xp, tasks_completed, streak_days, last_activity_date FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user:
        user_id, current_xp, current_tasks, streak, last_date = user
        new_xp = current_xp + xp_gained
        new_tasks = current_tasks + (1 if task_completed else 0)
        
        # Update streak
        today = str(date.today())
        new_streak = streak
        if last_date != today:
            if last_date == str(date.today() - timedelta(days=1)):
                new_streak = streak + 1
            else:
                new_streak = 1
        
        cursor.execute("""
            UPDATE User 
            SET total_xp = ?, tasks_completed = ?, streak_days = ?, last_activity_date = ?
            WHERE username = ?
        """, (new_xp, new_tasks, new_streak, today, username))
        
        conn.commit()
    
    conn.close()

def log_task_completion(username, task_text, difficulty, xp_earned, subject, topic):
    """Log a completed task"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute("""
            INSERT INTO TaskCompletion (user_id, task_text, difficulty, xp_earned, subject, topic)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user[0], task_text, difficulty, xp_earned, subject, topic))
        conn.commit()
    
    conn.close()

def get_user_analytics(username):
    """Get analytics data for insights dashboard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get user ID
    cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    user_id = user[0]
    
    # Tasks by day (last 7 days)
    cursor.execute("""
        SELECT DATE(completed_at) as day, COUNT(*) as count
        FROM TaskCompletion
        WHERE user_id = ? AND DATE(completed_at) >= DATE('now', '-7 days')
        GROUP BY DATE(completed_at)
        ORDER BY day
    """, (user_id,))
    daily_tasks = cursor.fetchall()
    
    # XP by day (last 7 days)
    cursor.execute("""
        SELECT DATE(completed_at) as day, SUM(xp_earned) as total_xp
        FROM TaskCompletion
        WHERE user_id = ? AND DATE(completed_at) >= DATE('now', '-7 days')
        GROUP BY DATE(completed_at)
        ORDER BY day
    """, (user_id,))
    daily_xp = cursor.fetchall()
    
    # Tasks by difficulty
    cursor.execute("""
        SELECT difficulty, COUNT(*) as count
        FROM TaskCompletion
        WHERE user_id = ?
        GROUP BY difficulty
    """, (user_id,))
    difficulty_breakdown = cursor.fetchall()
    
    # Tasks by subject
    cursor.execute("""
        SELECT subject, COUNT(*) as count, SUM(xp_earned) as total_xp
        FROM TaskCompletion
        WHERE user_id = ?
        GROUP BY subject
        ORDER BY count DESC
        LIMIT 5
    """, (user_id,))
    subject_stats = cursor.fetchall()
    
    # Recent tasks
    cursor.execute("""
        SELECT task_text, difficulty, xp_earned, subject, completed_at
        FROM TaskCompletion
        WHERE user_id = ?
        ORDER BY completed_at DESC
        LIMIT 10
    """, (user_id,))
    recent_tasks = cursor.fetchall()
    
    conn.close()
    
    return {
        'daily_tasks': daily_tasks,
        'daily_xp': daily_xp,
        'difficulty_breakdown': difficulty_breakdown,
        'subject_stats': subject_stats,
        'recent_tasks': recent_tasks
    }

def get_today_progress(username):
    """Get today's task completion count"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return 0
    
    today = str(date.today())
    cursor.execute("""
        SELECT COUNT(*) FROM TaskCompletion
        WHERE user_id = ? AND DATE(completed_at) = ?
    """, (user[0], today))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Initialize database
init_database()

# --- 2. Init & Config ---
load_dotenv()
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Arcade",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    
    .white-card {
        background: white; 
        padding: 25px; 
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6; 
        text-align: center;
        height: 400px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
    
    .white-card h3 {
        margin: 0 0 15px 0;
        flex-shrink: 0;
    }
    
    .scrollable-content {
        overflow-y: auto;
        overflow-x: hidden;
        flex-grow: 1;
        text-align: left;
        padding-right: 5px;
    }

    .stat-box {
        background: #f8f9fa; 
        border-radius: 12px; 
        padding: 15px;
        margin-bottom: 10px; 
        border: 1px solid #eee;
        word-wrap: break-word;
    }

    .brain-avatar { 
        font-size: 70px; 
        display: block; 
        margin-bottom: 10px;
        animation: float 3s ease-in-out infinite;
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    .friend-row {
        display: flex; 
        align-items: center; 
        justify-content: space-between;
        padding: 10px 0; 
        border-bottom: 1px solid #f8f9fa;
        font-size: 0.9em;
        word-wrap: break-word;
    }
    
    .friend-row > div {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .status-dot { 
        height: 10px; 
        width: 10px; 
        border-radius: 50%; 
        display: inline-block; 
        flex-shrink: 0;
        margin-left: 10px;
    }
    .online { background-color: #66bb6a; }
    .offline { background-color: #bdbdbd; }

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
    
    .badge-card { 
        background: white; 
        padding: 15px; 
        border-radius: 15px;
        border: 1px solid #eef2f6; 
        text-align: center; 
        height: 180px;
    }
    .badge-icon { font-size: 40px; }
    .locked { filter: grayscale(100%); opacity: 0.3; }

    .intro-banner {
        background: linear-gradient(90deg, #7F00FF 0%, #E100FF 100%);
        color: white; 
        padding: 25px; 
        border-radius: 20px; 
        margin-bottom: 30px;
    }
    
    .white-card .stButton {
        margin-top: auto;
        flex-shrink: 0;
    }
    
    .onboarding-container {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: 50px auto;
    }
    
    .daily-goal-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    
    .insight-metric {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. AI Core
def get_ai_client():
    if not API_KEY:
        st.error("Missing API Key!")
        return None
    return genai.Client(api_key=API_KEY)

def get_ai_response(prompt, is_json=False):
    client = get_ai_client()
    if not client: return None
    model_id = "gemini-2.5-flash"
    config = types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json" if is_json else "text/plain"
    )
    try:
        response = client.models.generate_content(model=model_id, contents=prompt, config=config)
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def get_initial_plan(subject, topic, context="", user_context=""):
    prompt = f"""
    Create a personalized study plan for {subject}: {topic}. 
    {f'User learning context: {user_context}' if user_context else ''}
    {f'Material context: {context[:5000]}' if context else ''}
    Return exactly 5 tasks (1 Hard, 2 Medium, 2 Easy).
    Each task MUST have a brief "solution".
    Return ONLY JSON:
    {{ "tasks": [
        {{"text": "Task...", "difficulty": "Hard", "xp": 300, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Medium", "xp": 150, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "..."}},
        {{"text": "Task...", "difficulty": "Easy", "xp": 50, "solution": "..."}}
    ] }}
    """
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else None

def get_new_task_json(subject, topic, diff, user_context=""):
    prompt = f"Create one new {diff} study task for {subject}: {topic}. {f'User context: {user_context}' if user_context else ''} Include a brief solution. Return ONLY JSON: {{'text': '...', 'solution': '...'}}"
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else {"text": "Review materials", "solution": "No solution available."}

# --- 4. Logic & State ---
if "onboarded" not in st.session_state: st.session_state.onboarded = False
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_db_data" not in st.session_state: st.session_state.user_db_data = None

BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "Time to study!"),
    (300, "🧠 Brain Builder", "Foundation set."),
    (800, "🔥 Brain Heater", "Getting warm!"),
    (1500, "⚡ High Voltage", "Sparking intelligence!"),
    (2500, "🌌 GALAXY BRAIN", "Universal Wisdom.")
]

ACHIEVEMENTS = [
    {"id": "first", "name": "The Initiate", "emoji": "🥉", "req": 100, "desc": "100 XP Earned"},
    {"id": "pro", "name": "Scholar", "emoji": "🥈", "req": 10, "type": "tasks", "desc": "10 Quests Done"},
    {"id": "master", "name": "Sage", "emoji": "🥇", "req": 1500, "desc": "1,500 XP Earned"},
    {"id": "god", "name": "Galaxy Brain", "emoji": "🌌", "req": 5000, "desc": "5,000 XP Earned"}
]

def get_brain_status(xp):
    current = BRAIN_LEVELS[0]
    next_limit = BRAIN_LEVELS[1][0]
    for i, level in enumerate(BRAIN_LEVELS):
        if xp >= level[0]:
            current = level
            next_limit = BRAIN_LEVELS[i+1][0] if i+1 < len(BRAIN_LEVELS) else xp * 1.5
    return current, next_limit

def load_user_data():
    """Load user data from database into session state"""
    if st.session_state.user_name:
        user = get_or_create_user(st.session_state.user_name)
        if user:
            st.session_state.user_db_data = {
                'id': user[0],
                'username': user[1],
                'total_xp': user[2],
                'tasks_completed': user[3],
                'daily_goal': user[4],
                'streak_days': user[5],
                'last_activity_date': user[6],
                'subjects_interested': user[8],
                'learning_style': user[9],
                'weekly_commitment': user[10]
            }

# --- 5. Onboarding ---
def render_onboarding():
    st.markdown("""
        <div class="onboarding-container">
            <h1 style="text-align: center; color: #7F00FF;">🧠 Welcome to BrainWash!</h1>
            <p style="text-align: center; color: #666; margin-bottom: 30px;">
                Let's personalize your learning journey
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("onboarding_form"):
        st.subheader("📝 Basic Info")
        username = st.text_input("Choose a username", placeholder="brain_master_2024")
        
        st.divider()
        st.subheader("🎯 Learning Preferences")
        
        subjects = st.text_area(
            "What subjects are you studying?",
            placeholder="e.g., Mathematics, Physics, Programming, History",
            help="Separate with commas"
        )
        
        learning_style = st.selectbox(
            "What's your learning style?",
            ["Visual (diagrams, videos)", "Auditory (lectures, discussions)", 
             "Reading/Writing (notes, articles)", "Kinesthetic (hands-on practice)"]
        )
        
        weekly_commitment = st.slider(
            "How many hours can you study per week?",
            min_value=1, max_value=40, value=10
        )
        
        daily_goal = st.slider(
            "Daily task goal (tasks per day)",
            min_value=1, max_value=20, value=3,
            help="How many tasks do you want to complete each day?"
        )
        
        st.divider()
        st.subheader("🎮 Experience Level")
        experience = st.radio(
            "How familiar are you with gamified learning?",
            ["Complete beginner", "I've tried it before", "I'm a pro!"]
        )
        
        submitted = st.form_submit_button("🚀 Start My Journey!", use_container_width=True, type="primary")
        
        if submitted:
            if not username:
                st.error("Please enter a username!")
            else:
                # Create user in database
                onboarding_data = {
                    'subjects': subjects,
                    'style': learning_style,
                    'commitment': weekly_commitment,
                    'daily_goal': daily_goal
                }
                
                user = get_or_create_user(username, onboarding_data)
                
                if user:
                    st.session_state.user_name = username
                    st.session_state.onboarded = True
                    load_user_data()
                    st.success(f"Welcome aboard, {username}! 🎉")
                    time.sleep(1)
                    st.rerun()

# --- 6. Daily Goal Widget ---
def render_daily_goal():
    if not st.session_state.user_db_data:
        return
    
    daily_goal = st.session_state.user_db_data['daily_goal']
    today_count = get_today_progress(st.session_state.user_name)
    progress_pct = min(today_count / daily_goal, 1.0)
    
    st.markdown(f"""
        <div class="daily-goal-card">
            <h3 style="margin: 0 0 10px 0;">🎯 Daily Goal</h3>
            <h1 style="margin: 0;">{today_count} / {daily_goal}</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">tasks completed today</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.progress(progress_pct)
    
    if today_count >= daily_goal:
        st.success("🎉 Daily goal achieved! Keep going!")
    elif today_count >= daily_goal * 0.5:
        st.info(f"💪 Halfway there! {daily_goal - today_count} more to go!")

# --- 7. Insights Dashboard ---
def render_insights():
    st.title("📊 Learning Insights")
    
    if not st.session_state.user_db_data:
        st.warning("No data available yet. Complete some tasks to see your insights!")
        return
    
    analytics = get_user_analytics(st.session_state.user_name)
    
    if not analytics:
        st.warning("No analytics data available yet.")
        return
    
    # Key Metrics
    st.subheader("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="insight-metric">
                <h2 style="color: #7F00FF; margin: 0;">{st.session_state.user_db_data['total_xp']}</h2>
                <p style="margin: 5px 0 0 0; color: #666;">Total XP</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="insight-metric">
                <h2 style="color: #ff4b4b; margin: 0;">{st.session_state.user_db_data['tasks_completed']}</h2>
                <p style="margin: 5px 0 0 0; color: #666;">Tasks Done</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="insight-metric">
                <h2 style="color: #ffa726; margin: 0;">{st.session_state.user_db_data['streak_days']}</h2>
                <p style="margin: 5px 0 0 0; color: #666;">Day Streak 🔥</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_xp = st.session_state.user_db_data['total_xp'] // max(st.session_state.user_db_data['tasks_completed'], 1)
        st.markdown(f"""
            <div class="insight-metric">
                <h2 style="color: #66bb6a; margin: 0;">{avg_xp}</h2>
                <p style="margin: 5px 0 0 0; color: #666;">Avg XP/Task</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Activity Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 7-Day Activity")
        if analytics['daily_tasks']:
            df_daily = pd.DataFrame(analytics['daily_tasks'], columns=['Date', 'Tasks'])
            st.bar_chart(df_daily.set_index('Date'))
        else:
            st.info("No activity data yet for the past 7 days.")
    
    with col2:
        st.subheader("⚡ XP Earned (7 Days)")
        if analytics['daily_xp']:
            df_xp = pd.DataFrame(analytics['daily_xp'], columns=['Date', 'XP'])
            st.area_chart(df_xp.set_index('Date'), color="#7F00FF")
        else:
            st.info("No XP data yet for the past 7 days.")
    
    st.divider()
    
    # Difficulty Breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Tasks by Difficulty")
        if analytics['difficulty_breakdown']:
            df_diff = pd.DataFrame(analytics['difficulty_breakdown'], columns=['Difficulty', 'Count'])
            st.bar_chart(df_diff.set_index('Difficulty'), color="#E100FF")
        else:
            st.info("No difficulty data available.")
    
    with col2:
        st.subheader("📚 Top Subjects")
        if analytics['subject_stats']:
            for subject, count, xp in analytics['subject_stats']:
                st.markdown(f"""
                    <div class="stat-box">
                        <strong>{subject}</strong><br>
                        <small>{count} tasks • {xp} XP earned</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No subject data available.")
    
    st.divider()
    
    # Recent Activity
    st.subheader("🕐 Recent Activity")
    if analytics['recent_tasks']:
        for task_text, difficulty, xp, subject, completed_at in analytics['recent_tasks'][:5]:
            completed_date = datetime.fromisoformat(completed_at).strftime("%b %d, %I:%M %p")
            color = {"Hard": "#ff4b4b", "Medium": "#ffa726", "Easy": "#66bb6a"}.get(difficulty, "#999")
            st.markdown(f"""
                <div class="task-card diff-{difficulty}">
                    <span style="background: {color}; color: white; padding: 3px 8px; border-radius: 5px; font-size: 0.8em;">
                        {difficulty} • +{xp} XP
                    </span>
                    <div style="margin-top: 8px;"><strong>{subject}</strong></div>
                    <div style="margin-top: 5px; color: #666;">{html.escape(task_text)}</div>
                    <small style="color: #999;">{completed_date}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent tasks to display.")

# --- 8. UI Renderers ---
def render_profile():
    st.title("👤 Brain Profile")
    
    if not st.session_state.user_db_data:
        st.error("User data not loaded!")
        return
    
    user_data = st.session_state.user_db_data
    
    with st.expander("📝 Edit Profile"):
        new_goal = st.number_input("Daily Goal", value=user_data['daily_goal'], min_value=1, max_value=20)
        if st.button("Save Changes"):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE User SET daily_goal = ? WHERE username = ?", 
                         (new_goal, st.session_state.user_name))
            conn.commit()
            conn.close()
            load_user_data()
            st.success("Profile updated!")
            st.rerun()

    (lvl_xp, lvl_title, lvl_desc), next_limit = get_brain_status(user_data['total_xp'])
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        emoji = lvl_title.split()[0]
        st.markdown(f"""
            <div class="white-card">
                <div class="brain-avatar">{emoji}</div>
                <h2>{st.session_state.user_name}</h2>
                <h4 style="color: #7F00FF;">{lvl_title}</h4>
                <p>{lvl_desc}</p>
                <div style="background:#eee; padding:5px; border-radius:10px;">Level {int(user_data['total_xp'] / 500) + 1}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="white-card">
                <h3 style="margin-bottom: 10px;">📊 Statistics</h3>
                <div class="scrollable-content">
                    <div class="stat-box"><strong>Total XP:</strong> {user_data['total_xp']}</div>
                    <div class="stat-box"><strong>Tasks Done:</strong> {user_data['tasks_completed']}</div>
                    <div class="stat-box"><strong>Day Streak:</strong> 🔥 {user_data['streak_days']} Days</div>
                    <div class="stat-box"><strong>Daily Goal:</strong> {user_data['daily_goal']} tasks/day</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
            <div class="white-card">
                <h3 style="margin-bottom: 10px;">👥 Study Buddies</h3>
                <div class="scrollable-content">
                    <div class="friend-row">
                        <div>
                            <strong>Sarah_Brains</strong><br><small>Physics</small>
                        </div>
                        <span class="status-dot online"></span>
                    </div>
                    <div class="friend-row">
                        <div>
                            <strong>Mike_The_Wiz</strong><br><small>Algebra</small>
                        </div>
                        <span class="status-dot online"></span>
                    </div>
                    <div class="friend-row">
                        <div>
                            <strong>Lazy_Dave</strong><br><small>Last seen 2d ago</small>
                        </div>
                        <span class="status-dot offline"></span>
                    </div>
                </div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #f0f0f0;">
                    <button style="
                        width: 100%;
                        padding: 10px;
                        background: white;
                        border: 2px solid #7F00FF;
                        color: #7F00FF;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s;
                    " onmouseover="this.style.background='#7F00FF'; this.style.color='white';" 
                       onmouseout="this.style.background='white'; this.style.color='#7F00FF';">
                        ➕ Add Friend
                    </button>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()
    
    # Achievements Section
    st.subheader("🏆 Achievements")
    badge_cols = st.columns(len(ACHIEVEMENTS))
    for i, ach in enumerate(ACHIEVEMENTS):
        is_locked = True
        if ach.get("type") == "tasks":
            if user_data['tasks_completed'] >= ach["req"]: 
                is_locked = False
        else:
            if user_data['total_xp'] >= ach["req"]: 
                is_locked = False
        
        with badge_cols[i]:
            status = "locked" if is_locked else ""
            st.markdown(f"""
                <div class="badge-card {status}">
                    <div class="badge-icon">{ach["emoji"]}</div>
                    <strong>{ach["name"]}</strong><br>
                    <small>{ach["desc"]}</small>
                </div>
            """, unsafe_allow_html=True)

    st.divider()
    
    # Focus Mode Timer
    st.subheader("⏲️ Focus Mode")
    with st.expander("Start Deep Work Session"):
        focus_mins = st.slider("Select Duration (Minutes)", 5, 120, 25)
        c1, c2 = st.columns(2)
        if c1.button("🚀 Start Timer", use_container_width=True, type="primary"):
            p = st.empty()
            stop_button_placeholder = c2.empty()
            for s in range(focus_mins * 60, 0, -1):
                if stop_button_placeholder.button("🛑 Stop & Reset", key=f"stop_{s}", use_container_width=True):
                    st.rerun()
                m, sc = divmod(s, 60)
                p.metric("Time Remaining", f"{m:02d}:{sc:02d}")
                time.sleep(1)
            st.balloons()
            update_user_stats(st.session_state.user_name, xp_gained=50)
            load_user_data()
            st.rerun()
    
def render_arcade():
    if not st.session_state.user_db_data:
        st.error("User data not loaded!")
        return
    
    user_data = st.session_state.user_db_data
    
    # Intro Banner
    st.markdown("""
        <div class="intro-banner">
            <h2>Welcome to BrainWash Arcade 🎮</h2>
            <p>Turn study materials into active quests. Earn XP, unlock ranks, and master subjects!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Progress Bar Header
    (lvl_xp, lvl_title, _), next_limit = get_brain_status(user_data['total_xp'])
    prog = min((user_data['total_xp'] - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.write(f"**Rank:** {lvl_title} ({user_data['total_xp']} XP)")
    st.progress(prog)

    if not st.session_state.user_details:
        # User context for AI
        user_context = f"Subjects: {user_data['subjects_interested']}, Learning style: {user_data['learning_style']}"
        
        t1, t2 = st.tabs(["🔍 Subject Search", "📄 PDF Scan"])
        with t1:
            with st.form("manual"):
                sub = st.text_input("Subject", "Math")
                top = st.text_input("Topic", "Matrices")
                if st.form_submit_button("Start Mission"):
                    plan = get_initial_plan(sub, top, user_context=user_context)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("pdf"):
                sub_p = st.text_input("Subject")
                f = st.file_uploader("Upload PDF", type="pdf")
                if st.form_submit_button("Analyze & Play"):
                    if f:
                        reader = pypdf.PdfReader(f)
                        txt = "".join([p.extract_text() for p in reader.pages])
                        plan = get_initial_plan(sub_p, f.name, txt, user_context=user_context)
                        if plan:
                            st.session_state.current_tasks = plan['tasks']
                            st.session_state.user_details = {"sub": sub_p, "top": f.name, "pdf_text": txt}
                            st.rerun()
    else:
        st.caption(f"Mission: {st.session_state.user_details['top']}")
        user_context = f"Subjects: {user_data['subjects_interested']}, Learning style: {user_data['learning_style']}"
        
        for i, task in enumerate(st.session_state.current_tasks):
            d = task['difficulty']
            xp = task['xp']
            st.markdown(f"""
                <div class="task-card diff-{d}">
                    <span class="badge bg-{d}">{d} | +{xp} XP</span>
                    <div style="margin-top:10px;">{html.escape(task['text'])}</div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Done", key=f"d{i}", use_container_width=True, type="primary"):
                    # Update database
                    update_user_stats(st.session_state.user_name, xp_gained=xp, task_completed=True)
                    log_task_completion(
                        st.session_state.user_name,
                        task['text'],
                        d,
                        xp,
                        st.session_state.user_details['sub'],
                        st.session_state.user_details['top']
                    )
                    load_user_data()
                    
                    # Generate new task
                    with st.spinner("New task..."):
                        new = get_new_task_json(
                            st.session_state.user_details['sub'], 
                            st.session_state.user_details['top'], 
                            d,
                            user_context=user_context
                        )
                        st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                    st.rerun()
            with c2:
                if st.button("🎲 Reroll (-20)", key=f"r{i}", use_container_width=True):
                    if user_data['total_xp'] >= 20:
                        update_user_stats(st.session_state.user_name, xp_gained=-20)
                        load_user_data()
                        with st.spinner("Rerolling..."):
                            new = get_new_task_json(
                                st.session_state.user_details['sub'], 
                                st.session_state.user_details['top'], 
                                d,
                                user_context=user_context
                            )
                            st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                        st.rerun()
            
            with st.expander("💡 Show Solution"):
                st.write(task.get('solution', 'No solution found.'))
        
        if st.button("🏳️ Reset Session"):
            st.session_state.user_details = {}
            st.rerun()

# --- 9. Main App Logic ---

# Check if user is onboarded
if not st.session_state.onboarded or not st.session_state.user_name:
    render_onboarding()
else:
    # Load user data if not loaded
    if not st.session_state.user_db_data:
        load_user_data()
    
    # Sidebar with Progress & Daily Goal
    with st.sidebar:
        st.title("🧠 BrainWash")
        st.write(f"Hello, **{st.session_state.user_name}**!")
        
        if st.session_state.user_db_data:
            user_data = st.session_state.user_db_data
            (lvl_xp, lvl_title, _), next_limit = get_brain_status(user_data['total_xp'])
            st.write(f"Rank: **{lvl_title}**")
            prog = min((user_data['total_xp'] - lvl_xp) / (next_limit - lvl_xp), 1.0)
            st.progress(prog)
            
            st.divider()
            
            # Daily Goal
            render_daily_goal()
            
            st.divider()
        
        page = st.radio("Menu", ["Arcade", "Profile", "Insights"])
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # Router
    if page == "Arcade": 
        render_arcade()
    elif page == "Profile":
        render_profile()
    else:
        render_insights()
