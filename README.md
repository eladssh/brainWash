# BrainWash: Arcade - Complete Edition 🧠🎮

A gamified learning platform that transforms study materials into engaging quests with XP, achievements, and personalized insights. Perfect for students, professionals, and lifelong learners who want to make studying actually fun!

## 🆕 Latest Updates

### Login System
- **Returning Users**: Quick login with username
- **New Users**: Simple account creation
- Seamless authentication flow

### Enhanced Onboarding
- **System Showcase**: Learn what makes BrainWash special
- **How It Works**: 4-step journey explanation
- **The Science**: Understand the psychology behind gamification
- LinkedIn-ready feature explanations

### Profile Management
- Edit learning preferences anytime
- Update subjects, learning style, and goals
- All stored persistently in your profile

### Data Export
- **CSV Export**: Download all your task history
- **Google Sheets Ready**: Copy-paste format for easy import
- Export button in Insights dashboard

## ✨ Core Features

### 1. **Login & Authentication**
```
🔑 Been Here?
   ↓
Enter username → Access your saved progress

✨ New Here?
   ↓
Create username → Personalized onboarding
```

### 2. **Smart Onboarding**
Learn about:
- 🎯 **Gamification That Actually Works**: RPG-style learning
- 🤖 **AI-Powered Personalization**: Gemini AI adapts to YOU
- 📊 **Smart Analytics**: Track patterns and progress
- 🎯 **Daily Goals & Streaks**: Build consistency
- 📈 **Progress Persistence**: Never lose your data

### 3. **Minimal Database (SQLite)**
- **User Table**: Profiles, XP, streaks, learning preferences
- **TaskCompletion Table**: Full task history with timestamps
- Automatic initialization and management

### 4. **Gamified Learning**
- **5 Brain Levels**: From 🧟 Brain Rot to 🌌 Galaxy Brain
- **XP System**: Easy (50), Medium (150), Hard (300)
- **Achievements**: Unlock badges at milestones
- **Streaks**: Build daily habits

### 5. **AI-Powered Tasks**
- Upload PDFs or enter topics manually
- AI generates 5 personalized tasks
- Solutions available when you need help
- Reroll option for variety

### 6. **Daily Goals**
- Set custom daily targets
- Real-time progress tracking
- Streak counter with automatic calculation
- Motivational feedback

### 7. **Insights Dashboard**
- 📈 **Overview**: XP, tasks, streaks, averages
- 📅 **7-Day Charts**: Activity and XP trends
- 🎯 **Difficulty Breakdown**: Task distribution
- 📚 **Top Subjects**: Focus areas
- 🕐 **Recent Activity**: Last 10 tasks
- 📤 **Export**: CSV download + Google Sheets format

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.8+
Google AI API Key (Gemini)
```

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up API key**

Option A - `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

Option B - Streamlit secrets (`.streamlit/secrets.toml`):
```toml
GOOGLE_API_KEY = "your_api_key_here"
```

3. **Run the app**
```bash
streamlit run brainwash_final.py
```

4. **First Time Setup**
- Choose "New Here?" tab
- Create your username
- Complete onboarding (read the showcase!)
- Start your first mission

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

## 🎮 User Flow

### 1. Login/Signup
```
First Visit → Create Account → Onboarding
   ↓
Returning → Enter Username → Dashboard
```

### 2. Profile Setup (Onboarding)
- Read system showcase and science
- Enter subjects you're studying
- Choose learning style
- Set weekly commitment & daily goal

### 3. Start Learning
```
Arcade → Choose Input Method
   ↓
Manual: Enter subject/topic
OR
PDF: Upload study materials
   ↓
AI generates 5 personalized tasks
   ↓
Complete → Earn XP → Get new task
```

### 4. Track Progress
```
Profile → View stats, achievements, focus timer
   ↓
Insights → Analyze patterns, export data
   ↓
Edit preferences anytime
```

## 🏆 Gamification System

### Brain Levels (XP Requirements)
1. 🧟 **Brain Rot** (0 XP) - "Time to study!"
2. 🧠 **Brain Builder** (300 XP) - "Foundation set."
3. 🔥 **Brain Heater** (800 XP) - "Getting warm!"
4. ⚡ **High Voltage** (1,500 XP) - "Sparking intelligence!"
5. 🌌 **GALAXY BRAIN** (2,500 XP) - "Universal Wisdom."

### Achievements
- 🥉 **The Initiate**: Earn 100 XP
- 🥈 **Scholar**: Complete 10 tasks
- 🥇 **Sage**: Earn 1,500 XP
- 🌌 **Galaxy Brain**: Earn 5,000 XP

### XP Rewards
| Action | XP |
|--------|-----|
| Easy Task | +50 |
| Medium Task | +150 |
| Hard Task | +300 |
| Focus Session | +50 |
| Task Reroll | -20 |

## 📤 Data Export

### From Insights Dashboard

**CSV Export**:
1. Click "📤 Export to CSV"
2. Click "⬇️ Download CSV"
3. Open in Excel or any spreadsheet app

**Google Sheets**:
1. Click "📊 View Google Sheets Format"
2. Copy the displayed table
3. Paste into Google Sheets
4. Format as needed

### Export Includes
- Completion timestamp
- Subject & topic
- Task description
- Difficulty level
- XP earned

## 🎨 Customization Guide

### Adjust Your Settings
```python
Profile → Edit Learning Preferences
   ↓
Modify:
- Subjects interested
- Learning style
- Weekly commitment
- Daily goal
```

### Modify Brain Levels
```python
# In brainwash_final.py
BRAIN_LEVELS = [
    (0, "🧟 Brain Rot", "Time to study!"),
    # Add your own levels...
]
```

### Add Achievements
```python
# In brainwash_final.py
ACHIEVEMENTS = [
    {"id": "custom", "name": "Custom", "emoji": "🎯", 
     "req": 500, "desc": "Description"},
]
```

## 🧪 The Science Behind BrainWash

### Why It Works

**Immediate Feedback Loop** (🎯 Dopamine)
- Instant XP creates reward response
- Gamified learning = 60% more engagement

**Consistency Through Streaks** (🔥 Commitment)
- Daily goals activate commitment psychology
- Loss aversion keeps streaks alive

**Mastery Progression** (📈 Growth)
- Clear levels = tangible improvement
- Graduated difficulty matches learning zones

**Social Proof** (🏆 Status)
- Achievements satisfy need for recognition
- (Coming: Leaderboards for competition)

**Personalization** (🎨 Retention)
- AI adapts to your learning style
- Relevant content = 40% better retention

## 🔧 Advanced Features

### Focus Mode
- Pomodoro-style timer
- Earn 50 XP per session
- Auto-save progress

### Task Management
- ✅ Complete tasks to earn XP
- 🎲 Reroll for variety (-20 XP)
- 💡 View solutions when stuck

### AI Personalization
```python
# AI considers:
- Your subjects of interest
- Learning style preference
- PDF content (if uploaded)
- Previous task difficulty
```

## 📱 Perfect For

- 🎓 **Students**: Make homework fun
- 💼 **Professionals**: Upskill with structure
- 📚 **Lifelong Learners**: Stay motivated
- 👨‍🏫 **Educators**: Engage students differently

## 🐛 Troubleshooting

**Can't login?**
- Check if username exists
- Use "New Here?" to create account

**Database locked?**
- Close all other app instances
- Restart the application

**API errors?**
- Verify Google AI API key
- Check quota limits

**Data not updating?**
- Ensure you clicked "Save Changes"
- Check database file permissions

**Export not working?**
- Complete at least one task first
- Check browser download settings

## 🚀 Future Enhancements

Potential additions:
- 🌐 Real multiplayer leaderboards
- 📧 Email reminders for streaks
- 🎵 Custom themes and sounds
- 📱 Mobile app version
- 🔗 Integration with other learning platforms
- 📊 Advanced analytics (ML predictions)
- 👥 Study groups and challenges
- 🎁 Reward marketplace

## 💡 Pro Tips

1. **Start Small**: Set achievable daily goals (3-5 tasks)
2. **Use PDF Upload**: Let AI extract from your materials
3. **Check Insights**: Review patterns weekly
4. **Maintain Streaks**: Login daily to keep momentum
5. **Reroll Wisely**: Only when task doesn't fit
6. **Export Often**: Keep backups of your progress
7. **Update Preferences**: Adjust as you learn what works

## 📄 Project Structure

```
brainwash-arcade/
│
├── brainwash_final.py      # Main application
├── requirements.txt         # Dependencies
├── README.md               # This file
├── .env                    # API keys (create this)
├── brainwash.db           # SQLite database (auto-created)
│
└── .streamlit/
    └── secrets.toml        # Alternative for API keys
```

## 📄 License

Open source - modify freely for your learning journey!

## 🙏 Acknowledgments

- **Google Gemini AI**: For intelligent task generation
- **Streamlit**: For the incredible UI framework
- **Learning Science**: Research that inspired gamification
---

**Ready to level up your learning? Let's go! 🚀**
