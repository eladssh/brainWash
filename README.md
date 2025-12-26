# BrainWash: Arcade - Enhanced Edition 🧠

A gamified learning platform that transforms study materials into engaging quests with XP, achievements, and personalized insights.

## ✨ New Features

### 1. **Minimal Database (SQLite)**
- **User Table**: Stores user profiles, XP, tasks completed, streaks, learning preferences
- **TaskCompletion Table**: Logs every completed task with subject, difficulty, XP earned, and timestamp
- Persistent data across sessions
- Automatic database initialization

### 2. **Onboarding with Context**
- Personalized welcome flow
- Collects learning preferences (subjects, learning style, weekly commitment)
- Sets daily goals based on user capacity
- AI uses onboarding data to generate personalized tasks

### 3. **Daily Goal System**
- Customizable daily task targets
- Real-time progress tracking
- Visual progress bar with motivational messages
- Streak counter to maintain consistency
- Automatic streak calculation (resets if day is skipped)

### 4. **Insights Dashboard**
- **Overview Metrics**: Total XP, tasks completed, streak, average XP per task
- **7-Day Activity Chart**: Visualize daily task completion
- **XP Trends**: Track XP earned over the past week
- **Difficulty Breakdown**: See distribution of Easy/Medium/Hard tasks
- **Top Subjects**: Track which subjects you're focusing on
- **Recent Activity Feed**: Review last 10 completed tasks with timestamps

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Google AI API Key (Gemini)

### Installation

1. **Clone or download the files**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

Or configure in Streamlit secrets (`.streamlit/secrets.toml`):
```toml
GOOGLE_API_KEY = "your_api_key_here"
```

4. **Run the app**
```bash
streamlit run brainwash_enhanced.py
```

## 📊 Database Schema

### User Table
```sql
CREATE TABLE User (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    total_xp INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    daily_goal INTEGER DEFAULT 3,
    streak_days INTEGER DEFAULT 0,
    last_activity_date TEXT,
    created_at TEXT,
    subjects_interested TEXT,
    learning_style TEXT,
    weekly_commitment INTEGER
)
```

### TaskCompletion Table
```sql
CREATE TABLE TaskCompletion (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    task_text TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    xp_earned INTEGER NOT NULL,
    subject TEXT,
    topic TEXT,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES User(id)
)
```

## 🎮 How to Use

### First Time Setup
1. Launch the app
2. Complete the onboarding form:
   - Choose a username
   - Enter subjects you're studying
   - Select your learning style
   - Set weekly commitment and daily goal
3. Click "Start My Journey"

### Creating a Study Session
1. Navigate to **Arcade**
2. Choose either:
   - **Subject Search**: Manual subject/topic input
   - **PDF Scan**: Upload study materials
3. AI generates 5 personalized tasks (1 Hard, 2 Medium, 2 Easy)

### Completing Tasks
- Click **✅ Done** to complete and earn XP
- Click **🎲 Reroll** (-20 XP) to get a different task
- View solutions by clicking **💡 Show Solution**

### Tracking Progress
- **Daily Goal**: Monitor in sidebar (updates in real-time)
- **Profile**: View stats, achievements, focus timer
- **Insights**: Analyze patterns, trends, and performance

## 🏆 Gamification Features

### Brain Levels
- 🧟 Brain Rot (0 XP)
- 🧠 Brain Builder (300 XP)
- 🔥 Brain Heater (800 XP)
- ⚡ High Voltage (1,500 XP)
- 🌌 Galaxy Brain (2,500 XP)

### Achievements
- 🥉 The Initiate: 100 XP
- 🥈 Scholar: 10 Tasks
- 🥇 Sage: 1,500 XP
- 🌌 Galaxy Brain: 5,000 XP

### XP Rewards
- Easy Task: 50 XP
- Medium Task: 150 XP
- Hard Task: 300 XP
- Focus Session: 50 XP

## 🔧 Key Functions

### Database Functions
- `init_database()`: Creates tables
- `get_or_create_user()`: User authentication
- `update_user_stats()`: XP and streak updates
- `log_task_completion()`: Records task history
- `get_user_analytics()`: Retrieves insights data
- `get_today_progress()`: Daily goal tracking

### AI Functions
- `get_initial_plan()`: Generates 5 personalized tasks
- `get_new_task_json()`: Creates individual tasks
- Uses user context from onboarding for personalization

## 📈 Analytics Queries

The insights dashboard uses SQL queries to analyze:
- Tasks completed per day (last 7 days)
- XP earned per day (last 7 days)
- Task difficulty distribution
- Subject focus areas
- Recent activity timeline

## 🎨 Customization

### Adjust Daily Goals
Profile → Edit Profile → Change daily goal slider

### Modify Brain Levels
Edit `BRAIN_LEVELS` list in code

### Add New Achievements
Edit `ACHIEVEMENTS` list in code

## 💾 Data Storage

- Database file: `brainwash.db` (SQLite)
- Created automatically on first run
- Portable - copy file to backup/transfer data

## 🐛 Troubleshooting

**Database locked error**: Close any other connections to the database

**API errors**: Check your Google AI API key and quota

**Onboarding not showing**: Delete session state or logout

**Stats not updating**: Ensure `load_user_data()` is called after updates

## 🔮 Future Enhancements

Potential features to add:
- Leaderboards (real multiplayer)
- Achievement notifications
- Export study reports
- Calendar view of activity
- Custom task categories
- Study reminders
- Integration with other learning platforms

## 📝 Notes

- The database is local SQLite (single-user)
- For multi-user deployment, migrate to PostgreSQL/MySQL
- AI responses may vary - regenerate if quality is low
- Streak resets if you skip a day
- Reroll costs 20 XP to encourage strategic thinking

## 📄 License

Open source - modify as needed for your learning journey!

---

**Built with**: Streamlit • Google Gemini AI • SQLite • Python

**Enjoy your gamified learning experience! 🎓🎮**
