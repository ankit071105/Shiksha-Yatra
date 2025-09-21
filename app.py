# main.py
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json
import time
import random
import os
from pathlib import Path
import hashlib
import base64
import math
from PIL import Image
import io
import cv2
from streamlit_drawable_canvas import st_canvas

# Set page configuration
st.set_page_config(
    page_title="Rural EduGame Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
def init_db():
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  user_type TEXT,
                  grade INTEGER,
                  school TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create game progress table
    c.execute('''CREATE TABLE IF NOT EXISTS game_progress
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  game_name TEXT,
                  subject TEXT,
                  score INTEGER,
                  level INTEGER,
                  time_spent INTEGER,
                  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Create analytics table
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date TEXT,
                  engagement_score INTEGER,
                  improvement_rate REAL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# User authentication functions
def create_user(username, password, user_type, grade, school):
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password, user_type, grade, school) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed_password, user_type, grade, school))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def verify_user(username, password):
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user

# Game classes
class CircuitBuilder:
    def __init__(self, grade_level):
        self.grade_level = grade_level
        self.components = self.generate_components()
        self.correct_circuit = self.generate_correct_circuit()
        self.user_circuit = []
        self.score = 0
        self.dragged_component = None
        
    def generate_components(self):
        return [
            {"id": "battery", "name": "Battery", "image": "🔋", "description": "Power source for the circuit"},
            {"id": "bulb", "name": "Light Bulb", "image": "💡", "description": "Lights up when current flows"},
            {"id": "switch", "name": "Switch", "image": "🔘", "description": "Controls current flow (on/off)"},
            {"id": "resistor", "name": "Resistor", "image": "📏", "description": "Limits current flow"},
            {"id": "wire", "name": "Wire", "image": "➖", "description": "Connects components"}
        ]
    
    def generate_correct_circuit(self):
        if self.grade_level <= 8:
            return ["battery", "wire", "switch", "wire", "bulb", "wire", "battery"]
        else:
            return ["battery", "wire", "resistor", "wire", "switch", "wire", "bulb", "wire", "battery"]
    
    def add_component(self, component_id):
        self.user_circuit.append(component_id)
        
    def check_circuit(self):
        return self.user_circuit == self.correct_circuit
    
    def get_score(self):
        if self.check_circuit():
            self.score = 100
        else:
            # Partial credit based on how many components are in correct position
            correct_positions = sum(1 for i, comp in enumerate(self.user_circuit) 
                                  if i < len(self.correct_circuit) and comp == self.correct_circuit[i])
            self.score = int((correct_positions / len(self.correct_circuit)) * 100)
        return self.score

class PhysicsLab:
    def __init__(self, grade_level):
        self.grade_level = grade_level
        self.equipment = self.generate_equipment()
        self.experiments = self.generate_experiments()
        self.current_experiment = 0
        self.user_setup = []
        self.score = 0
        
    def generate_equipment(self):
        return [
            {"id": "spring", "name": "Spring", "image": "🔄", "description": "Measures force and extension"},
            {"id": "weights", "name": "Weights", "image": "⚖️", "description": "Standard masses for experiments"},
            {"id": "pendulum", "name": "Pendulum", "image": "⏲️", "description": "For timing oscillations"},
            {"id": "lens", "name": "Convex Lens", "image": "🔍", "description": "Focuses light rays"},
            {"id": "prism", "name": "Prism", "image": "🌈", "description": "Splits light into spectrum"},
            {"id": "magnet", "name": "Magnet", "image": "🧲", "description": "Creates magnetic field"}
        ]
    
    def generate_experiments(self):
        if self.grade_level <= 8:
            return [
                {
                    "name": "Hooke's Law Experiment",
                    "description": "Set up equipment to verify Hooke's Law: F = kx",
                    "correct_setup": ["spring", "weights", "weights", "weights"]
                },
                {
                    "name": "Simple Pendulum",
                    "description": "Set up a simple pendulum to measure time period",
                    "correct_setup": ["pendulum", "weights"]
                }
            ]
        else:
            return [
                {
                    "name": "Light Refraction",
                    "description": "Set up equipment to demonstrate light refraction through a prism",
                    "correct_setup": ["lens", "prism"]
                },
                {
                    "name": "Magnetic Field Mapping",
                    "description": "Set up equipment to map magnetic field lines",
                    "correct_setup": ["magnet", "magnet"]
                }
            ]
    
    def add_equipment(self, equipment_id):
        self.user_setup.append(equipment_id)
    
    def check_setup(self):
        return sorted(self.user_setup) == sorted(self.experiments[self.current_experiment]["correct_setup"])
    
    def get_score(self):
        if self.check_setup():
            self.score = 100
        else:
            # Calculate partial score
            correct_items = sum(1 for item in self.user_setup 
                              if item in self.experiments[self.current_experiment]["correct_setup"])
            total_items = len(self.experiments[self.current_experiment]["correct_setup"])
            self.score = int((correct_items / total_items) * 100)
        return self.score
    
    def next_experiment(self):
        if self.current_experiment < len(self.experiments) - 1:
            self.current_experiment += 1
            self.user_setup = []
            return True
        return False

class ChemistryLab:
    def __init__(self, grade_level):
        self.grade_level = grade_level
        self.elements = self.generate_elements()
        self.compounds = self.generate_compounds()
        self.current_reaction = 0
        self.user_elements = []
        self.score = 0
        
    def generate_elements(self):
        return [
            {"id": "H", "name": "Hydrogen", "image": "⚪", "description": "Atomic number 1"},
            {"id": "O", "name": "Oxygen", "image": "🔴", "description": "Atomic number 8"},
            {"id": "C", "name": "Carbon", "image": "⚫", "description": "Atomic number 6"},
            {"id": "Na", "name": "Sodium", "image": "🟠", "description": "Atomic number 11"},
            {"id": "Cl", "name": "Chlorine", "image": "🟢", "description": "Atomic number 17"}
        ]
    
    def generate_compounds(self):
        if self.grade_level <= 8:
            return [
                {
                    "name": "Water Formation",
                    "description": "Create water molecules from elements",
                    "correct_formula": ["H", "H", "O"]
                },
                {
                    "name": "Carbon Dioxide",
                    "description": "Create carbon dioxide molecules",
                    "correct_formula": ["C", "O", "O"]
                }
            ]
        else:
            return [
                {
                    "name": "Sodium Chloride",
                    "description": "Create table salt molecules",
                    "correct_formula": ["Na", "Cl"]
                },
                {
                    "name": "Glucose",
                    "description": "Create a glucose molecule",
                    "correct_formula": ["C", "C", "C", "C", "C", "C", "H", "H", "H", "H", "H", "H", "O", "O", "O", "O", "O", "O"]
                }
            ]
    
    def add_element(self, element_id):
        self.user_elements.append(element_id)
    
    def check_reaction(self):
        return sorted(self.user_elements) == sorted(self.compounds[self.current_reaction]["correct_formula"])
    
    def get_score(self):
        if self.check_reaction():
            self.score = 100
        else:
            # Calculate partial score
            correct_items = sum(1 for item in self.user_elements 
                              if item in self.compounds[self.current_reaction]["correct_formula"])
            total_items = len(self.compounds[self.current_reaction]["correct_formula"])
            self.score = int((correct_items / total_items) * 100)
        return self.score
    
    def next_reaction(self):
        if self.current_reaction < len(self.compounds) - 1:
            self.current_reaction += 1
            self.user_elements = []
            return True
        return False

class GeographyExplorer:
    def __init__(self, grade_level):
        self.grade_level = grade_level
        self.countries = self.generate_countries()
        self.capitals = self.generate_capitals()
        self.landmarks = self.generate_landmarks()
        self.current_mode = "countries"  # countries, capitals, or landmarks
        self.user_answers = {}
        self.score = 0
        
    def generate_countries(self):
        return ["India", "United States", "Japan", "Brazil", "Egypt", 
                "Australia", "Germany", "South Africa", "China", "Mexico"]
    
    def generate_capitals(self):
        return {
            "India": "New Delhi",
            "United States": "Washington D.C.",
            "Japan": "Tokyo",
            "Brazil": "Brasília",
            "Egypt": "Cairo",
            "Australia": "Canberra",
            "Germany": "Berlin",
            "South Africa": "Pretoria",
            "China": "Beijing",
            "Mexico": "Mexico City"
        }
    
    def generate_landmarks(self):
        return {
            "India": "Taj Mahal",
            "United States": "Statue of Liberty",
            "Japan": "Mount Fuji",
            "Brazil": "Christ the Redeemer",
            "Egypt": "Pyramids of Giza",
            "Australia": "Sydney Opera House",
            "Germany": "Brandenburg Gate",
            "South Africa": "Table Mountain",
            "China": "Great Wall",
            "Mexico": "Chichen Itza"
        }
    
    def set_mode(self, mode):
        self.current_mode = mode
        self.user_answers = {}
    
    def add_answer(self, question, answer):
        self.user_answers[question] = answer
    
    def check_answers(self):
        if self.current_mode == "countries":
            correct = 0
            for country in self.countries:
                if country in self.user_answers and self.user_answers[country] == self.capitals[country]:
                    correct += 1
            return correct / len(self.countries)
        elif self.current_mode == "capitals":
            correct = 0
            for capital in self.capitals.values():
                if capital in self.user_answers and self.user_answers[capital] in self.capitals and self.capitals[self.user_answers[capital]] == capital:
                    correct += 1
            return correct / len(self.capitals)
        else:  # landmarks
            correct = 0
            for country, landmark in self.landmarks.items():
                if country in self.user_answers and self.user_answers[country] == landmark:
                    correct += 1
            return correct / len(self.landmarks)
    
    def get_score(self):
        accuracy = self.check_answers()
        self.score = int(accuracy * 100)
        return self.score

class MathAdventure:
    def __init__(self, grade_level):
        self.grade_level = grade_level
        self.problems = self.generate_problems()
        self.current_problem = 0
        self.user_answers = {}
        self.score = 0
        
    def generate_problems(self):
        if self.grade_level <= 8:
            return [
                {
                    "question": "Solve for x: 2x + 5 = 15",
                    "type": "algebra",
                    "answer": "5",
                    "hint": "Subtract 5 from both sides first"
                },
                {
                    "question": "What is the area of a circle with radius 7cm?",
                    "type": "geometry",
                    "answer": "153.94",
                    "hint": "Use the formula πr²"
                },
                {
                    "question": "If a train travels 120 km in 2 hours, what is its speed?",
                    "type": "word",
                    "answer": "60",
                    "hint": "Speed = Distance / Time"
                }
            ]
        else:
            return [
                {
                    "question": "Solve the quadratic equation: x² - 5x + 6 = 0",
                    "type": "algebra",
                    "answer": "2,3",
                    "hint": "Factor the equation"
                },
                {
                    "question": "Find the derivative of f(x) = 3x² + 2x - 5",
                    "type": "calculus",
                    "answer": "6x+2",
                    "hint": "Use the power rule"
                },
                {
                    "question": "What is the probability of getting a sum of 7 when rolling two dice?",
                    "type": "statistics",
                    "answer": "0.1667",
                    "hint": "Count the favorable outcomes divided by total outcomes"
                }
            ]
    
    def check_answer(self, answer):
        correct_answer = self.problems[self.current_problem]["answer"]
        # Allow for multiple formats of the same answer
        if "," in correct_answer:
            correct_answers = [a.strip() for a in correct_answer.split(",")]
            user_answers = [a.strip() for a in answer.split(",")]
            return sorted(user_answers) == sorted(correct_answers)
        else:
            return answer.strip() == correct_answer
    
    def next_problem(self):
        if self.current_problem < len(self.problems) - 1:
            self.current_problem += 1
            return True
        return False
    
    def get_score(self):
        correct = sum(1 for i in range(len(self.problems)) 
                     if str(i) in self.user_answers and 
                     self.check_answer(self.user_answers[str(i)]))
        self.score = int((correct / len(self.problems)) * 100)
        return self.score

# Analytics functions
def save_game_progress(user_id, game_name, subject, score, level, time_spent):
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    c.execute("INSERT INTO game_progress (user_id, game_name, subject, score, level, time_spent) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, game_name, subject, score, level, time_spent))
    conn.commit()
    conn.close()

def get_user_progress(user_id):
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    c.execute("SELECT game_name, subject, score, level, completed_at FROM game_progress WHERE user_id = ? ORDER BY completed_at DESC", (user_id,))
    progress = c.fetchall()
    conn.close()
    return progress

def get_class_progress(teacher_id):
    conn = sqlite3.connect('edu_game.db')
    c = conn.cursor()
    c.execute("""
        SELECT u.username, g.game_name, g.subject, AVG(g.score), COUNT(g.id)
        FROM game_progress g
        JOIN users u ON g.user_id = u.id
        WHERE u.user_type = 'student'
        GROUP BY u.username, g.game_name, g.subject
    """)
    progress = c.fetchall()
    conn.close()
    return progress

# ML functions for analytics
def analyze_student_performance(user_id):
    conn = sqlite3.connect('edu_game.db')
    df = pd.read_sql_query("SELECT game_name, subject, score, level, time_spent FROM game_progress WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    
    if df.empty:
        return "No data available for analysis"
    
    # Simple analysis
    avg_score = df['score'].mean()
    total_time = df['time_spent'].sum()
    favorite_subject = df['subject'].mode()[0] if not df['subject'].mode().empty else "None"
    
    analysis = f"""
    Performance Analysis:
    - Average Score: {avg_score:.2f}/100
    - Total Time Spent: {total_time} minutes
    - Favorite Subject: {favorite_subject}
    
    Recommendations:
    - Focus on subjects where scores are lower
    - Try to maintain consistent study time
    - Revisit completed games to improve scores
    """
    
    return analysis

# CSS for drag and drop
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Create CSS file for drag and drop
css_content = """
.draggable {
    cursor: move;
    padding: 10px;
    margin: 5px;
    border: 2px solid #4CAF50;
    border-radius: 5px;
    background-color: #f9f9f9;
    display: inline-block;
}

.dropzone {
    min-height: 100px;
    border: 2px dashed #ccc;
    border-radius: 5px;
    padding: 10px;
    margin: 10px 0;
}

.dropzone.active {
    border-color: #4CAF50;
    background-color: #f0fff0;
}

.game-container {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    background-color: #f8f9fa;
}

.component-palette {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 20px;
}

.lab-bench {
    min-height: 200px;
    border: 2px dashed #007bff;
    border-radius: 5px;
    padding: 15px;
    margin: 15px 0;
    background-color: #e9ecef;
}
"""

with open("style.css", "w") as f:
    f.write(css_content)

local_css("style.css")

# Main application
def main():
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_game' not in st.session_state:
        st.session_state.current_game = None
    if 'game_state' not in st.session_state:
        st.session_state.game_state = None
    
    # Sidebar for navigation
    st.sidebar.title("🎓 Rural EduGame Platform")
    
    if st.session_state.user is None:
        # Login/Signup section
        auth_option = st.sidebar.selectbox("Select Option", ["Login", "Sign Up"])
        
        if auth_option == "Login":
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            if st.sidebar.button("Login"):
                user = verify_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password")
        
        else:  # Sign Up
            st.sidebar.subheader("Create Account")
            new_username = st.sidebar.text_input("Choose Username")
            new_password = st.sidebar.text_input("Choose Password", type="password")
            user_type = st.sidebar.selectbox("User Type", ["student", "teacher"])
            grade = st.sidebar.selectbox("Grade", range(6, 13)) if user_type == "student" else None
            school = st.sidebar.text_input("School Name")
            
            if st.sidebar.button("Create Account"):
                if create_user(new_username, new_password, user_type, grade, school):
                    st.sidebar.success("Account created successfully. Please login.")
                else:
                    st.sidebar.error("Username already exists")
    
    else:
        # User is logged in
        user_id, username, _, user_type, grade, school, _ = st.session_state.user
        
        st.sidebar.write(f"Welcome, {username}!")
        st.sidebar.write(f"Type: {user_type.capitalize()}")
        if user_type == "student":
            st.sidebar.write(f"Grade: {grade}")
        st.sidebar.write(f"School: {school}")
        
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.session_state.current_game = None
            st.session_state.game_state = None
            st.rerun()
        
        # Navigation based on user type
        if user_type == "student":
            menu_options = ["Dashboard", "Circuit Builder", "Physics Lab", "Chemistry Lab", 
                           "Geography Explorer", "Math Adventure", "My Progress"]
        else:
            menu_options = ["Dashboard", "Class Analytics", "Student Reports"]
        
        choice = st.sidebar.selectbox("Menu", menu_options)
        
        # Main content area
        if choice == "Dashboard":
            st.title("🎓 Gamified Learning Platform for Rural Education")
            st.subheader("Welcome to your personalized learning dashboard!")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info("📚 Subjects Covered")
                st.write("- Mathematics")
                st.write("- Physics")
                st.write("- Chemistry")
                st.write("- Geography")
            
            with col2:
                st.info("🎮 Learning Games")
                st.write("- Circuit Builder (Physics)")
                st.write("- Physics Lab (Physics)")
                st.write("- Chemistry Lab (Chemistry)")
                st.write("- Geography Explorer (Geography)")
                st.write("- Math Adventure (Mathematics)")
            
            with col3:
                st.info("🏆 Your Progress")
                progress = get_user_progress(user_id)
                if progress:
                    st.write(f"Games Completed: {len(progress)}")
                    avg_score = sum(p[2] for p in progress) / len(progress)
                    st.write(f"Average Score: {avg_score:.1f}%")
                else:
                    st.write("No games completed yet")
            
            if user_type == "student":
                st.subheader("Recommended For You")
                rec_col1, rec_col2 = st.columns(2)
                
                with rec_col1:
                    st.write("**Based on your grade level:**")
                    if grade <= 8:
                        st.write("- Try Circuit Builder to learn about electricity")
                        st.write("- Explore the Chemistry Lab")
                    else:
                        st.write("- Challenge yourself with Physics Lab")
                        st.write("- Test your knowledge with Math Adventure")
                
                with rec_col2:
                    st.write("**Popular among students:**")
                    st.write("- Circuit Builder - build working circuits")
                    st.write("- Chemistry Lab - create chemical compounds")
        
        elif choice == "Circuit Builder":
            st.title("🔌 Circuit Builder")
            st.write("Build electrical circuits by dragging components to the workspace!")
            
            if st.session_state.current_game != "Circuit Builder":
                st.session_state.current_game = "Circuit Builder"
                st.session_state.game_state = CircuitBuilder(grade)
                st.rerun()
            
            game = st.session_state.game_state
            
            st.markdown("### Available Components")
            st.markdown("<div class='component-palette'>", unsafe_allow_html=True)
            
            cols = st.columns(len(game.components))
            for i, component in enumerate(game.components):
                with cols[i]:
                    if st.button(f"{component['image']} {component['name']}", key=f"comp_{component['id']}"):
                        game.add_component(component['id'])
                        st.rerun()
                    st.caption(component['description'])
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("### Your Circuit")
            st.markdown("<div class='lab-bench'>", unsafe_allow_html=True)
            
            if game.user_circuit:
                circuit_display = " → ".join([next(comp['image'] for comp in game.components if comp['id'] == c) for c in game.user_circuit])
                st.markdown(f"<h3 style='text-align: center;'>{circuit_display}</h3>", unsafe_allow_html=True)
                
                # Show component names
                component_names = " → ".join([next(comp['name'] for comp in game.components if comp['id'] == c) for c in game.user_circuit])
                st.markdown(f"<p style='text-align: center;'>{component_names}</p>", unsafe_allow_html=True)
            else:
                st.info("No components added yet. Click on components above to build your circuit!")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("Test Circuit"):
                score = game.get_score()
                if score == 100:
                    st.success("🎉 Congratulations! Your circuit works perfectly!")
                    st.balloons()
                    
                    # Visual effect for working circuit
                    if "battery" in game.user_circuit and "bulb" in game.user_circuit:
                        st.markdown("<h2 style='text-align: center; color: yellow;'>💡 Light Bulb Glowing!</h2>", unsafe_allow_html=True)
                else:
                    st.warning(f"Your circuit is {score}% correct. Try again!")
                
                save_game_progress(user_id, "Circuit Builder", "Physics", score, grade, 10)
                
                if st.button("Build New Circuit"):
                    st.session_state.game_state = CircuitBuilder(grade)
                    st.rerun()
        
        elif choice == "Physics Lab":
            st.title("🔬 Physics Laboratory")
            st.write("Conduct physics experiments by setting up equipment correctly!")
            
            if st.session_state.current_game != "Physics Lab":
                st.session_state.current_game = "Physics Lab"
                st.session_state.game_state = PhysicsLab(grade)
                st.rerun()
            
            game = st.session_state.game_state
            experiment = game.experiments[game.current_experiment]
            
            st.markdown(f"### Experiment: {experiment['name']}")
            st.write(experiment['description'])
            
            st.markdown("### Available Equipment")
            st.markdown("<div class='component-palette'>", unsafe_allow_html=True)
            
            cols = st.columns(len(game.equipment))
            for i, equipment in enumerate(game.equipment):
                with cols[i]:
                    if st.button(f"{equipment['image']} {equipment['name']}", key=f"equip_{equipment['id']}"):
                        game.add_equipment(equipment['id'])
                        st.rerun()
                    st.caption(equipment['description'])
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("### Your Experiment Setup")
            st.markdown("<div class='lab-bench'>", unsafe_allow_html=True)
            
            if game.user_setup:
                setup_display = " + ".join([next(equip['image'] for equip in game.equipment if equip['id'] == e) for e in game.user_setup])
                st.markdown(f"<h3 style='text-align: center;'>{setup_display}</h3>", unsafe_allow_html=True)
                
                # Show equipment names
                equipment_names = " + ".join([next(equip['name'] for equip in game.equipment if equip['id'] == e) for e in game.user_setup])
                st.markdown(f"<p style='text-align: center;'>{equipment_names}</p>", unsafe_allow_html=True)
            else:
                st.info("No equipment added yet. Click on equipment above to set up your experiment!")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("Run Experiment"):
                score = game.get_score()
                if score == 100:
                    st.success("🎉 Congratulations! Your experiment was successful!")
                    st.balloons()
                    
                    # Show experiment result visualization
                    if game.current_experiment == 0:  # Hooke's Law
                        st.line_chart(pd.DataFrame({
                            'Force (N)': [1, 2, 3, 4, 5],
                            'Extension (cm)': [2, 4, 6, 8, 10]
                        }))
                        st.caption("Hooke's Law: Force vs Extension")
                    
                else:
                    st.warning(f"Your experiment is {score}% correct. Try again!")
                
                save_game_progress(user_id, "Physics Lab", "Physics", score, grade, 15)
                
                if score == 100 and game.next_experiment():
                    st.info("Moving to the next experiment!")
                    st.rerun()
                
                if st.button("Reset Experiment"):
                    st.session_state.game_state = PhysicsLab(grade)
                    st.rerun()
        
        elif choice == "Chemistry Lab":
            st.title("🧪 Chemistry Laboratory")
            st.write("Create chemical compounds by combining elements!")
            
            if st.session_state.current_game != "Chemistry Lab":
                st.session_state.current_game = "Chemistry Lab"
                st.session_state.game_state = ChemistryLab(grade)
                st.rerun()
            
            game = st.session_state.game_state
            compound = game.compounds[game.current_reaction]
            
            st.markdown(f"### Compound: {compound['name']}")
            st.write(compound['description'])
            
            st.markdown("### Available Elements")
            st.markdown("<div class='component-palette'>", unsafe_allow_html=True)
            
            cols = st.columns(len(game.elements))
            for i, element in enumerate(game.elements):
                with cols[i]:
                    if st.button(f"{element['image']} {element['name']}", key=f"elem_{element['id']}"):
                        game.add_element(element['id'])
                        st.rerun()
                    st.caption(element['description'])
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("### Your Chemical Formula")
            st.markdown("<div class='lab-bench'>", unsafe_allow_html=True)
            
            if game.user_elements:
                formula_display = " + ".join([next(elem['image'] for elem in game.elements if elem['id'] == e) for e in game.user_elements])
                st.markdown(f"<h3 style='text-align: center;'>{formula_display}</h3>", unsafe_allow_html=True)
                
                # Show element symbols
                element_symbols = " + ".join(game.user_elements)
                st.markdown(f"<p style='text-align: center;'>{element_symbols}</p>", unsafe_allow_html=True)
            else:
                st.info("No elements added yet. Click on elements above to create your compound!")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("Create Compound"):
                score = game.get_score()
                if score == 100:
                    st.success("🎉 Congratulations! You created the correct compound!")
                    st.balloons()
                    
                    # Show compound visualization
                    if compound['name'] == "Water Formation":
                        st.markdown("<h3 style='text-align: center; color: blue;'>H₂O - Water</h3>", unsafe_allow_html=True)
                        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Water_molecule_3D.svg/1200px-Water_molecule_3D.svg.png", 
                                width=200, caption="Water Molecule")
                    
                else:
                    st.warning(f"Your compound is {score}% correct. Try again!")
                
                save_game_progress(user_id, "Chemistry Lab", "Chemistry", score, grade, 15)
                
                if score == 100 and game.next_reaction():
                    st.info("Moving to the next compound!")
                    st.rerun()
                
                if st.button("Reset Reaction"):
                    st.session_state.game_state = ChemistryLab(grade)
                    st.rerun()
        
        elif choice == "Geography Explorer":
            st.title("🌍 Geography Explorer")
            st.write("Test your knowledge of countries, capitals, and landmarks!")
            
            if st.session_state.current_game != "Geography Explorer":
                st.session_state.current_game = "Geography Explorer"
                st.session_state.game_state = GeographyExplorer(grade)
                st.rerun()
            
            game = st.session_state.game_state
            
            st.markdown("### Select Game Mode")
            mode = st.radio("Choose mode:", ["Countries to Capitals", "Capitals to Countries", "Countries to Landmarks"])
            
            if mode == "Countries to Capitals":
                game.set_mode("countries")
                st.markdown("#### Match Countries with their Capitals")
                
                for country in game.countries:
                    capital_options = [""] + list(game.capitals.values())
                    selected = st.selectbox(f"Capital of {country}", options=capital_options, 
                                          key=f"cap_{country}")
                    game.add_answer(country, selected)
            
            elif mode == "Capitals to Countries":
                game.set_mode("capitals")
                st.markdown("#### Match Capitals with their Countries")
                
                for capital in game.capitals.values():
                    country_options = [""] + list(game.capitals.keys())
                    selected = st.selectbox(f"Country for {capital}", options=country_options,
                                          key=f"country_{capital}")
                    game.add_answer(capital, selected)
            
            else:  # Countries to Landmarks
                game.set_mode("landmarks")
                st.markdown("#### Match Countries with their Famous Landmarks")
                
                for country in game.countries:
                    landmark_options = [""] + list(game.landmarks.values())
                    selected = st.selectbox(f"Landmark in {country}", options=landmark_options,
                                          key=f"land_{country}")
                    game.add_answer(country, selected)
            
            if st.button("Check Answers"):
                score = game.get_score()
                if score == 100:
                    st.success("🎉 Perfect! You know your geography!")
                    st.balloons()
                else:
                    st.warning(f"You scored {score}%. Good try!")
                
                save_game_progress(user_id, "Geography Explorer", "Geography", score, grade, 10)
                
                if st.button("Play Again"):
                    st.session_state.game_state = GeographyExplorer(grade)
                    st.rerun()
        
        elif choice == "Math Adventure":
            st.title("🧮 Math Adventure")
            st.write("Solve mathematical problems and challenges!")
            
            if st.session_state.current_game != "Math Adventure":
                st.session_state.current_game = "Math Adventure"
                st.session_state.game_state = MathAdventure(grade)
                st.rerun()
            
            game = st.session_state.game_state
            problem = game.problems[game.current_problem]
            
            st.markdown(f"### Problem {game.current_problem + 1} of {len(game.problems)}")
            st.markdown(f"**{problem['question']}**")
            st.caption(f"Hint: {problem['hint']}")
            
            answer = st.text_input("Your answer:", key=f"math_prob_{game.current_problem}")
            
            if answer:
                game.user_answers[str(game.current_problem)] = answer
                
                if st.button("Check Answer"):
                    if game.check_answer(answer):
                        st.success("✅ Correct! Well done!")
                        
                        if game.next_problem():
                            st.info("Moving to the next problem!")
                            st.rerun()
                        else:
                            # All problems completed
                            score = game.get_score()
                            st.success(f"🎉 You completed all problems with a score of {score}%!")
                            save_game_progress(user_id, "Math Adventure", "Mathematics", score, grade, 15)
                            
                            if st.button("Play Again"):
                                st.session_state.game_state = MathAdventure(grade)
                                st.rerun()
                    else:
                        st.error("❌ Incorrect. Try again!")
        
        elif choice == "My Progress":
            st.title("📊 My Learning Progress")
            progress = get_user_progress(user_id)
            
            if progress:
                st.subheader("Game Performance")
                df = pd.DataFrame(progress, columns=["Game", "Subject", "Score", "Level", "Date"])
                
                # Show recent activity
                st.dataframe(df.head(10))
                
                # Show charts
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Scores by Subject")
                    subject_scores = df.groupby("Subject")["Score"].mean()
                    st.bar_chart(subject_scores)
                
                with col2:
                    st.subheader("Progress Over Time")
                    df['Date'] = pd.to_datetime(df['Date'])
                    time_series = df.set_index('Date')['Score']
                    st.line_chart(time_series)
                
                # Performance analysis
                st.subheader("Performance Analysis")
                analysis = analyze_student_performance(user_id)
                st.write(analysis)
            else:
                st.info("You haven't completed any games yet. Play some games to see your progress here!")
        
        elif choice == "Class Analytics" and user_type == "teacher":
            st.title("👨‍🏫 Class Analytics")
            progress = get_class_progress(user_id)
            
            if progress:
                df = pd.DataFrame(progress, columns=["Student", "Game", "Subject", "Avg Score", "Games Played"])
                
                st.subheader("Overall Class Performance")
                st.dataframe(df)
                
                st.subheader("Average Scores by Subject")
                subject_avg = df.groupby("Subject")["Avg Score"].mean()
                st.bar_chart(subject_avg)
                
                st.subheader("Student Engagement")
                engagement = df.groupby("Student")["Games Played"].sum()
                st.bar_chart(engagement)
            else:
                st.info("No student data available yet.")
        
        elif choice == "Student Reports" and user_type == "teacher":
            st.title("📝 Individual Student Reports")
            
            # Get list of students
            conn = sqlite3.connect('edu_game.db')
            c = conn.cursor()
            c.execute("SELECT id, username, grade FROM users WHERE user_type = 'student'")
            students = c.fetchall()
            conn.close()
            
            if students:
                student_options = [f"{s[1]} (Grade {s[2]})" for s in students]
                selected_student = st.selectbox("Select Student", student_options)
                
                if selected_student:
                    student_id = students[student_options.index(selected_student)][0]
                    progress = get_user_progress(student_id)
                    
                    if progress:
                        st.subheader(f"Progress Report for {selected_student}")
                        df = pd.DataFrame(progress, columns=["Game", "Subject", "Score", "Level", "Date"])
                        st.dataframe(df)
                        
                        # Show analysis
                        analysis = analyze_student_performance(student_id)
                        st.write(analysis)
                    else:
                        st.info("This student hasn't completed any games yet.")
            else:
                st.info("No students registered yet.")

if __name__ == "__main__":
    main()