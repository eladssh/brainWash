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
from collections import defaultdict
import numpy as np

# --- 1. ADVANCED DATABASE SCHEMA ---
DB_PATH = Path("brainwash_advanced.db")

def init_database():
    """Initialize comprehensive database schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # User table with onboarding data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            total_xp INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_activity_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            -- Onboarding data
            subjects_interested TEXT,
            learning_style TEXT,
            weekly_hours_available INTEGER DEFAULT 10,
            motivation_level TEXT DEFAULT 'Medium',
            self_assessed_skill TEXT DEFAULT 'Intermediate',
            urgency_level TEXT DEFAULT 'Moderate',
            -- Adaptive settings
            xp_multiplier REAL DEFAULT 1.0,
            reroll_cost INTEGER DEFAULT 20,
            unlocked_features TEXT DEFAULT '[]'
        )
    """)
    
    # Goals table - goals as first-class entities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Goal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_type TEXT NOT NULL, -- 'daily' or 'weekly'
            target_tasks INTEGER NOT NULL,
            target_xp INTEGER,
            target_focus_minutes INTEGER,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            status TEXT DEFAULT 'active', -- active, completed, failed
            actual_tasks INTEGER DEFAULT 0,
            actual_xp INTEGER DEFAULT 0,
            actual_focus_minutes INTEGER DEFAULT 0,
            completion_rate REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            adjustment_reason TEXT,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    # Task lifecycle tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            xp_value INTEGER NOT NULL,
            subject TEXT,
            topic TEXT,
            state TEXT DEFAULT 'new', -- new, in_progress, completed, skipped, failed
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            time_spent_seconds INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            solution TEXT,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    # Task completions with behavioral data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TaskCompletion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            xp_earned INTEGER NOT NULL,
            xp_multiplier REAL DEFAULT 1.0,
            subject TEXT,
            topic TEXT,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            time_to_complete_seconds INTEGER,
            attempts_made INTEGER DEFAULT 1,
            solution_viewed BOOLEAN DEFAULT 0,
            focus_session_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES User(id),
            FOREIGN KEY (task_id) REFERENCES Task(id),
            FOREIGN KEY (focus_session_id) REFERENCES FocusSession(id)
        )
    """)
    
    # Focus sessions as measurable data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS FocusSession (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            interruptions INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            xp_earned INTEGER DEFAULT 0,
            efficiency_score REAL, -- XP per minute
            session_quality TEXT, -- excellent, good, average, poor
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    # Task state transitions (for behavioral analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TaskStateTransition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            from_state TEXT,
            to_state TEXT NOT NULL,
            reason TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES Task(id)
        )
    """)
    
    # Goal adjustments log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GoalAdjustment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            old_daily_target INTEGER,
            new_daily_target INTEGER,
            adjustment_type TEXT, -- increase, decrease, maintain
            reason TEXT,
            performance_trend TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    # Achievements with behavioral requirements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Achievement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_type TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reward_type TEXT, -- xp_multiplier, reroll_discount, feature_unlock
            reward_value TEXT,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    # KPI tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS KPI (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            learning_efficiency REAL, -- XP per focus minute
            task_completion_rate REAL,
            avg_task_time_seconds REAL,
            focus_quality_score REAL,
            consistency_score REAL,
            FOREIGN KEY (user_id) REFERENCES User(id)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

# --- 2. DATA ACCESS LAYER ---

class UserDataManager:
    """Manages all user data operations"""
    
    @staticmethod
    def create_user(username, onboarding_data):
        """Create new user with onboarding data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO User (
                username, subjects_interested, learning_style,
                weekly_hours_available, motivation_level,
                self_assessed_skill, urgency_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            onboarding_data.get('subjects', ''),
            onboarding_data.get('learning_style', 'Visual'),
            onboarding_data.get('weekly_hours', 10),
            onboarding_data.get('motivation_level', 'Medium'),
            onboarding_data.get('skill_level', 'Intermediate'),
            onboarding_data.get('urgency', 'Moderate')
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Create initial goals
        GoalManager.create_initial_goals(user_id, onboarding_data)
        
        conn.close()
        return user_id
    
    @staticmethod
    def get_user(username):
        """Get user data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    @staticmethod
    def user_exists(username):
        """Check if user exists"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM User WHERE username = ?", (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    @staticmethod
    def update_xp_and_streak(username, xp_gained, multiplier=1.0):
        """Update XP and streak"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, total_xp, current_streak, longest_streak, last_activity_date
            FROM User WHERE username = ?
        """, (username,))
        user = cursor.fetchone()
        
        if user:
            user_id, current_xp, streak, longest, last_date = user
            new_xp = current_xp + int(xp_gained * multiplier)
            
            today = str(date.today())
            new_streak = streak
            
            if last_date != today:
                if last_date == str(date.today() - timedelta(days=1)):
                    new_streak = streak + 1
                else:
                    new_streak = 1
            
            new_longest = max(new_streak, longest or 0)
            
            cursor.execute("""
                UPDATE User 
                SET total_xp = ?, current_streak = ?, longest_streak = ?,
                    last_activity_date = ?
                WHERE username = ?
            """, (new_xp, new_streak, new_longest, today, username))
            
            conn.commit()
        
        conn.close()

class GoalManager:
    """Manages adaptive goal system"""
    
    @staticmethod
    def create_initial_goals(user_id, onboarding_data):
        """Create initial daily/weekly goals based on onboarding"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Calculate initial targets from onboarding
        weekly_hours = onboarding_data.get('weekly_hours', 10)
        motivation = onboarding_data.get('motivation_level', 'Medium')
        urgency = onboarding_data.get('urgency', 'Moderate')
        
        # Base daily tasks
        base_tasks = 3
        if motivation == 'High' or urgency == 'Urgent':
            base_tasks = 5
        elif motivation == 'Low':
            base_tasks = 2
        
        # Daily goal
        today = date.today()
        cursor.execute("""
            INSERT INTO Goal (
                user_id, goal_type, target_tasks, target_xp, target_focus_minutes,
                period_start, period_end, status
            ) VALUES (?, 'daily', ?, ?, ?, ?, ?, 'active')
        """, (user_id, base_tasks, base_tasks * 100, 25, str(today), str(today), 'active'))
        
        # Weekly goal
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        cursor.execute("""
            INSERT INTO Goal (
                user_id, goal_type, target_tasks, target_xp, target_focus_minutes,
                period_start, period_end, status
            ) VALUES (?, 'weekly', ?, ?, ?, ?, ?, 'active')
        """, (user_id, base_tasks * 5, base_tasks * 500, weekly_hours * 60 // 2, 
              str(week_start), str(week_end), 'active'))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_active_goals(user_id):
        """Get current active goals"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = str(date.today())
        cursor.execute("""
            SELECT * FROM Goal 
            WHERE user_id = ? AND status = 'active'
            AND period_start <= ? AND period_end >= ?
            ORDER BY goal_type
        """, (user_id, today, today))
        
        goals = cursor.fetchall()
        conn.close()
        return goals
    
    @staticmethod
    def update_goal_progress(user_id, tasks_increment=0, xp_increment=0, focus_minutes_increment=0):
        """Update goal progress"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = str(date.today())
        cursor.execute("""
            UPDATE Goal 
            SET actual_tasks = actual_tasks + ?,
                actual_xp = actual_xp + ?,
                actual_focus_minutes = actual_focus_minutes + ?
            WHERE user_id = ? AND status = 'active'
            AND period_start <= ? AND period_end >= ?
        """, (tasks_increment, xp_increment, focus_minutes_increment, user_id, today, today))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def evaluate_and_adjust_goals(user_id):
        """Evaluate completed goals and adjust future targets adaptively"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get last 7 daily goals
        cursor.execute("""
            SELECT target_tasks, actual_tasks, completion_rate
            FROM Goal
            WHERE user_id = ? AND goal_type = 'daily'
            AND status IN ('completed', 'failed')
            ORDER BY period_end DESC
            LIMIT 7
        """, (user_id,))
        
        recent_goals = cursor.fetchall()
        
        if len(recent_goals) < 3:
            conn.close()
            return None  # Not enough data yet
        
        # Calculate success rate
        success_count = sum(1 for g in recent_goals if (g[1] or 0) >= (g[0] or 1))
        success_rate = success_count / len(recent_goals)
        
        # Get current daily target
        cursor.execute("""
            SELECT target_tasks FROM Goal
            WHERE user_id = ? AND goal_type = 'daily' AND status = 'active'
            LIMIT 1
        """, (user_id,))
        
        current = cursor.fetchone()
        if not current:
            conn.close()
            return None
        
        current_target = current[0]
        new_target = current_target
        adjustment_type = 'maintain'
        reason = ''
        
        # Adaptive logic
        if success_rate >= 0.85:  # Consistent overachievement
            new_target = min(current_target + 1, 20)
            adjustment_type = 'increase'
            reason = f'High success rate ({success_rate:.0%}). Ready for more challenge.'
        elif success_rate <= 0.3:  # Consistent failure
            new_target = max(current_target - 1, 1)
            adjustment_type = 'decrease'
            reason = f'Low success rate ({success_rate:.0%}). Reducing target to build consistency.'
        else:
            reason = f'Moderate success rate ({success_rate:.0%}). Maintaining current target.'
        
        # Log adjustment
        if new_target != current_target:
            cursor.execute("""
                INSERT INTO GoalAdjustment (
                    user_id, old_daily_target, new_daily_target,
                    adjustment_type, reason, performance_trend
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, current_target, new_target, adjustment_type, reason, 
                  f'{success_rate:.0%} success'))
            
            conn.commit()
        
        conn.close()
        return {
            'old_target': current_target,
            'new_target': new_target,
            'adjustment_type': adjustment_type,
            'reason': reason,
            'success_rate': success_rate
        }
    
    @staticmethod
    def finalize_period_goals(user_id):
        """Finalize goals at end of period"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = str(date.today())
        
        # Find expired active goals
        cursor.execute("""
            SELECT id, target_tasks, actual_tasks, target_xp, actual_xp
            FROM Goal
            WHERE user_id = ? AND status = 'active' AND period_end < ?
        """, (user_id, today))
        
        expired_goals = cursor.fetchall()
        
        for goal_id, target_tasks, actual_tasks, target_xp, actual_xp in expired_goals:
            completion_rate = (actual_tasks or 0) / max(target_tasks, 1)
            status = 'completed' if completion_rate >= 0.8 else 'failed'
            
            cursor.execute("""
                UPDATE Goal
                SET status = ?, completion_rate = ?, completed_at = ?
                WHERE id = ?
            """, (status, completion_rate, today, goal_id))
        
        conn.commit()
        conn.close()
        
        # Trigger adaptive adjustment
        if expired_goals:
            return GoalManager.evaluate_and_adjust_goals(user_id)
        return None

class TaskManager:
    """Manages task lifecycle and state transitions"""
    
    @staticmethod
    def create_task(user_id, task_data, subject, topic):
        """Create new task"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Task (
                user_id, task_text, difficulty, xp_value,
                subject, topic, solution, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
        """, (
            user_id,
            task_data['text'],
            task_data['difficulty'],
            task_data['xp'],
            subject,
            topic,
            task_data.get('solution', '')
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    @staticmethod
    def transition_task_state(task_id, new_state, reason=None):
        """Record task state transition"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current state
        cursor.execute("SELECT state FROM Task WHERE id = ?", (task_id,))
        current = cursor.fetchone()
        
        if current:
            old_state = current[0]
            
            # Update task state
            update_fields = ["state = ?"]
            update_values = [new_state]
            
            if new_state == 'in_progress' and old_state == 'new':
                update_fields.append("started_at = ?")
                update_values.append(datetime.now().isoformat())
            elif new_state == 'completed':
                update_fields.append("completed_at = ?")
                update_values.append(datetime.now().isoformat())
            
            update_values.append(task_id)
            
            cursor.execute(f"""
                UPDATE Task SET {', '.join(update_fields)} WHERE id = ?
            """, update_values)
            
            # Log transition
            cursor.execute("""
                INSERT INTO TaskStateTransition (task_id, from_state, to_state, reason)
                VALUES (?, ?, ?, ?)
            """, (task_id, old_state, new_state, reason))
            
            conn.commit()
        
        conn.close()
    
    @staticmethod
    def complete_task(task_id, user_id, xp_earned, multiplier, time_spent, solution_viewed):
        """Complete task and record completion data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get task details
        cursor.execute("""
            SELECT task_text, difficulty, xp_value, subject, topic, attempts
            FROM Task WHERE id = ?
        """, (task_id,))
        
        task = cursor.fetchone()
        
        if task:
            task_text, difficulty, xp_value, subject, topic, attempts = task
            
            # Update task
            cursor.execute("""
                UPDATE Task
                SET state = 'completed', completed_at = ?, time_spent_seconds = ?, attempts = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), time_spent, attempts + 1, task_id))
            
            # Record completion
            cursor.execute("""
                INSERT INTO TaskCompletion (
                    user_id, task_id, task_text, difficulty, xp_earned,
                    xp_multiplier, subject, topic, time_to_complete_seconds,
                    attempts_made, solution_viewed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, task_id, task_text, difficulty, xp_earned, multiplier,
                  subject, topic, time_spent, attempts + 1, solution_viewed))
            
            conn.commit()
        
        conn.close()

class FocusSessionManager:
    """Manages focus sessions"""
    
    @staticmethod
    def start_session(user_id, duration_minutes):
        """Start new focus session"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO FocusSession (user_id, duration_minutes, started_at)
            VALUES (?, ?, ?)
        """, (user_id, duration_minutes, datetime.now().isoformat()))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id
    
    @staticmethod
    def complete_session(session_id, tasks_completed, xp_earned, interruptions=0):
        """Complete focus session and calculate efficiency"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, duration_minutes, started_at
            FROM FocusSession WHERE id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        
        if session:
            user_id, duration, started = session
            efficiency = xp_earned / max(duration, 1)
            
            # Quality assessment
            if efficiency >= 15 and interruptions == 0:
                quality = 'excellent'
            elif efficiency >= 10:
                quality = 'good'
            elif efficiency >= 5:
                quality = 'average'
            else:
                quality = 'poor'
            
            cursor.execute("""
                UPDATE FocusSession
                SET completed_at = ?, interruptions = ?, tasks_completed = ?,
                    xp_earned = ?, efficiency_score = ?, session_quality = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), interruptions, tasks_completed,
                  xp_earned, efficiency, quality, session_id))
            
            conn.commit()
        
        conn.close()

class AnalyticsEngine:
    """Advanced analytics and insights generation"""
    
    @staticmethod
    def calculate_learning_efficiency(user_id, days=7):
        """Calculate XP per focus minute"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cutoff = str(date.today() - timedelta(days=days))
        
        cursor.execute("""
            SELECT SUM(xp_earned), SUM(duration_minutes)
            FROM FocusSession
            WHERE user_id = ? AND DATE(started_at) >= ? AND completed_at IS NOT NULL
        """, (user_id, cutoff))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[1]:
            return result[0] / result[1]
        return 0.0
    
    @staticmethod
    def generate_behavioral_insights(user_id):
        """Generate textual insights from behavioral data"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        insights = []
        
        # Insight 1: Difficulty preference
        cursor.execute("""
            SELECT difficulty, COUNT(*) as count, AVG(time_to_complete_seconds) as avg_time
            FROM TaskCompletion
            WHERE user_id = ?
            GROUP BY difficulty
            ORDER BY count DESC
        """, (user_id,))
        
        diff_data = cursor.fetchall()
        if diff_data:
            top_diff = diff_data[0][0]
            top_count = diff_data[0][1]
            
            if len(diff_data) >= 2:
                completion_ratio = top_count / sum(d[1] for d in diff_data)
                if completion_ratio > 0.5:
                    insights.append({
                        'type': 'difficulty_preference',
                        'text': f"You complete {top_diff} tasks more consistently ({completion_ratio:.0%} of all tasks). Consider challenging yourself with more variety.",
                        'action': 'Try harder difficulties'
                    })
        
        # Insight 2: Focus session quality
        cursor.execute("""
            SELECT AVG(efficiency_score), session_quality, COUNT(*)
            FROM FocusSession
            WHERE user_id = ? AND completed_at IS NOT NULL
            GROUP BY session_quality
            ORDER BY COUNT(*) DESC
        """, (user_id,))
        
        focus_data = cursor.fetchall()
        if focus_data:
            avg_eff = focus_data[0][0]
            if avg_eff and avg_eff > 10:
                insights.append({
                    'type': 'focus_quality',
                    'text': f"Your focus sessions are highly efficient (avg {avg_eff:.1f} XP/min). Longer sessions could multiply your progress.",
                    'action': 'Increase session duration'
                })
        
        # Insight 3: Streak consistency
        cursor.execute("""
            SELECT current_streak, longest_streak
            FROM User WHERE id = ?
        """, (user_id,))
        
        streak_data = cursor.fetchone()
        if streak_data:
            current, longest = streak_data
            if current and longest and current >= longest * 0.8:
                insights.append({
                    'type': 'consistency',
                    'text': f"Amazing! You're at {current} days - near your record of {longest}. Keep this momentum!",
                    'action': 'Maintain streak'
                })
        
        # Insight 4: Time efficiency by difficulty
        cursor.execute("""
            SELECT difficulty, 
                   AVG(CAST(xp_earned AS FLOAT) / NULLIF(time_to_complete_seconds, 0)) * 60 as xp_per_min
            FROM TaskCompletion
            WHERE user_id = ? AND time_to_complete_seconds > 0
            GROUP BY difficulty
        """, (user_id,))
        
        eff_by_diff = cursor.fetchall()
        if len(eff_by_diff) >= 2:
            eff_sorted = sorted(eff_by_diff, key=lambda x: x[1] or 0, reverse=True)
            best_diff = eff_sorted[0][0]
            best_rate = eff_sorted[0][1]
            
            if best_rate:
                insights.append({
                    'type': 'efficiency',
                    'text': f"{best_diff} tasks give you the best XP return ({best_rate:.1f} XP/min). This is your sweet spot!",
                    'action': f'Focus on {best_diff} tasks'
                })
        
        # Insight 5: Solution dependency
        cursor.execute("""
            SELECT AVG(CASE WHEN solution_viewed = 1 THEN 1.0 ELSE 0.0 END) * 100 as pct
            FROM TaskCompletion
            WHERE user_id = ?
        """, (user_id,))
        
        solution_pct = cursor.fetchone()[0]
        if solution_pct and solution_pct > 60:
            insights.append({
                'type': 'learning_approach',
                'text': f"You view solutions {solution_pct:.0f}% of the time. Try solving independently first for deeper learning.",
                'action': 'Reduce solution viewing'
            })
        
        conn.close()
        return insights
    
    @staticmethod
    def calculate_kpis(user_id):
        """Calculate key performance indicators"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        today = str(date.today())
        
        # Learning efficiency
        efficiency = AnalyticsEngine.calculate_learning_efficiency(user_id, days=7)
        
        # Task completion rate (vs attempts)
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN state = 'completed' THEN 1 END) * 1.0 / COUNT(*) as rate
            FROM Task
            WHERE user_id = ? AND DATE(created_at) >= DATE('now', '-7 days')
        """, (user_id,))
        
        completion_rate = cursor.fetchone()[0] or 0
        
        # Average task time
        cursor.execute("""
            SELECT AVG(time_to_complete_seconds)
            FROM TaskCompletion
            WHERE user_id = ? AND DATE(completed_at) >= DATE('now', '-7 days')
        """, (user_id,))
        
        avg_time = cursor.fetchone()[0] or 0
        
        # Focus quality
        cursor.execute("""
            SELECT AVG(efficiency_score)
            FROM FocusSession
            WHERE user_id = ? AND DATE(started_at) >= DATE('now', '-7 days')
            AND completed_at IS NOT NULL
        """, (user_id,))
        
        focus_quality = cursor.fetchone()[0] or 0
        
        # Consistency (tasks per day)
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(completed_at))
            FROM TaskCompletion
            WHERE user_id = ? AND DATE(completed_at) >= DATE('now', '-7 days')
        """, (user_id,))
        
        active_days = cursor.fetchone()[0] or 0
        consistency = active_days / 7.0
        
        # Store KPI
        cursor.execute("""
            INSERT INTO KPI (
                user_id, date, learning_efficiency, task_completion_rate,
                avg_task_time_seconds, focus_quality_score, consistency_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, today, efficiency, completion_rate, avg_time, focus_quality, consistency))
        
        conn.commit()
        conn.close()
        
        return {
            'learning_efficiency': efficiency,
            'completion_rate': completion_rate,
            'avg_task_time': avg_time,
            'focus_quality': focus_quality,
            'consistency': consistency
        }

class AchievementSystem:
    """Behavioral-based achievement system"""
    
    ACHIEVEMENTS_CONFIG = [
        {
            'id': 'efficiency_master',
            'name': 'Efficiency Master',
            'emoji': '⚡',
            'requirement': lambda data: data.get('learning_efficiency', 0) >= 12,
            'reward_type': 'xp_multiplier',
            'reward_value': '1.2',
            'description': 'Maintain 12+ XP/min efficiency'
        },
        {
            'id': 'consistency_king',
            'name': 'Consistency King',
            'emoji': '👑',
            'requirement': lambda data: data.get('current_streak', 0) >= 7,
            'reward_type': 'reroll_discount',
            'reward_value': '50',
            'description': '7-day streak'
        },
        {
            'id': 'balanced_learner',
            'name': 'Balanced Learner',
            'emoji': '⚖️',
            'requirement': lambda data: AchievementSystem._check_balanced_difficulty(data['user_id']),
            'reward_type': 'xp_multiplier',
            'reward_value': '1.15',
            'description': 'Complete all difficulty levels evenly'
        },
        {
            'id': 'focus_champion',
            'name': 'Focus Champion',
            'emoji': '🎯',
            'requirement': lambda data: data.get('focus_sessions_excellent', 0) >= 5,
            'reward_type': 'feature_unlock',
            'reward_value': 'advanced_analytics',
            'description': '5 excellent focus sessions'
        }
    ]
    
    @staticmethod
    def _check_balanced_difficulty(user_id):
        """Check if user completes all difficulties relatively evenly"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT difficulty, COUNT(*) as count
            FROM TaskCompletion
            WHERE user_id = ?
            GROUP BY difficulty
        """, (user_id,))
        
        counts = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        if len(counts) < 3:
            return False
        
        values = list(counts.values())
        if not values:
            return False
        
        max_val = max(values)
        min_val = min(values)
        
        # Check if all difficulties are within 50% of each other
        return (min_val / max_val) >= 0.5 if max_val > 0 else False
    
    @staticmethod
    def check_and_award_achievements(user_id):
        """Check for new achievements and award them"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get existing achievements
        cursor.execute("""
            SELECT achievement_type FROM Achievement WHERE user_id = ?
        """, (user_id,))
        
        existing = {row[0] for row in cursor.fetchall()}
        
        # Gather user data for requirements
        cursor.execute("SELECT * FROM User WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        kpis = AnalyticsEngine.calculate_kpis(user_id)
        
        cursor.execute("""
            SELECT COUNT(*) FROM FocusSession
            WHERE user_id = ? AND session_quality = 'excellent'
        """, (user_id,))
        excellent_sessions = cursor.fetchone()[0]
        
        user_data = {
            'user_id': user_id,
            'current_streak': user_row[9] if user_row else 0,
            'learning_efficiency': kpis['learning_efficiency'],
            'focus_sessions_excellent': excellent_sessions
        }
        
        newly_earned = []
        
        for achievement in AchievementSystem.ACHIEVEMENTS_CONFIG:
            if achievement['id'] not in existing:
                if achievement['requirement'](user_data):
                    cursor.execute("""
                        INSERT INTO Achievement (
                            user_id, achievement_type, achievement_name,
                            reward_type, reward_value
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (user_id, achievement['id'], achievement['name'],
                          achievement['reward_type'], achievement['reward_value']))
                    
                    newly_earned.append(achievement)
                    
                    # Apply reward
                    if achievement['reward_type'] == 'xp_multiplier':
                        cursor.execute("""
                            UPDATE User SET xp_multiplier = ?
                            WHERE id = ?
                        """, (float(achievement['reward_value']), user_id))
                    elif achievement['reward_type'] == 'reroll_discount':
                        discount_pct = float(achievement['reward_value']) / 100
                        cursor.execute("""
                            UPDATE User SET reroll_cost = CAST(reroll_cost * ? AS INTEGER)
                            WHERE id = ?
                        """, (1 - discount_pct, user_id))
        
        conn.commit()
        conn.close()
        
        return newly_earned

# --- 3. STREAMLIT CONFIG & INIT ---
load_dotenv()
API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="BrainWash: Data-Driven Learning",
    page_icon="🧠",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .insight-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
    }
    .kpi-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        text-align: center;
    }
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
    .achievement-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 25px;
        margin: 5px;
        font-weight: bold;
    }
    .adjustment-notice {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "onboarded" not in st.session_state: st.session_state.onboarded = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "username" not in st.session_state: st.session_state.username = None
if "current_tasks" not in st.session_state: st.session_state.current_tasks = []
if "active_focus_session" not in st.session_state: st.session_state.active_focus_session = None
if "task_start_times" not in st.session_state: st.session_state.task_start_times = {}
if "solution_viewed" not in st.session_state: st.session_state.solution_viewed = set()

# AI functions
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

def get_new_task_json(subject, topic, diff, user_context="", failed_tasks_context=""):
    prompt = f"""Create one new {diff} study task for {subject}: {topic}. 
    {f'User context: {user_context}' if user_context else ''}
    {f'Avoid similar to: {failed_tasks_context}' if failed_tasks_context else ''}
    Include a brief solution. Return ONLY JSON: {{'text': '...', 'solution': '...'}}"""
    res = get_ai_response(prompt, is_json=True)
    return json.loads(res) if res else {"text": "Review materials", "solution": "No solution available."}

# --- 4. UI COMPONENTS ---

def render_login():
    """Login/Signup page"""
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h1 style="font-size: 4em;">🧠</h1>
            <h1 style="color: #7F00FF;">BrainWash: Data-Driven Learning</h1>
            <p style="color: #666; font-size: 1.2em;">Your adaptive learning companion</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Returning User", "✨ New User"])
    
    with tab1:
        with st.form("login"):
            username = st.text_input("Username")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if UserDataManager.user_exists(username):
                    user = UserDataManager.get_user(username)
                    st.session_state.user_id = user[0]
                    st.session_state.username = username
                    st.session_state.authenticated = True
                    st.session_state.onboarded = True
                    st.success(f"Welcome back, {username}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("User not found!")
    
    with tab2:
        with st.form("signup"):
            new_username = st.text_input("Choose Username")
            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                if not UserDataManager.user_exists(new_username):
                    st.session_state.username = new_username
                    st.session_state.authenticated = True
                    st.session_state.onboarded = False
                    st.success("Account created! Let's personalize your experience.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Username taken!")

def render_onboarding():
    """Enhanced onboarding for data collection"""
    st.title("🎯 Welcome to Data-Driven Learning")
    
    st.markdown("""
    BrainWash uses **adaptive algorithms** to personalize your learning experience.
    We'll use your answers to:
    - Set intelligent initial goals
    - Adjust difficulty dynamically
    - Generate personalized insights
    - Track your learning efficiency
    """)
    
    with st.form("onboarding"):
        st.subheader("📚 Learning Profile")
        
        col1, col2 = st.columns(2)
        
        with col1:
            subjects = st.text_area(
                "What are you studying?",
                placeholder="Math, Physics, Programming",
                help="We'll personalize task generation"
            )
            
            skill_level = st.select_slider(
                "Self-assessed skill level",
                options=['Beginner', 'Intermediate', 'Advanced', 'Expert'],
                value='Intermediate'
            )
            
            learning_style = st.selectbox(
                "Preferred learning style",
                ['Visual', 'Auditory', 'Reading/Writing', 'Kinesthetic']
            )
        
        with col2:
            weekly_hours = st.slider(
                "Weekly hours available",
                1, 40, 10,
                help="Used to calculate realistic goals"
            )
            
            motivation = st.select_slider(
                "Current motivation level",
                options=['Low', 'Medium', 'High'],
                value='Medium'
            )
            
            urgency = st.select_slider(
                "Learning urgency",
                options=['Relaxed', 'Moderate', 'Urgent'],
                value='Moderate'
            )
        
        st.divider()
        st.subheader("🎯 Initial Goals")
        st.info("💡 Don't worry - these will adapt based on your performance!")
        
        submitted = st.form_submit_button("🚀 Start Learning", type="primary", use_container_width=True)
        
        if submitted:
            if not subjects:
                st.error("Please enter at least one subject!")
            else:
                onboarding_data = {
                    'subjects': subjects,
                    'skill_level': skill_level,
                    'learning_style': learning_style,
                    'weekly_hours': weekly_hours,
                    'motivation_level': motivation,
                    'urgency': urgency
                }
                
                user_id = UserDataManager.create_user(st.session_state.username, onboarding_data)
                st.session_state.user_id = user_id
                st.session_state.onboarded = True
                
                st.balloons()
                st.success("✅ Profile created! Your adaptive learning journey begins now.")
                time.sleep(1)
                st.rerun()

def render_arcade():
    """Main learning interface"""
    st.title("🎮 Learning Arcade")
    
    # Check for goal adjustments
    adjustment = GoalManager.finalize_period_goals(st.session_state.user_id)
    if adjustment and adjustment['adjustment_type'] != 'maintain':
        st.markdown(f"""
            <div class="adjustment-notice">
                <strong>🎯 Goal Adjusted!</strong><br>
                {adjustment['reason']}<br>
                New daily target: <strong>{adjustment['new_target']} tasks</strong>
            </div>
        """, unsafe_allow_html=True)
    
    # Display active goals
    goals = GoalManager.get_active_goals(st.session_state.user_id)
    
    if goals:
        st.subheader("🎯 Active Goals")
        cols = st.columns(len(goals))
        
        for i, goal in enumerate(goals):
            with cols[i]:
                goal_type = goal[2]
                target = goal[3]
                actual = goal[7]
                progress = min(actual / target, 1.0) if target > 0 else 0
                
                st.metric(
                    f"{goal_type.title()} Goal",
                    f"{actual}/{target} tasks",
                    f"{progress:.0%} complete"
                )
                st.progress(progress)
    
    st.divider()
    
    # Task generation
    if not st.session_state.current_tasks:
        tab1, tab2 = st.tabs(["📝 Manual Entry", "📄 PDF Upload"])
        
        with tab1:
            with st.form("manual_entry"):
                subject = st.text_input("Subject")
                topic = st.text_input("Topic")
                
                if st.form_submit_button("Generate Tasks"):
                    if subject and topic:
                        with st.spinner("Generating personalized tasks..."):
                            plan = get_initial_plan(subject, topic)
                            if plan:
                                # Create tasks in database
                                for task_data in plan['tasks']:
                                    task_id = TaskManager.create_task(
                                        st.session_state.user_id,
                                        task_data,
                                        subject,
                                        topic
                                    )
                                    task_data['id'] = task_id
                                    task_data['start_time'] = None
                                
                                st.session_state.current_tasks = plan['tasks']
                                st.success("Tasks generated!")
                                st.rerun()
        
        with tab2:
            with st.form("pdf_upload"):
                subject_pdf = st.text_input("Subject")
                uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
                
                if st.form_submit_button("Analyze & Generate"):
                    if uploaded_file and subject_pdf:
                        reader = pypdf.PdfReader(uploaded_file)
                        text = "".join([page.extract_text() for page in reader.pages])
                        
                        with st.spinner("Analyzing document..."):
                            plan = get_initial_plan(subject_pdf, uploaded_file.name, context=text)
                            if plan:
                                for task_data in plan['tasks']:
                                    task_id = TaskManager.create_task(
                                        st.session_state.user_id,
                                        task_data,
                                        subject_pdf,
                                        uploaded_file.name
                                    )
                                    task_data['id'] = task_id
                                    task_data['start_time'] = None
                                
                                st.session_state.current_tasks = plan['tasks']
                                st.success("Tasks generated from PDF!")
                                st.rerun()
    
    else:
        # Display and manage tasks
        st.subheader("📋 Your Tasks")
        
        for i, task in enumerate(st.session_state.current_tasks):
            task_id = task.get('id')
            difficulty = task['difficulty']
            xp = task['xp']
            
            st.markdown(f"""
                <div class="task-card diff-{difficulty}">
                    <strong>{difficulty}</strong> • {xp} XP<br>
                    {html.escape(task['text'])}
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("✅ Complete", key=f"complete_{i}", use_container_width=True):
                    # Calculate time spent
                    time_spent = 120  # Default 2 minutes
                    if task.get('start_time'):
                        time_spent = int((datetime.now() - task['start_time']).total_seconds())
                    
                    # Get user multiplier
                    user = UserDataManager.get_user(st.session_state.username)
                    multiplier = user[15] if user else 1.0
                    
                    # Complete task
                    xp_earned = int(xp * multiplier)
                    solution_viewed = i in st.session_state.solution_viewed
                    
                    TaskManager.complete_task(
                        task_id, st.session_state.user_id,
                        xp_earned, multiplier, time_spent, solution_viewed
                    )
                    
                    TaskManager.transition_task_state(task_id, 'completed', 'User completed')
                    
                    # Update user stats and goals
                    UserDataManager.update_xp_and_streak(st.session_state.username, xp_earned, multiplier)
                    GoalManager.update_goal_progress(st.session_state.user_id, tasks_increment=1, xp_increment=xp_earned)
                    
                    # Check achievements
                    new_achievements = AchievementSystem.check_and_award_achievements(st.session_state.user_id)
                    if new_achievements:
                        for ach in new_achievements:
                            st.success(f"🏆 Achievement Unlocked: {ach['name']} - {ach['description']}")
                    
                    # Generate new task
                    st.session_state.current_tasks.pop(i)
                    st.rerun()
            
            with col2:
                if st.button("⏭️ Skip", key=f"skip_{i}", use_container_width=True):
                    TaskManager.transition_task_state(task_id, 'skipped', 'User skipped')
                    st.session_state.current_tasks.pop(i)
                    st.rerun()
            
            with col3:
                if st.button("👁️", key=f"solution_{i}", use_container_width=True, help="View solution"):
                    st.session_state.solution_viewed.add(i)
                    TaskManager.transition_task_state(task_id, 'in_progress', 'Solution viewed')
            
            if i in st.session_state.solution_viewed:
                st.info(f"💡 Solution: {task.get('solution', 'No solution available')}")
            
            st.divider()
        
        if st.button("🔄 Reset Session"):
            st.session_state.current_tasks = []
            st.rerun()

def render_insights():
    """Advanced insights dashboard"""
    st.title("📊 Learning Insights")
    
    # Calculate latest KPIs
    kpis = AnalyticsEngine.calculate_kpis(st.session_state.user_id)
    
    # KPI Display
    st.subheader("🎯 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <h3 style="color: #7F00FF; margin: 0;">{kpis['learning_efficiency']:.2f}</h3>
                <p style="color: #666; margin: 5px 0 0 0;">Learning Efficiency<br><small>XP per minute</small></p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <h3 style="color: #ff4b4b; margin: 0;">{kpis['completion_rate']:.0%}</h3>
                <p style="color: #666; margin: 5px 0 0 0;">Completion Rate<br><small>vs attempts</small></p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="kpi-card">
                <h3 style="color: #ffa726; margin: 0;">{kpis['avg_task_time']/60:.1f}</h3>
                <p style="color: #666; margin: 5px 0 0 0;">Avg Task Time<br><small>minutes</small></p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <h3 style="color: #66bb6a; margin: 0;">{kpis['consistency']:.0%}</h3>
                <p style="color: #666; margin: 5px 0 0 0;">Weekly Consistency<br><small>active days</small></p>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Behavioral Insights
    st.subheader("🧠 Behavioral Insights")
    
    insights = AnalyticsEngine.generate_behavioral_insights(st.session_state.user_id)
    
    if insights:
        for insight in insights:
            st.markdown(f"""
                <div class="insight-card">
                    <strong>{insight['text']}</strong><br>
                    <small>💡 Suggested action: {insight['action']}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Complete more tasks to unlock personalized insights!")
    
    st.divider()
    
    # Goal Performance History
    st.subheader("📈 Goal Performance Trend")
    
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT period_start, target_tasks, actual_tasks, completion_rate, status
        FROM Goal
        WHERE user_id = ? AND goal_type = 'daily'
        ORDER BY period_start DESC
        LIMIT 14
    """
    df_goals = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))
    conn.close()
    
    if not df_goals.empty:
        df_goals = df_goals.iloc[::-1]  # Reverse for chronological order
        st.line_chart(df_goals.set_index('period_start')[['target_tasks', 'actual_tasks']])
    else:
        st.info("Goal history will appear here as you progress.")
    
    st.divider()
    
    # Export functionality
    st.subheader("📤 Export Data")
    
    if st.button("Download Complete Learning History (CSV)"):
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT 
                tc.completed_at,
                tc.subject,
                tc.topic,
                tc.task_text,
                tc.difficulty,
                tc.xp_earned,
                tc.time_to_complete_seconds,
                tc.solution_viewed
            FROM TaskCompletion tc
            WHERE tc.user_id = ?
            ORDER BY tc.completed_at DESC
        """
        df = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))
        conn.close()
        
        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                f"brainwash_data_{st.session_state.username}.csv",
                "text/csv"
            )
        else:
            st.info("No data yet!")

def render_profile():
    """User profile with achievements"""
    st.title("👤 Profile")
    
    user = UserDataManager.get_user(st.session_state.username)
    
    if user:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Statistics")
            st.metric("Total XP", user[2])
            st.metric("Tasks Completed", user[3])
            st.metric("Current Streak", f"{user[4]} days 🔥")
            st.metric("Longest Streak", f"{user[5]} days")
            st.metric("XP Multiplier", f"{user[15]:.2f}x")
        
        with col2:
            st.subheader("🎯 Learning Profile")
            st.write(f"**Subjects:** {user[8]}")
            st.write(f"**Learning Style:** {user[9]}")
            st.write(f"**Weekly Hours:** {user[10]}")
            st.write(f"**Motivation:** {user[11]}")
            st.write(f"**Skill Level:** {user[12]}")
    
    st.divider()
    
    # Achievements
    st.subheader("🏆 Achievements")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT achievement_name, earned_at, reward_type, reward_value
        FROM Achievement WHERE user_id = ?
        ORDER BY earned_at DESC
    """, (st.session_state.user_id,))
    
    achievements = cursor.fetchall()
    conn.close()
    
    if achievements:
        for ach in achievements:
            st.markdown(f"""
                <div class="achievement-badge">
                    🏆 {ach[0]} - Earned {ach[1][:10]}
                    <br><small>Reward: {ach[2]}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Complete tasks to earn achievements!")

# --- 5. MAIN APP ---

if not st.session_state.authenticated:
    render_login()
elif not st.session_state.onboarded:
    render_onboarding()
else:
    # Sidebar navigation
    with st.sidebar:
        st.title("🧠 BrainWash")
        st.write(f"**{st.session_state.username}**")
        
        user = UserDataManager.get_user(st.session_state.username)
        if user:
            st.metric("XP", user[2])
            st.metric("Streak", f"{user[4]} days")
        
        st.divider()
        
        page = st.radio("Navigate", ["Arcade", "Insights", "Profile"])
        
        st.divider()
        
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()
    
    # Route to pages
    if page == "Arcade":
        render_arcade()
    elif page == "Insights":
        render_insights()
    else:
        render_profile()
