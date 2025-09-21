# main.py
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import bcrypt
import time
from PIL import Image
import requests
from io import BytesIO

load_dotenv()

st.set_page_config(
    page_title="Shiksha Yatra",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API key not found. Please add it to your environment variables.")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

def init_db():
    conn = sqlite3.connect('edugamify.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  name TEXT,
                  grade INTEGER,
                  school TEXT,
                  language TEXT DEFAULT 'English',
                  avatar TEXT DEFAULT 'student1',
                  points INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  message TEXT,
                  response TEXT,
                  subject TEXT,
                  sentiment TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create analytics table
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  subject TEXT,
                  time_spent INTEGER,
                  problems_solved INTEGER,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create gamification table
    c.execute('''CREATE TABLE IF NOT EXISTS gamification
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  badge_name TEXT,
                  badge_description TEXT,
                  earned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create offline content table
    c.execute('''CREATE TABLE IF NOT EXISTS offline_content
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  subject TEXT,
                  content_type TEXT,
                  content TEXT,
                  grade_level INTEGER,
                  language TEXT,
                  download_count INTEGER DEFAULT 0)''')
    
    # Insert some sample offline content
    c.execute('''INSERT OR IGNORE INTO offline_content 
                 (title, subject, content_type, content, grade_level, language) VALUES
                 ('Basic Algebra', 'Math', 'PDF', 'algebra_basics.pdf', 6, 'English'),
                 ('Photosynthesis', 'Science', 'PDF', 'photosynthesis.pdf', 7, 'English'),
                 ('Simple Circuits', 'Technology', 'PDF', 'circuits.pdf', 8, 'English'),
                 ('Geometry Basics', 'Math', 'Game', 'geometry_game.html', 6, 'English'),
                 ('English Vocabulary', 'English', 'Flashcards', 'vocabulary_cards.pdf', 6, 'English')
              ''')
    
    conn.commit()
    return conn

# Initialize database and model
conn = init_db()
model = setup_gemini()

def local_css():
    st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            color: #4809b7;
            text-align: center;
            margin-bottom: 2rem;
        }
        .sub-header {
            font-size: 1.8rem;
            color: #12438c;
            margin-bottom: 1rem;
        }
        .card {
            padding: 20px;
            border-radius: 10px;
             color: #ddfafd;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            background-color: rgb(2, 26, 42);
        }
        .sidebar .sidebar-content {
            background-color: #020619;
        }
        .stButton>button {
            background-color: #0e0227;
            color: white;
            border-radius: 8px;
            padding: 10px 24px;
        }
        .chat-message {
            padding: 1.5rem;
             color: #180539;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        .chat-message.user {
            background-color: #E3F2FD;
            margin-left: 20%;
             color: #180539;
        }
        .chat-message.assistant {
            background-color: #BBDEFB;
            margin-right: 20%;
             color: #180539;
        }
        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            background-color: #FFD700;
            color: #000;
            margin: 5px;
            font-weight: bold;
        }
        .progress-bar {
            height: 20px;
            background-color: #E0E0E0;
            border-radius: 10px;
               color: #180539;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            border-radius: 10px;
            text-align: center;
            color: white;
            line-height: 20px;
        }
        .subject-card {
            cursor: pointer;
               color: #180539;
            transition: all 0.3s ease;
        }
        .subject-card:hover {
            transform: scale(1.05);
               color: #32116b;
        }
        </style>
    """, unsafe_allow_html=True)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_user(username, password, name, grade, school, language):
    c = conn.cursor()
    try:
        hashed_pw = hash_password(password)
        c.execute("INSERT INTO users (username, password, name, grade, school, language) VALUES (?, ?, ?, ?, ?, ?)",
                  (username, hashed_pw, name, grade, school, language))
        conn.commit()
        
        # Add initial badges
        user_id = c.lastrowid
        c.execute("INSERT INTO gamification (user_id, badge_name, badge_description) VALUES (?, ?, ?)",
                 (user_id, "Starter", "Welcome to EduGamify! You've taken your first step in learning."))
        conn.commit()
        
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    if user and check_password(password, user[2]):
        return user
    return None

# Chat functions
def get_gemini_response(prompt, user_context):
    full_prompt = f"""
    You are an AI tutor named "EduBot" for rural students in grades 6-12. 
    The student is in grade {user_context['grade']} and studying at {user_context['school']}. 
    The student's preferred language is {user_context['language']}.
    
    The student has limited internet access, so your explanations should be clear and concise. 
    Help with STEM subjects primarily but be willing to help with other subjects too.
    
    Make your responses engaging, encouraging, and slightly gamified. Use emojis occasionally to make it fun.
    If the student is struggling, offer encouragement and break down the problem into smaller steps.
    
    Student's message: {prompt}
    
    Provide a helpful, engaging response that addresses the student's question while making learning fun. 
    If relevant, suggest a gamified way to practice this concept.
    """
    
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"I'm having trouble responding right now. Please try again later. Error: {str(e)}"

def analyze_sentiment(text):
    # Simple sentiment analysis (in a real app, you'd use a proper NLP library)
    positive_words = ['good', 'great', 'awesome', 'excellent', 'happy', 'thanks', 'thank you', 'helpful', 'love', 'like']
    negative_words = ['bad', 'terrible', 'hate', 'difficult', 'hard', 'confused', 'problem', 'issue', 'don\'t understand']
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"

def save_chat(user_id, message, response, subject):
    sentiment = analyze_sentiment(message)
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (user_id, message, response, subject, sentiment) VALUES (?, ?, ?, ?, ?)",
              (user_id, message, response, subject, sentiment))
    
    # Award points for interaction
    c.execute("UPDATE users SET points = points + 5 WHERE id = ?", (user_id,))
    
    # Check for badge achievements
    check_badge_achievements(user_id)
    
    conn.commit()

def get_chat_history(user_id):
    c = conn.cursor()
    c.execute("SELECT message, response, timestamp, subject FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    return c.fetchall()

# Analytics functions
def update_analytics(user_id, subject, time_spent=1, problems_solved=1):
    c = conn.cursor()
    c.execute("INSERT INTO analytics (user_id, subject, time_spent, problems_solved) VALUES (?, ?, ?, ?)",
              (user_id, subject, time_spent, problems_solved))
    
    # Award points for learning
    c.execute("UPDATE users SET points = points + ? WHERE id = ?", (problems_solved * 10, user_id))
    
    # Check for badge achievements
    check_badge_achievements(user_id)
    
    conn.commit()

def get_analytics(user_id):
    c = conn.cursor()
    c.execute("SELECT subject, SUM(time_spent) as total_time, SUM(problems_solved) as total_problems FROM analytics WHERE user_id = ? GROUP BY subject", (user_id,))
    return c.fetchall()

# Gamification functions
def check_badge_achievements(user_id):
    c = conn.cursor()
    
    # Check total points
    c.execute("SELECT points FROM users WHERE id = ?", (user_id,))
    points = c.fetchone()[0]
    
    # Check subjects covered
    c.execute("SELECT COUNT(DISTINCT subject) FROM analytics WHERE user_id = ?", (user_id,))
    subjects_covered = c.fetchone()[0]
    
    # Check problems solved
    c.execute("SELECT SUM(problems_solved) FROM analytics WHERE user_id = ?", (user_id,))
    problems_solved = c.fetchone()[0] or 0
    
    # Define badge criteria
    badges = [
        ("Quick Learner", "Earned 50 points", points >= 50 and points < 100),
        ("Knowledge Seeker", "Earned 100 points", points >= 100),
        ("Math Whiz", "Solved 10 math problems", problems_solved >= 10),
        ("Science Explorer", "Solved 10 science problems", problems_solved >= 10),
        ("Multitalented", "Studied 3 different subjects", subjects_covered >= 3),
    ]
    
    # Award new badges
    for badge_name, badge_desc, condition in badges:
        if condition:
            # Check if user already has this badge
            c.execute("SELECT * FROM gamification WHERE user_id = ? AND badge_name = ?", (user_id, badge_name))
            if not c.fetchone():
                c.execute("INSERT INTO gamification (user_id, badge_name, badge_description) VALUES (?, ?, ?)",
                         (user_id, badge_name, badge_desc))
                conn.commit()

def get_badges(user_id):
    c = conn.cursor()
    c.execute("SELECT badge_name, badge_description, earned_date FROM gamification WHERE user_id = ? ORDER BY earned_date DESC", (user_id,))
    return c.fetchall()

def get_leaderboard():
    c = conn.cursor()
    c.execute("SELECT name, grade, school, points FROM users ORDER BY points DESC LIMIT 10")
    return c.fetchall()

# Offline content functions
def get_offline_content(grade=None, subject=None, language='English'):
    c = conn.cursor()
    query = "SELECT * FROM offline_content WHERE language = ?"
    params = [language]
    
    if grade:
        query += " AND grade_level = ?"
        params.append(grade)
    if subject and subject != 'All':
        query += " AND subject = ?"
        params.append(subject)
    
    c.execute(query, params)
    return c.fetchall()

def increment_download_count(content_id):
    c = conn.cursor()
    c.execute("UPDATE offline_content SET download_count = download_count + 1 WHERE id = ?", (content_id,))
    conn.commit()

# Page functions
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 class='main-header'>Shiksha Yatra</h1>", unsafe_allow_html=True)
        st.markdown("<h3 class='sub-header'>Login to Your Account</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                user = verify_user(username, password)
                if user:
                    st.session_state.user = {
                        'id': user[0],
                        'username': user[1],
                        'name': user[3],
                        'grade': user[4],
                        'school': user[5],
                        'language': user[6],
                        'avatar': user[7],
                        'points': user[8]
                    }
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        if st.button("Create New Account"):
            st.session_state.page = "register"
            st.rerun()

def register_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 class='main-header'>Shiksha Yatra</h1>", unsafe_allow_html=True)
        st.markdown("<h3 class='sub-header'>Create New Account</h3>", unsafe_allow_html=True)
        
        with st.form("register_form"):
            name = st.text_input("Full Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            grade = st.selectbox("Grade", options=list(range(6, 13)))
            school = st.text_input("School Name")
            language = st.selectbox("Preferred Language", 
                                   ["English", "Hindi", "Odia", "Telugu", "Bengali"])
            submitted = st.form_submit_button("Create Account")
            
            if submitted:
                if create_user(username, password, name, grade, school, language):
                    st.success("Account created successfully! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Username already exists. Please choose a different one.")
        
        if st.button("Back to Login"):
            st.session_state.page = "login"
            st.rerun()

def dashboard_page():
    st.markdown(f"<h1 class='main-header'>Welcome, {st.session_state.user['name']}!</h1>", unsafe_allow_html=True)
    
    # Display user stats
    col1, col2, col3, col4 = st.columns(4)
    analytics = get_analytics(st.session_state.user['id'])
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Total Learning Time")
        total_time = sum([a[1] for a in analytics]) if analytics else 0
        st.metric(label="Hours", value=total_time)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Problems Solved")
        total_problems = sum([a[2] for a in analytics]) if analytics else 0
        st.metric(label="Count", value=total_problems)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Subjects Covered")
        subjects = len(set([a[0] for a in analytics])) if analytics else 0
        st.metric(label="Count", value=subjects)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("EduPoints")
        st.metric(label="Points", value=st.session_state.user['points'])
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("<h3 class='sub-header'>Quick Actions</h3>", unsafe_allow_html=True)
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("📚 Study Now", use_container_width=True):
            st.session_state.page = "subjects"
            st.rerun()
    
    with action_col2:
        if st.button("💬 Ask Tutor", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
    
    with action_col3:
        if st.button("📥 Offline Content", use_container_width=True):
            st.session_state.page = "offline"
            st.rerun()
    
    with action_col4:
        if st.button("🏆 View Badges", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()
    
    # Display subject-wise analytics
    st.markdown("<h3 class='sub-header'>Subject-wise Performance</h3>", unsafe_allow_html=True)
    if analytics:
        df = pd.DataFrame(analytics, columns=['Subject', 'Time Spent', 'Problems Solved'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(df, values='Time Spent', names='Subject', title='Time Spent per Subject')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(df, x='Subject', y='Problems Solved', title='Problems Solved per Subject')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No analytics data yet. Start studying to see your progress!")
    
    # Recent activity
    st.markdown("<h3 class='sub-header'>Recent Activity</h3>", unsafe_allow_html=True)
    chat_history = get_chat_history(st.session_state.user['id'])
    if chat_history:
        for message, response, timestamp, subject in chat_history:
            st.markdown(f"<div class='card'><b>{timestamp.split()[0]}:</b> {message[:100]}... <i>({subject})</i></div>", unsafe_allow_html=True)
    else:
        st.info("No recent activity. Start a conversation with your AI tutor!")

def subjects_page():
    st.markdown("<h1 class='main-header'>Study Subjects</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='sub-header'>Choose a subject to study</h3>", unsafe_allow_html=True)
    
    subjects = [
        {"name": "Mathematics", "icon": "🧮", "color": "#FF6B6B"},
        {"name": "Science", "icon": "🔬", "color": "#4ECDC4"},
        {"name": "Technology", "icon": "💻", "color": "#45B7D1"},
        {"name": "Engineering", "icon": "⚙️", "color": "#FFBE0B"},
        {"name": "English", "icon": "📚", "color": "#FF6B6B"},
        {"name": "Social Studies", "icon": "🌍", "color": "#4ECDC4"},
    ]
    
    cols = st.columns(3)
    for idx, subject in enumerate(subjects):
        with cols[idx % 3]:
            st.markdown(f"""
                <div class='card subject-card' style='border-top: 5px solid {subject["color"]}; text-align: center;'>
                    <h2>{subject['icon']}</h2>
                    <h3>{subject['name']}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Study {subject['name']}", key=f"subject_{idx}"):
                st.session_state.current_subject = subject['name']
                st.session_state.page = "chat"
                st.rerun()

def chat_page():
    st.markdown(f"<h1 class='main-header'>AI Tutor - {st.session_state.get('current_subject', 'General Help')}</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='sub-header'>Chat with your personal learning assistant</h3>", unsafe_allow_html=True)
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for i, (message, is_user) in enumerate(st.session_state.chat_history):
        if is_user:
            st.markdown(f"<div class='chat-message user'><b>You:</b> {message}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-message assistant'><b>EduBot:</b> {message}</div>", unsafe_allow_html=True)
    
    # Chat input
    subject = st.session_state.get('current_subject', 'General')
    
    user_input = st.chat_input("Type your question here...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.chat_history.append((user_input, True))
        
        # Get AI response
        with st.spinner("EduBot is thinking..."):
            response = get_gemini_response(user_input, st.session_state.user)
        
        # Add AI response to chat history
        st.session_state.chat_history.append((response, False))
        
        # Save to database
        save_chat(st.session_state.user['id'], user_input, response, subject)
        update_analytics(st.session_state.user['id'], subject, time_spent=2, problems_solved=1)
        
        st.rerun()
    
    if st.button("Back to Subjects"):
        st.session_state.page = "subjects"
        st.rerun()

def offline_content_page():
    st.markdown("<h1 class='main-header'>Offline Content</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='sub-header'>Download content for offline study</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        grade_filter = st.selectbox("Filter by Grade", 
                                   options=["All"] + list(range(6, 13)),
                                   index=0)
    
    with col2:
        subject_filter = st.selectbox("Filter by Subject", 
                                     options=["All", "Math", "Science", "Technology", "Engineering", "English"],
                                     index=0)
    
    content = get_offline_content(
        grade=grade_filter if grade_filter != "All" else None,
        subject=subject_filter if subject_filter != "All" else None,
        language=st.session_state.user['language']
    )
    
    if content:
        for item in content:
            id, title, subject, content_type, content, grade_level, language, download_count = item
            
            st.markdown(f"""
            <div class='card'>
                <h3>{title} ({subject})</h3>
                <p>Grade: {grade_level} | Type: {content_type} | Language: {language} | Downloads: {download_count}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Download {title}", key=f"download_{id}"):
                increment_download_count(id)
                st.success(f"Downloading {title}. This content is now available offline!")
    else:
        st.info("No offline content available for your filters.")
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def profile_page():
    st.markdown("<h1 class='main-header'>Your Profile</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Personal Information")
        st.write(f"**Name:** {st.session_state.user['name']}")
        st.write(f"**Username:** {st.session_state.user['username']}")
        st.write(f"**Grade:** {st.session_state.user['grade']}")
        st.write(f"**School:** {st.session_state.user['school']}")
        st.write(f"**Language:** {st.session_state.user['language']}")
        st.write(f"**EduPoints:** {st.session_state.user['points']}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show learning statistics
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Learning Statistics")
        analytics = get_analytics(st.session_state.user['id'])
        
        if analytics:
            df = pd.DataFrame(analytics, columns=['Subject', 'Time Spent', 'Problems Solved'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No learning data available yet.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Show badges
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Your Badges")
        badges = get_badges(st.session_state.user['id'])
        
        if badges:
            for badge_name, badge_description, earned_date in badges:
                st.markdown(f'<div class="badge">{badge_name}</div>', unsafe_allow_html=True)
                st.caption(f"{badge_description} - {earned_date.split()[0]}")
        else:
            st.info("You haven't earned any badges yet. Keep learning!")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show leaderboard
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Top Learners")
        leaderboard = get_leaderboard()
        
        if leaderboard:
            for i, (name, grade, school, points) in enumerate(leaderboard):
                st.write(f"{i+1}. {name} (Grade {grade}) - {points} points")
                if name == st.session_state.user['name']:
                    st.success("That's you!")
        else:
            st.info("No leaderboard data available.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

def about_page():
    st.markdown("<h1 class='main-header'>About Rural EduGamify</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='card'>
    <h3>Empowering Rural Education Through Gamification</h3>
    <p>Rural EduGamify is a innovative platform designed to enhance learning outcomes for students in rural schools (grades 6-12), with a focus on STEM subjects. Our platform uses interactive games, multilingual content, and offline access to engage students with limited internet connectivity.</p>
    
    <h4>Key Features:</h4>
    <ul>
        <li>AI-powered tutoring system</li>
        <li>Gamified learning experiences with points and badges</li>
        <li>Multilingual support for diverse learners</li>
        <li>Offline accessibility for low-connectivity areas</li>
        <li>Progress tracking and analytics</li>
        <li>Low-bandwidth optimized</li>
        <li>Personalized learning paths</li>
    </ul>
    
    <h4>Our Mission:</h4>
    <p>To bridge the educational gap in rural areas by providing engaging, accessible, and effective learning tools that inspire students to excel in STEM subjects.</p>
    
    <p>This initiative is supported by the Government of Odisha, Electronics & IT Department.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Team information
    st.markdown("<h3 class='sub-header'>Our Team</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='card' style='text-align: center;'>
            <h4>Education Experts</h4>
            <p>Curriculum designers and teachers with experience in rural education</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='card' style='text-align: center;'>
            <h4>Technology Team</h4>
            <p>Software developers and AI specialists creating innovative learning solutions</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='card' style='text-align: center;'>
            <h4>Community Partners</h4>
            <p>Local organizations helping implement our platform in rural schools</p>
        </div>
        """, unsafe_allow_html=True)

def contact_page():
    st.markdown("<h1 class='main-header'>Contact Us</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='card'>
    <h3>Get in Touch</h3>
    <p>We'd love to hear from you! Whether you have questions, feedback, or need support, please don't hesitate to reach out.</p>
    
    <h4>Contact Information:</h4>
    <p><b>Email:</b> support@ruraledugamify.org</p>
    <p><b>Phone:</b> +91-XXX-XXX-XXXX</p>
    <p><b>Address:</b> Electronics & IT Department, Government of Odisha, India</p>
    
    <h4>Send us a message:</h4>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("contact_form"):
        name = st.text_input("Your Name")
        email = st.text_input("Your Email")
        message = st.text_area("Your Message")
        submitted = st.form_submit_button("Send Message")
        
        if submitted:
            st.success("Thank you for your message! We'll get back to you soon.")

# Main app
def main():
    local_css()
    
    # Initialize session state
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "user" not in st.session_state:
        st.session_state.user = None
    
    # Sidebar navigation
    if st.session_state.user:
        with st.sidebar:
            st.image("https://ideogram.ai/assets/progressive-image/balanced/response/Y4_3nbqYQOu7h4NNJjaPkw", use_column_width=True)
            st.write(f"Welcome, {st.session_state.user['name']}!")
            
            # Progress bar
            st.markdown("<div class='progress-bar'><div class='progress-fill' style='width: 65%;'>Level 3</div></div>", unsafe_allow_html=True)
            st.write(f"**EduPoints:** {st.session_state.user['points']}")
            
            st.divider()
            
            if st.button("🏠 Dashboard"):
                st.session_state.page = "dashboard"
                st.rerun()
            if st.button("📚 Study Subjects"):
                st.session_state.page = "subjects"
                st.rerun()
            if st.button("💬 AI Tutor"):
                st.session_state.page = "chat"
                st.rerun()
            if st.button("📥 Offline Content"):
                st.session_state.page = "offline"
                st.rerun()
            if st.button("📊 Profile & Badges"):
                st.session_state.page = "profile"
                st.rerun()
            if st.button("ℹ️ About"):
                st.session_state.page = "about"
                st.rerun()
            if st.button("📞 Contact"):
                st.session_state.page = "contact"
                st.rerun()
            if st.button("🚪 Logout"):
                st.session_state.user = None
                st.session_state.page = "login"
                st.session_state.chat_history = []
                st.rerun()
    
    # Page routing
    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "register":
        register_page()
    elif st.session_state.page == "dashboard":
        dashboard_page()
    elif st.session_state.page == "subjects":
        subjects_page()
    elif st.session_state.page == "chat":
        chat_page()
    elif st.session_state.page == "offline":
        offline_content_page()
    elif st.session_state.page == "profile":
        profile_page()
    elif st.session_state.page == "about":
        about_page()
    elif st.session_state.page == "contact":
        contact_page()

if __name__ == "__main__":
    main()