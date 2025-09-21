# main.py (updated with multilanguage support)
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
import random
import math
from googletrans import Translator, LANGUAGES

# Load environment variables
load_dotenv()

# Configure page settings
st.set_page_config(
    page_title="Shiksha Yatra",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Gemini API
def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Please add it to your environment variables.")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

# Initialize translator
def setup_translator():
    return Translator()

# Language mapping
LANGUAGE_MAPPING = {
    'English': 'en',
    'Hindi': 'hi',
    'Odia': 'or',
    'Telugu': 'te',
    'Bengali': 'bn',
    'Tamil': 'ta',
    'Marathi': 'mr',
    'Gujarati': 'gu',
    'Kannada': 'kn',
    'Malayalam': 'ml',
    'Punjabi': 'pa',
    'Urdu': 'ur'
}

# Initialize database
def init_db():
    conn = sqlite3.connect('edugamify.db')
    c = conn.cursor()
    
    # Create users table
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
    
    # Create game scores table
    c.execute('''CREATE TABLE IF NOT EXISTS game_scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  game_name TEXT,
                  score INTEGER,
                  subject TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Insert some sample offline content
    c.execute('''INSERT OR IGNORE INTO offline_content 
                 (title, subject, content_type, content, grade_level, language) VALUES
                 ('Basic Algebra', 'Math', 'PDF', 'algebra_basics.pdf', 6, 'English'),
                 ('Photosynthesis', 'Science', 'PDF', 'photosynthesis.pdf', 7, 'English'),
                 ('Simple Circuits', 'Technology', 'PDF', 'circuits.pdf', 8, 'English'),
                 ('Geometry Basics', 'Math', 'Game', 'geometry_game.html', 6, 'English'),
                 ('English Vocabulary', 'English', 'Flashcards', 'vocabulary_cards.pdf', 6, 'English'),
                 ('बीजगणित की मूल बातें', 'Math', 'PDF', 'algebra_basics_hindi.pdf', 6, 'Hindi'),
                 ('প্রকৃতির বিস্ময়', 'Science', 'PDF', 'nature_wonders_bengali.pdf', 7, 'Bengali'),
                 ('ଗଣିତ ମୌଳିକ', 'Math', 'PDF', 'math_basics_odia.pdf', 6, 'Odia')
              ''')
    
    conn.commit()
    return conn

# Initialize database and models
conn = init_db()
model = setup_gemini()
translator = setup_translator()

# Custom CSS
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
            background-color: rgb(6, 43, 67);
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
        .math-game-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 15px 0;
        }
        .math-game-cell {
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            background-color: #BBDEFB;
            border: 2px solid #1E88E5;
            border-radius: 5px;
            cursor: pointer;
        }
        .science-quiz-option {
            padding: 10px;
            margin: 5px 0;
            background-color: #C8E6C9;
            border: 1px solid #4CAF50;
            border-radius: 5px;
            cursor: pointer;
        }
        .science-quiz-option:hover {
            background-color: #A5D6A7;
        }
        </style>
    """, unsafe_allow_html=True)

# Translation functions
def translate_text(text, dest_lang='en', src_lang='auto'):
    """
    Translate text to the specified language
    """
    try:
        if not text or text.strip() == "":
            return text
            
        # If the destination language is English, no need to translate
        if dest_lang == 'en' and src_lang == 'en':
            return text
            
        translation = translator.translate(text, dest=dest_lang, src=src_lang)
        return translation.text
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return text

def translate_to_english(text, src_lang='auto'):
    """
    Translate text to English
    """
    return translate_text(text, 'en', src_lang)

def translate_from_english(text, dest_lang):
    """
    Translate text from English to the specified language
    """
    return translate_text(text, dest_lang, 'en')

# Authentication functions
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
    
    # Check games played
    c.execute("SELECT COUNT(*) FROM game_scores WHERE user_id = ?", (user_id,))
    games_played = c.fetchone()[0]
    
    # Define badge criteria
    badges = [
        ("Quick Learner", "Earned 50 points", points >= 50 and points < 100),
        ("Knowledge Seeker", "Earned 100 points", points >= 100),
        ("Math Whiz", "Solved 10 math problems", problems_solved >= 10),
        ("Science Explorer", "Solved 10 science problems", problems_solved >= 10),
        ("Multitalented", "Studied 3 different subjects", subjects_covered >= 3),
        ("Game Master", "Played 5 educational games", games_played >= 5),
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

# Game functions
def save_game_score(user_id, game_name, score, subject):
    c = conn.cursor()
    c.execute("INSERT INTO game_scores (user_id, game_name, score, subject) VALUES (?, ?, ?, ?)",
              (user_id, game_name, score, subject))
    
    # Award points for playing games
    c.execute("UPDATE users SET points = points + ? WHERE id = ?", (score // 10, user_id))
    
    # Update analytics
    update_analytics(user_id, subject, time_spent=5, problems_solved=1)
    
    # Check for badge achievements
    check_badge_achievements(user_id)
    
    conn.commit()

def get_game_scores(user_id):
    c = conn.cursor()
    c.execute("SELECT game_name, score, timestamp FROM game_scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    return c.fetchall()

# Math Game Functions
def math_quiz_game():
    st.markdown("<h3 class='sub-header'>Math Quiz Challenge</h3>", unsafe_allow_html=True)
    
    if 'math_score' not in st.session_state:
        st.session_state.math_score = 0
        st.session_state.math_question = 0
        st.session_state.math_questions = generate_math_questions()
        st.session_state.math_correct = None
    
    if st.session_state.math_question < len(st.session_state.math_questions):
        question_data = st.session_state.math_questions[st.session_state.math_question]
        
        # Translate question and options if needed
        user_lang = st.session_state.user['language']
        if user_lang != 'English':
            question = translate_from_english(question_data['question'], LANGUAGE_MAPPING[user_lang])
            options = [translate_from_english(opt, LANGUAGE_MAPPING[user_lang]) for opt in question_data['options']]
            answer = translate_from_english(question_data['answer'], LANGUAGE_MAPPING[user_lang])
        else:
            question = question_data['question']
            options = question_data['options']
            answer = question_data['answer']
        
        st.markdown(f"<div class='game-container'>", unsafe_allow_html=True)
        st.markdown(f"**Question {st.session_state.math_question + 1}:** {question}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            for i, option in enumerate(options):
                if st.button(option, key=f"math_opt_{i}", use_container_width=True):
                    if option == answer:
                        st.session_state.math_score += 10
                        st.session_state.math_correct = True
                    else:
                        st.session_state.math_correct = False
                    st.session_state.math_question += 1
                    st.rerun()
        
        with col2:
            if st.session_state.math_correct is not None:
                if st.session_state.math_correct:
                    st.success(translate_from_english("Correct! 🎉", LANGUAGE_MAPPING[user_lang]))
                else:
                    error_msg = translate_from_english(f"Wrong! The correct answer is {answer}", LANGUAGE_MAPPING[user_lang])
                    st.error(error_msg)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='game-container'>", unsafe_allow_html=True)
        score_text = translate_from_english(f"Quiz Complete! Your score: {st.session_state.math_score}/{(len(st.session_state.math_questions)) * 10}", 
                                           LANGUAGE_MAPPING[user_lang])
        st.markdown(f"### {score_text}")
        
        if st.button(translate_from_english("Play Again", LANGUAGE_MAPPING[user_lang])):
            st.session_state.math_score = 0
            st.session_state.math_question = 0
            st.session_state.math_questions = generate_math_questions()
            st.session_state.math_correct = None
            st.rerun()
        
        if st.button(translate_from_english("Save Score", LANGUAGE_MAPPING[user_lang])):
            save_game_score(st.session_state.user['id'], "Math Quiz", st.session_state.math_score, "Math")
            st.success(translate_from_english("Score saved! 🎯", LANGUAGE_MAPPING[user_lang]))
            time.sleep(1)
            st.session_state.math_score = 0
            st.session_state.math_question = 0
            st.session_state.math_questions = generate_math_questions()
            st.session_state.math_correct = None
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def generate_math_questions():
    questions = []
    
    # Grade-appropriate math questions
    if st.session_state.user['grade'] <= 8:
        questions = [
            {
                "question": "What is 15 + 27?",
                "options": ["42", "32", "52", "37"],
                "answer": "42"
            },
            {
                "question": "If a = 5 and b = 3, what is a² + b²?",
                "options": ["34", "64", "16", "25"],
                "answer": "34"
            },
            {
                "question": "What is 3/4 of 60?",
                "options": ["45", "30", "15", "40"],
                "answer": "45"
            },
            {
                "question": "Solve for x: 2x + 5 = 15",
                "options": ["x = 5", "x = 10", "x = 7.5", "x = 6"],
                "answer": "x = 5"
            },
            {
                "question": "What is the area of a rectangle with length 8cm and width 5cm?",
                "options": ["40cm²", "26cm²", "13cm²", "35cm²"],
                "answer": "40cm²"
            }
        ]
    else:
        questions = [
            {
                "question": "What is the value of sin(90°)?",
                "options": ["1", "0", "0.5", "√2/2"],
                "answer": "1"
            },
            {
                "question": "If f(x) = x² + 3x - 4, what is f(2)?",
                "options": ["6", "2", "10", "8"],
                "answer": "6"
            },
            {
                "question": "What is the derivative of x³?",
                "options": ["3x²", "x²", "3x", "x⁴/4"],
                "answer": "3x²"
            },
            {
                "question": "Solve the equation: log₁₀(100) = ?",
                "options": ["2", "10", "1", "100"],
                "answer": "2"
            },
            {
                "question": "What is the Pythagorean theorem?",
                "options": ["a² + b² = c²", "a + b = c", "a² - b² = c²", "a × b = c"],
                "answer": "a² + b² = c²"
            }
        ]
    
    return questions

def science_quiz_game():
    st.markdown("<h3 class='sub-header'>Science Quiz Challenge</h3>", unsafe_allow_html=True)
    
    if 'science_score' not in st.session_state:
        st.session_state.science_score = 0
        st.session_state.science_question = 0
        st.session_state.science_questions = generate_science_questions()
        st.session_state.science_correct = None
    
    if st.session_state.science_question < len(st.session_state.science_questions):
        question_data = st.session_state.science_questions[st.session_state.science_question]
        
        # Translate question and options if needed
        user_lang = st.session_state.user['language']
        if user_lang != 'English':
            question = translate_from_english(question_data['question'], LANGUAGE_MAPPING[user_lang])
            options = [translate_from_english(opt, LANGUAGE_MAPPING[user_lang]) for opt in question_data['options']]
            answer = translate_from_english(question_data['answer'], LANGUAGE_MAPPING[user_lang])
        else:
            question = question_data['question']
            options = question_data['options']
            answer = question_data['answer']
        
        st.markdown(f"<div class='game-container'>", unsafe_allow_html=True)
        st.markdown(f"**Question {st.session_state.science_question + 1}:** {question}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            for i, option in enumerate(options):
                if st.button(option, key=f"science_opt_{i}", use_container_width=True):
                    if option == answer:
                        st.session_state.science_score += 10
                        st.session_state.science_correct = True
                    else:
                        st.session_state.science_correct = False
                    st.session_state.science_question += 1
                    st.rerun()
        
        with col2:
            if st.session_state.science_correct is not None:
                if st.session_state.science_correct:
                    st.success(translate_from_english("Correct! 🎉", LANGUAGE_MAPPING[user_lang]))
                else:
                    error_msg = translate_from_english(f"Wrong! The correct answer is {answer}", LANGUAGE_MAPPING[user_lang])
                    st.error(error_msg)
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='game-container'>", unsafe_allow_html=True)
        score_text = translate_from_english(f"Quiz Complete! Your score: {st.session_state.science_score}/{(len(st.session_state.science_questions)) * 10}", 
                                           LANGUAGE_MAPPING[user_lang])
        st.markdown(f"### {score_text}")
        
        if st.button(translate_from_english("Play Again", LANGUAGE_MAPPING[user_lang])):
            st.session_state.science_score = 0
            st.session_state.science_question = 0
            st.session_state.science_questions = generate_science_questions()
            st.session_state.science_correct = None
            st.rerun()
        
        if st.button(translate_from_english("Save Score", LANGUAGE_MAPPING[user_lang])):
            save_game_score(st.session_state.user['id'], "Science Quiz", st.session_state.science_score, "Science")
            st.success(translate_from_english("Score saved! 🎯", LANGUAGE_MAPPING[user_lang]))
            time.sleep(1)
            st.session_state.science_score = 0
            st.session_state.science_question = 0
            st.session_state.science_questions = generate_science_questions()
            st.session_state.science_correct = None
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def generate_science_questions():
    questions = []
    
    # Grade-appropriate science questions
    if st.session_state.user['grade'] <= 8:
        questions = [
            {
                "question": "Which planet is known as the Red Planet?",
                "options": ["Mars", "Venus", "Jupiter", "Saturn"],
                "answer": "Mars"
            },
            {
                "question": "What is the process by which plants make their own food?",
                "options": ["Photosynthesis", "Respiration", "Digestion", "Transpiration"],
                "answer": "Photosynthesis"
            },
            {
                "question": "Which gas do plants absorb from the atmosphere?",
                "options": ["Carbon Dioxide", "Oxygen", "Nitrogen", "Hydrogen"],
                "answer": "Carbon Dioxide"
            },
            {
                "question": "What is the smallest unit of life?",
                "options": ["Cell", "Atom", "Molecule", "Tissue"],
                "answer": "Cell"
            },
            {
                "question": "Which organ pumps blood throughout the body?",
                "options": ["Heart", "Brain", "Lungs", "Liver"],
                "answer": "Heart"
            }
        ]
    else:
        questions = [
            {
                "question": "What is the chemical symbol for gold?",
                "options": ["Au", "Ag", "Fe", "Go"],
                "answer": "Au"
            },
            {
                "question": "Which subatomic particle has a negative charge?",
                "options": ["Electron", "Proton", "Neutron", "Photon"],
                "answer": "Electron"
            },
            {
                "question": "What is the speed of light?",
                "options": ["299,792 km/s", "150,000 km/s", "450,000 km/s", "100,000 km/s"],
                "answer": "299,792 km/s"
            },
            {
                "question": "Which gas is most abundant in Earth's atmosphere?",
                "options": ["Nitrogen", "Oxygen", "Carbon Dioxide", "Argon"],
                "answer": "Nitrogen"
            },
            {
                "question": "What is the main function of mitochondria?",
                "options": ["Produce energy", "Store genetic information", "Transport proteins", "Create proteins"],
                "answer": "Produce energy"
            }
        ]
    
    return questions

def memory_match_game():
    st.markdown("<h3 class='sub-header'>STEM Memory Match</h3>", unsafe_allow_html=True)
    
    if 'memory_cards' not in st.session_state:
        # Initialize the memory game
        symbols = ['π', '√', '∞', 'α', 'β', '∫', '∑', 'Δ']
        st.session_state.memory_cards = symbols + symbols
        random.shuffle(st.session_state.memory_cards)
        st.session_state.memory_flipped = [False] * 16
        st.session_state.memory_matched = [False] * 16
        st.session_state.memory_first_selection = None
        st.session_state.memory_moves = 0
        st.session_state.memory_matches = 0
    
    user_lang = st.session_state.user['language']
    moves_text = translate_from_english("Moves", LANGUAGE_MAPPING[user_lang])
    matches_text = translate_from_english("Matches", LANGUAGE_MAPPING[user_lang])
    
    st.markdown(f"**{moves_text}:** {st.session_state.memory_moves} | **{matches_text}:** {st.session_state.memory_matches}/8")
    
    # Create the memory game grid
    cols = st.columns(4)
    for i in range(16):
        with cols[i % 4]:
            if st.session_state.memory_matched[i]:
                st.button("✓", key=f"mem_{i}", use_container_width=True)
            elif st.session_state.memory_flipped[i]:
                st.button(st.session_state.memory_cards[i], key=f"mem_{i}", use_container_width=True)
            else:
                if st.button("?", key=f"mem_{i}", use_container_width=True):
                    if st.session_state.memory_first_selection is None:
                        st.session_state.memory_first_selection = i
                        st.session_state.memory_flipped[i] = True
                    else:
                        st.session_state.memory_flipped[i] = True
                        st.session_state.memory_moves += 1
                        
                        # Check for match
                        if st.session_state.memory_cards[st.session_state.memory_first_selection] == st.session_state.memory_cards[i]:
                            st.session_state.memory_matched[st.session_state.memory_first_selection] = True
                            st.session_state.memory_matched[i] = True
                            st.session_state.memory_matches += 1
                        
                        st.session_state.memory_first_selection = None
                    st.rerun()
    
    # Check for game completion
    if st.session_state.memory_matches == 8:
        congrats_text = translate_from_english("🎉 Congratulations! You've matched all pairs!", LANGUAGE_MAPPING[user_lang])
        st.success(congrats_text)
        score = 100 - (st.session_state.memory_moves - 8) * 5
        score = max(score, 10)
        
        score_text = translate_from_english(f"**Your score: {score}**", LANGUAGE_MAPPING[user_lang])
        st.markdown(score_text)
        
        if st.button(translate_from_english("Save Score", LANGUAGE_MAPPING[user_lang])):
            save_game_score(st.session_state.user['id'], "Memory Match", score, "General")
            success_text = translate_from_english("Score saved! 🎯", LANGUAGE_MAPPING[user_lang])
            st.success(success_text)
            time.sleep(1)
            # Reset the game
            st.session_state.memory_cards = None
            st.rerun()

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
                                   ["English", "Hindi", "Odia", "Telugu", "Bengali", "Tamil", "Marathi", 
                                    "Gujarati", "Kannada", "Malayalam", "Punjabi", "Urdu"])
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
    user_lang = st.session_state.user['language']
    welcome_text = translate_from_english(f"Welcome, {st.session_state.user['name']}!", LANGUAGE_MAPPING[user_lang])
    st.markdown(f"<h1 class='main-header'>{welcome_text}</h1>", unsafe_allow_html=True)
    
    # Display user stats
    col1, col2, col3, col4 = st.columns(4)
    analytics = get_analytics(st.session_state.user['id'])
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Total Learning Time", LANGUAGE_MAPPING[user_lang]))
        total_time = sum([a[1] for a in analytics]) if analytics else 0
        st.metric(label=translate_from_english("Hours", LANGUAGE_MAPPING[user_lang]), value=total_time)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Problems Solved", LANGUAGE_MAPPING[user_lang]))
        total_problems = sum([a[2] for a in analytics]) if analytics else 0
        st.metric(label=translate_from_english("Count", LANGUAGE_MAPPING[user_lang]), value=total_problems)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Subjects Covered", LANGUAGE_MAPPING[user_lang]))
        subjects = len(set([a[0] for a in analytics])) if analytics else 0
        st.metric(label=translate_from_english("Count", LANGUAGE_MAPPING[user_lang]), value=subjects)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("EduPoints", LANGUAGE_MAPPING[user_lang]))
        st.metric(label=translate_from_english("Points", LANGUAGE_MAPPING[user_lang]), value=st.session_state.user['points'])
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Quick actions
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Quick Actions', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button(translate_from_english("📚 Study Now", LANGUAGE_MAPPING[user_lang]), use_container_width=True):
            st.session_state.page = "subjects"
            st.rerun()
    
    with action_col2:
        if st.button(translate_from_english("💬 Ask Tutor", LANGUAGE_MAPPING[user_lang]), use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
    
    with action_col3:
        if st.button(translate_from_english("🎮 Play Games", LANGUAGE_MAPPING[user_lang]), use_container_width=True):
            st.session_state.page = "games"
            st.rerun()
    
    with action_col4:
        if st.button(translate_from_english("📥 Offline Content", LANGUAGE_MAPPING[user_lang]), use_container_width=True):
            st.session_state.page = "offline"
            st.rerun()
    
    # Display subject-wise analytics
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Subject-wise Performance', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    if analytics:
        df = pd.DataFrame(analytics, columns=['Subject', 'Time Spent', 'Problems Solved'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(df, values='Time Spent', names='Subject', title=translate_from_english('Time Spent per Subject', LANGUAGE_MAPPING[user_lang]))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(df, x='Subject', y='Problems Solved', title=translate_from_english('Problems Solved per Subject', LANGUAGE_MAPPING[user_lang]))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(translate_from_english("No analytics data yet. Start studying to see your progress!", LANGUAGE_MAPPING[user_lang]))
    
    # Recent activity
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Recent Activity', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    chat_history = get_chat_history(st.session_state.user['id'])
    if chat_history:
        for message, response, timestamp, subject in chat_history:
            # Translate the message preview if needed
            if user_lang != 'English':
                message_preview = translate_from_english(message[:100], LANGUAGE_MAPPING[user_lang])
            else:
                message_preview = message[:100]
                
            st.markdown(f"<div class='card'><b>{timestamp.split()[0]}:</b> {message_preview}... <i>({subject})</i></div>", unsafe_allow_html=True)
    else:
        st.info(translate_from_english("No recent activity. Start a conversation with your AI tutor!", LANGUAGE_MAPPING[user_lang]))

def subjects_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('Study Subjects', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Choose a subject to study', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    
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
            subject_name = translate_from_english(subject['name'], LANGUAGE_MAPPING[user_lang])
            st.markdown(f"""
                <div class='card subject-card' style='border-top: 5px solid {subject["color"]}; text-align: center;'>
                    <h2>{subject['icon']}</h2>
                    <h3>{subject_name}</h3>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(translate_from_english(f"Study {subject['name']}", LANGUAGE_MAPPING[user_lang]), key=f"subject_{idx}"):
                st.session_state.current_subject = subject['name']
                st.session_state.page = "chat"
                st.rerun()

def chat_page():
    user_lang = st.session_state.user['language']
    subject = st.session_state.get('current_subject', 'General Help')
    subject_translated = translate_from_english(subject, LANGUAGE_MAPPING[user_lang])
    
    st.markdown(f"<h1 class='main-header'>{translate_from_english('AI Tutor', LANGUAGE_MAPPING[user_lang])} - {subject_translated}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Chat with your personal learning assistant', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for i, (message, is_user, original_lang) in enumerate(st.session_state.chat_history):
        if is_user:
            # For user messages, show in the original language
            display_message = message if original_lang == user_lang else translate_from_english(message, LANGUAGE_MAPPING[user_lang])
            st.markdown(f"<div class='chat-message user'><b>{translate_from_english('You', LANGUAGE_MAPPING[user_lang])}:</b> {display_message}</div>", unsafe_allow_html=True)
        else:
            # For assistant messages, show in the user's language
            display_message = translate_from_english(message, LANGUAGE_MAPPING[user_lang])
            st.markdown(f"<div class='chat-message assistant'><b>EduBot:</b> {display_message}</div>", unsafe_allow_html=True)
    
    # Chat input
    subject = st.session_state.get('current_subject', 'General')
    
    chat_placeholder = translate_from_english("Type your question here...", LANGUAGE_MAPPING[user_lang])
    user_input = st.chat_input(chat_placeholder)
    
    if user_input:
        # Translate user input to English for processing
        if user_lang != 'English':
            user_input_english = translate_to_english(user_input, LANGUAGE_MAPPING[user_lang])
        else:
            user_input_english = user_input
        
        # Add user message to chat history (store in original language)
        st.session_state.chat_history.append((user_input, True, user_lang))
        
        # Get AI response
        with st.spinner(translate_from_english("EduBot is thinking...", LANGUAGE_MAPPING[user_lang])):
            response = get_gemini_response(user_input_english, st.session_state.user)
        
        # Add AI response to chat history (store in English for consistency)
        st.session_state.chat_history.append((response, False, 'English'))
        
        # Save to database (store original message and English response)
        save_chat(st.session_state.user['id'], user_input, response, subject)
        update_analytics(st.session_state.user['id'], subject, time_spent=2, problems_solved=1)
        
        st.rerun()
    
    if st.button(translate_from_english("Back to Subjects", LANGUAGE_MAPPING[user_lang])):
        st.session_state.page = "subjects"
        st.rerun()

def games_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('Educational Games', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Learn through fun games!', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    
    # Game selection
    games = [
        {"name": "Math Quiz", "icon": "🧮", "description": "Test your math skills with challenging questions", "subject": "Math"},
        {"name": "Science Quiz", "icon": "🔬", "description": "Explore science concepts with fun quizzes", "subject": "Science"},
        {"name": "Memory Match", "icon": "🎯", "description": "Match STEM symbols in this memory game", "subject": "General"},
    ]
    
    cols = st.columns(3)
    for idx, game in enumerate(games):
        with cols[idx]:
            game_name = translate_from_english(game['name'], LANGUAGE_MAPPING[user_lang])
            game_desc = translate_from_english(game['description'], LANGUAGE_MAPPING[user_lang])
            
            st.markdown(f"""
                <div class='card subject-card' style='text-align: center;'>
                    <h2>{game['icon']}</h2>
                    <h3>{game_name}</h3>
                    <p>{game_desc}</p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(translate_from_english(f"Play {game['name']}", LANGUAGE_MAPPING[user_lang]), key=f"game_{idx}"):
                st.session_state.current_game = game['name']
                st.rerun()
    
    # Display selected game
    if hasattr(st.session_state, 'current_game'):
        game_name = translate_from_english(st.session_state.current_game, LANGUAGE_MAPPING[user_lang])
        st.markdown(f"<h3 class='sub-header'>{game_name}</h3>", unsafe_allow_html=True)
        
        if st.session_state.current_game == "Math Quiz":
            math_quiz_game()
        elif st.session_state.current_game == "Science Quiz":
            science_quiz_game()
        elif st.session_state.current_game == "Memory Match":
            memory_match_game()
        
        if st.button(translate_from_english("Back to Games Menu", LANGUAGE_MAPPING[user_lang])):
            del st.session_state.current_game
            st.rerun()
    
    # Display game scores
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Your Game Scores', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    game_scores = get_game_scores(st.session_state.user['id'])
    if game_scores:
        for game_name, score, timestamp in game_scores:
            game_name_translated = translate_from_english(game_name, LANGUAGE_MAPPING[user_lang])
            st.markdown(f"<div class='card'><b>{game_name_translated}:</b> {score} {translate_from_english('points', LANGUAGE_MAPPING[user_lang])} <i>({timestamp.split()[0]})</i></div>", unsafe_allow_html=True)
    else:
        st.info(translate_from_english("No game scores yet. Play some games to earn points!", LANGUAGE_MAPPING[user_lang]))
    
    if st.button(translate_from_english("Back to Dashboard", LANGUAGE_MAPPING[user_lang])):
        st.session_state.page = "dashboard"
        st.rerun()

def offline_content_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('Offline Content', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Download content for offline study', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        grade_filter = st.selectbox(
            translate_from_english("Filter by Grade", LANGUAGE_MAPPING[user_lang]),
            options=["All"] + list(range(6, 13)),
            index=0
        )
    
    with col2:
        subject_filter = st.selectbox(
            translate_from_english("Filter by Subject", LANGUAGE_MAPPING[user_lang]),
            options=["All", "Math", "Science", "Technology", "Engineering", "English"],
            index=0
        )
    
    content = get_offline_content(
        grade=grade_filter if grade_filter != "All" else None,
        subject=subject_filter if subject_filter != "All" else None,
        language=user_lang
    )
    
    if content:
        for item in content:
            id, title, subject, content_type, content, grade_level, language, download_count = item
            
            st.markdown(f"""
            <div class='card'>
                <h3>{title} ({subject})</h3>
                <p>{translate_from_english('Grade', LANGUAGE_MAPPING[user_lang])}: {grade_level} | {translate_from_english('Type', LANGUAGE_MAPPING[user_lang])}: {content_type} | {translate_from_english('Language', LANGUAGE_MAPPING[user_lang])}: {language} | {translate_from_english('Downloads', LANGUAGE_MAPPING[user_lang])}: {download_count}</p>
            </div>
            """, unsafe_allow_html=True)
            
            download_text = translate_from_english(f"Download {title}", LANGUAGE_MAPPING[user_lang])
            if st.button(download_text, key=f"download_{id}"):
                increment_download_count(id)
                success_text = translate_from_english(f"Downloading {title}. This content is now available offline!", LANGUAGE_MAPPING[user_lang])
                st.success(success_text)
    else:
        st.info(translate_from_english("No offline content available for your filters.", LANGUAGE_MAPPING[user_lang]))
    
    if st.button(translate_from_english("Back to Dashboard", LANGUAGE_MAPPING[user_lang])):
        st.session_state.page = "dashboard"
        st.rerun()

def profile_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('Your Profile', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Personal Information", LANGUAGE_MAPPING[user_lang]))
        st.write(f"**{translate_from_english('Name', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['name']}")
        st.write(f"**{translate_from_english('Username', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['username']}")
        st.write(f"**{translate_from_english('Grade', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['grade']}")
        st.write(f"**{translate_from_english('School', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['school']}")
        st.write(f"**{translate_from_english('Language', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['language']}")
        st.write(f"**{translate_from_english('EduPoints', LANGUAGE_MAPPING[user_lang])}:** {st.session_state.user['points']}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show learning statistics
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Learning Statistics", LANGUAGE_MAPPING[user_lang]))
        analytics = get_analytics(st.session_state.user['id'])
        
        if analytics:
            df = pd.DataFrame(analytics, columns=[
                translate_from_english('Subject', LANGUAGE_MAPPING[user_lang]),
                translate_from_english('Time Spent', LANGUAGE_MAPPING[user_lang]),
                translate_from_english('Problems Solved', LANGUAGE_MAPPING[user_lang])
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info(translate_from_english("No learning data available yet.", LANGUAGE_MAPPING[user_lang]))
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        # Show badges
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Your Badges", LANGUAGE_MAPPING[user_lang]))
        badges = get_badges(st.session_state.user['id'])
        
        if badges:
            for badge_name, badge_description, earned_date in badges:
                badge_name_translated = translate_from_english(badge_name, LANGUAGE_MAPPING[user_lang])
                badge_desc_translated = translate_from_english(badge_description, LANGUAGE_MAPPING[user_lang])
                
                st.markdown(f'<div class="badge">{badge_name_translated}</div>', unsafe_allow_html=True)
                st.caption(f"{badge_desc_translated} - {earned_date.split()[0]}")
        else:
            st.info(translate_from_english("You haven't earned any badges yet. Keep learning!", LANGUAGE_MAPPING[user_lang]))
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show leaderboard
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader(translate_from_english("Top Learners", LANGUAGE_MAPPING[user_lang]))
        leaderboard = get_leaderboard()
        
        if leaderboard:
            for i, (name, grade, school, points) in enumerate(leaderboard):
                st.write(f"{i+1}. {name} ({translate_from_english('Grade', LANGUAGE_MAPPING[user_lang])} {grade}) - {points} {translate_from_english('points', LANGUAGE_MAPPING[user_lang])}")
                if name == st.session_state.user['name']:
                    st.success(translate_from_english("That's you!", LANGUAGE_MAPPING[user_lang]))
        else:
            st.info(translate_from_english("No leaderboard data available.", LANGUAGE_MAPPING[user_lang]))
        st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button(translate_from_english("Back to Dashboard", LANGUAGE_MAPPING[user_lang])):
        st.session_state.page = "dashboard"
        st.rerun()

def about_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('About Rural EduGamify', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    
    about_content = translate_from_english("""
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
    """, LANGUAGE_MAPPING[user_lang])
    
    st.markdown(f"<div class='card'>{about_content}</div>", unsafe_allow_html=True)
    
    # Team information
    st.markdown(f"<h3 class='sub-header'>{translate_from_english('Our Team', LANGUAGE_MAPPING[user_lang])}</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        team_content = translate_from_english("""
        <h4>Education Experts</h4>
        <p>Curriculum designers and teachers with experience in rural education</p>
        """, LANGUAGE_MAPPING[user_lang])
        st.markdown(f"<div class='card' style='text-align: center;'>{team_content}</div>", unsafe_allow_html=True)
    
    with col2:
        team_content = translate_from_english("""
        <h4>Technology Team</h4>
        <p>Software developers and AI specialists creating innovative learning solutions</p>
        """, LANGUAGE_MAPPING[user_lang])
        st.markdown(f"<div class='card' style='text-align: center;'>{team_content}</div>", unsafe_allow_html=True)
    
    with col3:
        team_content = translate_from_english("""
        <h4>Community Partners</h4>
        <p>Local organizations helping implement our platform in rural schools</p>
        """, LANGUAGE_MAPPING[user_lang])
        st.markdown(f"<div class='card' style='text-align: center;'>{team_content}</div>", unsafe_allow_html=True)

def contact_page():
    user_lang = st.session_state.user['language']
    st.markdown(f"<h1 class='main-header'>{translate_from_english('Contact Us', LANGUAGE_MAPPING[user_lang])}</h1>", unsafe_allow_html=True)
    
    contact_content = translate_from_english("""
    <h3>Get in Touch</h3>
    <p>We'd love to hear from you! Whether you have questions, feedback, or need support, please don't hesitate to reach out.</p>
    
    <h4>Contact Information:</h4>
    <p><b>Email:</b> support@ruraledugamify.org</p>
    <p><b>Phone:</b> +91-XXX-XXX-XXXX</p>
    <p><b>Address:</b> Electronics & IT Department, Government of Odisha, India</p>
    
    <h4>Send us a message:</h4>
    """, LANGUAGE_MAPPING[user_lang])
    
    st.markdown(f"<div class='card'>{contact_content}</div>", unsafe_allow_html=True)
    
    with st.form("contact_form"):
        name = st.text_input(translate_from_english("Your Name", LANGUAGE_MAPPING[user_lang]))
        email = st.text_input(translate_from_english("Your Email", LANGUAGE_MAPPING[user_lang]))
        message = st.text_area(translate_from_english("Your Message", LANGUAGE_MAPPING[user_lang]))
        submitted = st.form_submit_button(translate_from_english("Send Message", LANGUAGE_MAPPING[user_lang]))
        
        if submitted:
            st.success(translate_from_english("Thank you for your message! We'll get back to you soon.", LANGUAGE_MAPPING[user_lang]))

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
        user_lang = st.session_state.user['language']
        with st.sidebar:
            st.image("https://ideogram.ai/assets/image/lossless/response/Y4_3nbqYQOu7h4NNJjaPkw", use_column_width=True)
            welcome_text = translate_from_english(f"Welcome, {st.session_state.user['name']}!", LANGUAGE_MAPPING[user_lang])
            st.write(welcome_text)
            
            # Progress bar
            level_text = translate_from_english("Level 3", LANGUAGE_MAPPING[user_lang])
            st.markdown(f"<div class='progress-bar'><div class='progress-fill' style='width: 65%;'>{level_text}</div></div>", unsafe_allow_html=True)
            points_text = translate_from_english("EduPoints", LANGUAGE_MAPPING[user_lang])
            st.write(f"**{points_text}:** {st.session_state.user['points']}")
            
            st.divider()
            
            if st.button(translate_from_english("🏠 Dashboard", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "dashboard"
                st.rerun()
            if st.button(translate_from_english("📚 Study Subjects", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "subjects"
                st.rerun()
            if st.button(translate_from_english("💬 AI Tutor", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "chat"
                st.rerun()
            if st.button(translate_from_english("🎮 Educational Games", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "games"
                st.rerun()
            if st.button(translate_from_english("📥 Offline Content", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "offline"
                st.rerun()
            if st.button(translate_from_english("📊 Profile & Badges", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "profile"
                st.rerun()
            if st.button(translate_from_english("ℹ️ About", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "about"
                st.rerun()
            if st.button(translate_from_english("📞 Contact", LANGUAGE_MAPPING[user_lang])):
                st.session_state.page = "contact"
                st.rerun()
            if st.button(translate_from_english("🚪 Logout", LANGUAGE_MAPPING[user_lang])):
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
    elif st.session_state.page == "games":
        games_page()
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
