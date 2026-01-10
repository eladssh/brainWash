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
import io
import hashlib

# --- 1. Database Setup ---
DB_PATH = Path("brainwash.db")

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initialize SQLite database with User and TaskCompletion tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User table with password
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
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
            user_answer TEXT,
            ai_feedback TEXT,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    conn.commit()
    conn.close()

def create_user(username, password, onboarding_data=None):
    """Create new user with hashed password"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO User (username, password_hash, subjects_interested, learning_style, weekly_commitment, daily_goal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            hash_password(password),
            onboarding_data.get('subjects', '') if onboarding_data else '',
            onboarding_data.get('style', '') if onboarding_data else '',
            onboarding_data.get('commitment', 3) if onboarding_data else 3,
            onboarding_data.get('daily_goal', 3) if onboarding_data else 3
        ))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    
    conn.close()
    return success

def verify_login(username, password):
    """Verify username and password"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash FROM User WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] == hash_password(password):
        return True
    return False

def get_user(username):
    """Get user data by username"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def user_exists(username):
    """Check if username exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

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

def update_user_profile(username, subjects, learning_style, weekly_commitment, daily_goal):
    """Update user learning preferences"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE User 
        SET subjects_interested = ?, learning_style = ?, weekly_commitment = ?, daily_goal = ?
        WHERE username = ?
    """, (subjects, learning_style, weekly_commitment, daily_goal, username))
    conn.commit()
    conn.close()

def log_task_completion(username, task_text, difficulty, xp_earned, subject, topic, user_answer="", ai_feedback=""):
    """Log a completed task with optional answer and feedback"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user:
        cursor.execute("""
            INSERT INTO TaskCompletion (user_id, task_text, difficulty, xp_earned, subject, topic, user_answer, ai_feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user[0], task_text, difficulty, xp_earned, subject, topic, user_answer, ai_feedback))
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
    
    # All tasks for export
    cursor.execute("""
        SELECT completed_at, subject, topic, task_text, difficulty, xp_earned
        FROM TaskCompletion
        WHERE user_id = ?
        ORDER BY completed_at DESC
    """, (user_id,))
    all_tasks = cursor.fetchall()
    
    conn.close()
    
    return {
        'daily_tasks': daily_tasks,
        'daily_xp': daily_xp,
        'difficulty_breakdown': difficulty_breakdown,
        'subject_stats': subject_stats,
        'recent_tasks': recent_tasks,
        'all_tasks': all_tasks
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
        max-width: 700px;
        margin: 30px auto;
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
    
    .login-container {
        background: white;
        padding: 50px;
        border-radius: 25px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        max-width: 500px;
        margin: 80px auto;
        text-align: center;
    }
    
    .feature-box {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        margin: 15px 0;
        border-left: 4px solid #7F00FF;
    }
    
    .showcase-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
    }
    
    .subject-tag {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        margin: 5px;
        font-size: 0.9em;
    }
    
    .answer-feedback {
        padding: 15px;
        border-radius: 10px;
        margin-top: 10px;
        border-left: 4px solid;
    }
    
    .feedback-correct {
        background: #e8f5e9;
        border-color: #66bb6a;
        color: #2e7d32;
    }
    
    .feedback-partial {
        background: #fff3e0;
        border-color: #ffa726;
        color: #e65100;
    }
    
    .feedback-incorrect {
        background: #ffebee;
        border-color: #ff4b4b;
        color: #c62828;
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

def check_answer(task_text, solution, user_answer):
    """Use AI to check if user's answer is correct"""
    prompt = f"""
    Task: {task_text}
    Expected Solution: {solution}
    User's Answer: {user_answer}
    
    Evaluate if the user's answer is correct or close to the expected solution.
    Return ONLY JSON with this format:
    {{
        "is_correct": true/false,
        "score": 0-100,
        "feedback": "brief feedback message",
        "status": "correct"/"partial"/"incorrect"
    }}
    
    Score guidelines:
    - 90-100: Fully correct
    - 60-89: Partially correct
    - 0-59: Incorrect
    """
    
    res = get_ai_response(prompt, is_json=True)
    if res:
        try:
            return json.loads(res)
        except:
            return {
                "is_correct": False,
                "score": 0,
                "feedback": "Could not evaluate answer",
                "status": "incorrect"
            }
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
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "onboarded" not in st.session_state: st.session_state.onboarded = False
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "user_details" not in st.session_state: st.session_state.user_details = {}
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_db_data" not in st.session_state: st.session_state.user_db_data = None
if "answer_mode" not in st.session_state: st.session_state.answer_mode = True  # Default to answer mode

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
        user = get_user(st.session_state.user_name)
        if user:
            st.session_state.user_db_data = {
                'id': user[0],
                'username': user[1],
                'total_xp': user[3],
                'tasks_completed': user[4],
                'daily_goal': user[5],
                'streak_days': user[6],
                'last_activity_date': user[7],
                'subjects_interested': user[9],
                'learning_style': user[10],
                'weekly_commitment': user[11]
            }

# --- 5. Login Page ---
def render_login():
    st.markdown("""
        <div class="login-container">
            <div class="brain-avatar">🧠</div>
            <h1 style="color: #7F00FF; margin-bottom: 10px;">BrainWash: Arcade</h1>
            <p style="color: #666; margin-bottom: 40px;">Gamify Your Learning Journey</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "✨ Register"])
    
    with tab1:
        st.markdown("### Welcome Back!")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("🚀 Enter Arcade", use_container_width=True, type="primary")
            
            if login_btn:
                if not username or not password:
                    st.error("Please enter both username and password!")
                elif verify_login(username, password):
                    st.session_state.user_name = username
                    st.session_state.authenticated = True
                    st.session_state.onboarded = True
                    load_user_data()
                    st.success(f"Welcome back, {username}! 🎮")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid username or password!")
    
    with tab2:
        st.markdown("### Create Your Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username", placeholder="brain_master_2024")
            new_password = st.text_input("Choose a Password", type="password", placeholder="Min 6 characters")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            signup_btn = st.form_submit_button("🎯 Create Account", use_container_width=True, type="primary")
            
            if signup_btn:
                if not new_username or not new_password:
                    st.error("Please fill in all fields!")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long!")
                elif new_password != confirm_password:
                    st.error("Passwords do not match!")
                elif user_exists(new_username):
                    st.error("Username already exists! Please choose a different one.")
                else:
                    # Create user without onboarding data - will be added in onboarding
                    if create_user(new_username, new_password):
                        st.session_state.user_name = new_username
                        st.session_state.authenticated = True
                        st.session_state.onboarded = False
                        st.success(f"Account created! Let's set up your profile, {new_username}! 🎉")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")

# --- 6. Enhanced Onboarding ---
def render_onboarding():
    st.markdown("""
        <div class="onboarding-container">
            <h1 style="text-align: center; color: #7F00FF; margin-bottom: 10px;">
                🎮 Welcome to BrainWash Arcade!
            </h1>
            <p style="text-align: center; color: #666; font-size: 1.1em; margin-bottom: 30px;">
                Transform boring study materials into epic quests
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # System Showcase
    with st.expander("🌟 What Makes BrainWash Special?", expanded=True):
        st.markdown("""
            <div class="showcase-section">
                <h3>🎯 Gamification That Actually Works</h3>
                <p>We've turned studying into an RPG-style adventure. Every topic becomes a mission, every completed task earns XP, and your progress unlocks achievements and brain levels!</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div class="feature-box">
                    <h4>🤖 AI-Powered Answer Checking</h4>
                    <p>Write your own answers and get instant AI feedback! Our system evaluates your responses and helps you learn from mistakes.</p>
                </div>
                
                <div class="feature-box">
                    <h4>📊 Smart Analytics</h4>
                    <p>Track your learning patterns with detailed insights: daily progress, subject distribution, difficulty trends, and more!</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div class="feature-box">
                    <h4>🎯 Daily Goals & Streaks</h4>
                    <p>Set personalized daily targets and build consistency with streak tracking. Stay motivated every single day!</p>
                </div>
                
                <div class="feature-box">
                    <h4>📈 Progress Persistence</h4>
                    <p>All your data is saved securely. Your XP, achievements, and task history stay with you forever.</p>
                </div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    # Setup Form
    st.markdown("### 🎯 Let's Personalize Your Experience")
    
    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subjects = st.text_area(
                "📚 What subjects are you studying?",
                placeholder="e.g., Mathematics, Physics, Programming, History",
                help="Separate multiple subjects with commas",
                height=100
            )
            
            learning_style = st.selectbox(
                "🎨 Your learning style?",
                ["Visual (diagrams, videos)", "Auditory (lectures, discussions)", 
                 "Reading/Writing (notes, articles)", "Kinesthetic (hands-on practice)"],
                help="We'll tailor tasks to match your style"
            )
        
        with col2:
            weekly_commitment = st.slider(
                "⏰ Weekly study hours?",
                min_value=1, max_value=40, value=10,
                help="This helps us understand your availability"
            )
            
            daily_goal = st.slider(
                "🎯 Daily task goal?",
                min_value=1, max_value=20, value=3,
                help="Start small! You can adjust this later"
            )
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "🚀 Launch My Learning Journey!", 
                use_container_width=True, 
                type="primary"
            )
        
        if submitted:
            if not subjects:
                st.error("Please enter at least one subject!")
            else:
                # Update user preferences
                update_user_profile(
                    st.session_state.user_name,
                    subjects,
                    learning_style,
                    weekly_commitment,
                    daily_goal
                )
                
                st.session_state.onboarded = True
                load_user_data()
                st.balloons()
                st.success(f"🎉 All set, {st.session_state.user_name}! Let's start learning!")
                time.sleep(1.5)
                st.rerun()

# --- 7. Daily Goal Widget ---
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

# --- 8. Insights Dashboard ---
def render_insights():
    st.title("📊 Learning Insights")
    
    if not st.session_state.user_db_data:
        st.warning("No data available yet. Complete some tasks to see your insights!")
        return
    
    analytics = get_user_analytics(st.session_state.user_name)
    
    if not analytics:
        st.warning("No analytics data available yet.")
        return
    
    # Export Button
    col1, col2, col3 = st.columns([2, 1, 1])
    with col3:
        if st.button("📤 Export to CSV", use_container_width=True):
            if analytics['all_tasks']:
                df = pd.DataFrame(
                    analytics['all_tasks'],
                    columns=['Completed At', 'Subject', 'Topic', 'Task', 'Difficulty', 'XP Earned']
                )
                csv = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"brainwash_data_{st.session_state.user_name}_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.success("✅ CSV ready for download!")
            else:
                st.info("No data to export yet!")
    
    st.divider()
    
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

# --- 9. Profile ---
def render_profile():
    st.title("👤 Brain Profile")
    
    if not st.session_state.user_db_data:
        st.error("User data not loaded!")
        return
    
    user_data = st.session_state.user_db_data
    
    # Editable Learning Preferences
    with st.expander("📝 Edit Learning Preferences", expanded=False):
        with st.form("edit_profile"):
            new_subjects = st.text_area(
                "Subjects", 
                value=user_data['subjects_interested'],
                help="Separate with commas"
            )
            new_style = st.selectbox(
                "Learning Style",
                ["Visual (diagrams, videos)", "Auditory (lectures, discussions)", 
                 "Reading/Writing (notes, articles)", "Kinesthetic (hands-on practice)"],
                index=["Visual (diagrams, videos)", "Auditory (lectures, discussions)", 
                       "Reading/Writing (notes, articles)", "Kinesthetic (hands-on practice)"].index(user_data['learning_style'])
            )
            new_commitment = st.slider(
                "Weekly Commitment (hours)",
                min_value=1, max_value=40, 
                value=user_data['weekly_commitment']
            )
            new_goal = st.slider(
                "Daily Goal (tasks)",
                min_value=1, max_value=20, 
                value=user_data['daily_goal']
            )
            
            if st.form_submit_button("💾 Save Changes", type="primary"):
                update_user_profile(
                    st.session_state.user_name,
                    new_subjects,
                    new_style,
                    new_commitment,
                    new_goal
                )
                load_user_data()
                st.success("✅ Profile updated!")
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
                    <div class="stat-box"><strong>Learning Style:</strong> {user_data['learning_style'].split('(')[0]}</div>
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

# --- 10. Arcade ---
def render_arcade():
    if not st.session_state.user_db_data:
        st.error("User data not loaded!")
        return
    
    user_data = st.session_state.user_db_data
    
    # Intro Banner with Subject Preferences
    subjects_list = [s.strip() for s in user_data['subjects_interested'].split(',') if s.strip()]
    subjects_html = ''.join([f'<span class="subject-tag">{s}</span>' for s in subjects_list])
    
    st.markdown(f"""
        <div class="intro-banner">
            <h2>Welcome to BrainWash Arcade 🎮</h2>
            <p>Turn study materials into active quests. Earn XP, unlock ranks, and master subjects!</p>
            <div style="margin-top: 15px;">
                <strong>Your Interests:</strong><br>
                {subjects_html if subjects_html else '<em>No subjects set yet</em>'}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Progress Bar Header
    (lvl_xp, lvl_title, _), next_limit = get_brain_status(user_data['total_xp'])
    prog = min((user_data['total_xp'] - lvl_xp) / (next_limit - lvl_xp), 1.0)
    st.write(f"**Rank:** {lvl_title} ({user_data['total_xp']} XP)")
    st.progress(prog)
    
    # Answer Mode Toggle
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        answer_mode = st.toggle(
            "✍️ Answer Mode (Write & Check Answers)", 
            value=st.session_state.answer_mode,
            help="When enabled, you can write your answers and get AI feedback"
        )
        st.session_state.answer_mode = answer_mode

    if not st.session_state.user_details:
        # User context for AI
        user_context = f"Subjects: {user_data['subjects_interested']}, Learning style: {user_data['learning_style']}"
        
        # Get user's first subject as default
        subjects_list = [s.strip() for s in user_data['subjects_interested'].split(',') if s.strip()]
        default_subject = subjects_list[0] if subjects_list else "Math"
        
        t1, t2 = st.tabs(["🔍 Subject Search", "📄 PDF Scan"])
        with t1:
            with st.form("manual"):
                sub = st.text_input("Subject", default_subject)
                top = st.text_input("Topic", "")
                if st.form_submit_button("Start Mission"):
                    plan = get_initial_plan(sub, top, user_context=user_context)
                    if plan:
                        st.session_state.current_tasks = plan['tasks']
                        st.session_state.user_details = {"sub": sub, "top": top}
                        st.rerun()
        with t2:
            with st.form("pdf"):
                sub_p = st.text_input("Subject", default_subject)
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
            
            # Answer Mode
            if st.session_state.answer_mode:
                with st.form(f"answer_form_{i}"):
                    user_answer = st.text_area(
                        "✍️ Your Answer:",
                        placeholder="Write your answer here...",
                        height=100,
                        key=f"answer_{i}"
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    submit_answer = col1.form_submit_button("✅ Submit Answer", type="primary", use_container_width=True)
                    
                    if submit_answer and user_answer.strip():
                        with st.spinner("🤖 AI is checking your answer..."):
                            result = check_answer(task['text'], task.get('solution', ''), user_answer)
                            
                            if result:
                                feedback_class = f"feedback-{result['status']}"
                                status_emoji = {"correct": "🎉", "partial": "👍", "incorrect": "❌"}
                                
                                st.markdown(f"""
                                    <div class="answer-feedback {feedback_class}">
                                        <strong>{status_emoji.get(result['status'], '💭')} {result['feedback']}</strong><br>
                                        <small>Score: {result['score']}/100</small>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Award XP based on score
                                earned_xp = int(xp * (result['score'] / 100))
                                
                                if result['score'] >= 60:  # Partial credit threshold
                                    update_user_stats(st.session_state.user_name, xp_gained=earned_xp, task_completed=True)
                                    log_task_completion(
                                        st.session_state.user_name,
                                        task['text'],
                                        d,
                                        earned_xp,
                                        st.session_state.user_details['sub'],
                                        st.session_state.user_details['top'],
                                        user_answer,
                                        result['feedback']
                                    )
                                    load_user_data()
                                    
                                    st.success(f"🎊 Earned {earned_xp} XP!")
                                    
                                    # Generate new task
                                    with st.spinner("Generating new task..."):
                                        new = get_new_task_json(
                                            st.session_state.user_details['sub'], 
                                            st.session_state.user_details['top'], 
                                            d,
                                            user_context=user_context
                                        )
                                        st.session_state.current_tasks[i] = {**new, "difficulty": d, "xp": xp}
                                    
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.info("💪 Keep trying! You can reroll or try a different approach.")
            
            else:
                # Regular mode (quick complete)
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
                        else:
                            st.error("Not enough XP to reroll!")
            
            # Reroll button for Answer Mode
            if st.session_state.answer_mode:
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
                    else:
                        st.error("Not enough XP to reroll!")
            
            with st.expander("💡 Show Solution"):
                st.write(task.get('solution', 'No solution found.'))
        
        if st.button("🏳️ Reset Session"):
            st.session_state.user_details = {}
            st.rerun()

# --- 11. Main App Logic ---

# Check authentication
if not st.session_state.authenticated:
    render_login()
elif not st.session_state.onboarded:
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
