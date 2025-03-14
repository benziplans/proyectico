#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 12:27:31 2025

@author: rodrigo
"""

import sqlite3
import logging

# Setup logging (consistent with other scripts)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

# Database configuration
DB_PATH = "training_data.db"

# Constants for day ordering and scheduling
DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6, "Sunday": 7}
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Training goals and their associated distances (in km, None for non-distance goals)
GOALS = {
    "Marathon": 42.195, "Half Marathon": 21.1, "10K": 10, "5K": 5, "Hyrox": 8.0,
    "Muscle Gains": None, "Stay Lean": None, "Lose Weight": None
}

# User experience levels
EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Available equipment options
EQUIPMENT_OPTIONS = [
    "gym", "dumbbells", "barbell", "bench", "bodyweight", "none", "skierg", "sled", 
    "rower", "sandbag", "wallball", "kettlebell", "treadmill", "pool"
]

# Muscle groups for focus in training plans
MUSCLE_GROUPS = [
    "chest", "back", "legs", "arms", "shoulders", "core", "glutes", "full body", "biceps", "triceps"
]

# Units for distance and weight measurements
DISTANCE_UNITS = ["km", "miles"]
WEIGHT_UNITS = ["kg", "lbs"]

# Default training periods (in weeks) by experience level and goal
TRAINING_PERIODS = {
    "Beginner": {"Marathon": 24, "Half Marathon": 20, "10K": 16, "5K": 12, "Hyrox": 16, "Muscle Gains": 12, "Stay Lean": 12, "Lose Weight": 16},
    "Intermediate": {"Marathon": 20, "Half Marathon": 16, "10K": 12, "5K": 10, "Hyrox": 12, "Muscle Gains": 12, "Stay Lean": 12, "Lose Weight": 12},
    "Advanced": {"Marathon": 16, "Half Marathon": 12, "10K": 8, "5K": 6, "Hyrox": 10, "Muscle Gains": 12, "Stay Lean": 10, "Lose Weight": 10}
}

# Exercise substitution options for adaptability
EXERCISE_SUBSTITUTES = {
    "Squat": ["Lunges", "Leg Press"],
    "Bench": ["Push-ups", "Dumbbell Press"],
    "Deadlift": ["Romanian Deadlift", "Back Extensions"],
    "Squats": ["Lunges", "Leg Press"],
    "Bench Press": ["Push-ups", "Dumbbell Press"],
    "Overhead Press": ["Dumbbell Shoulder Press", "Pike Push-ups"],
    "Bent-Over Rows": ["Seated Rows", "Pull-ups"]
}

# Hyrox-specific stations (name, category, equipment, base_value, unit, description, youtube_link)
HYROX_STATIONS = [
    ("SkiErg", "endurance", "skierg", 1000, "m", "Simulates cross-country skiing, full-body cardio exercise.", "https://www.youtube.com/watch?v=elD1BQu71U4"),
    ("Sled Push", "strength", "sled", 50, "m", "Push a weighted sled for power and lower-body endurance.", "https://www.youtube.com/watch?v=YEtE3wEpxhE"),
    ("Sled Pull", "strength", "sled", 50, "m", "Pull a weighted sled using a rope, focusing on upper-body strength.", "https://www.youtube.com/watch?v=y5cX0uHeHTE"),
    ("Burpee Broad Jumps", "strength", "bodyweight", 80, "m", "Perform burpees with explosive forward jumps.", "https://www.youtube.com/watch?v=n_5A4qHp5GQ"),
    ("Rowing", "endurance", "rower", 1000, "m", "Use a rowing machine for full-body endurance work.", "https://www.youtube.com/watch?v=3DsF9BaYbJA"),
    ("Farmer’s Carry", "strength", "kettlebell", 100, "m", "Carry heavy kettlebells for grip, core, and leg endurance.", "https://www.youtube.com/watch?v=6t7T5mQ_r6E"),
    ("Sandbag Lunges", "strength", "sandbag", 100, "m", "Perform walking lunges while carrying a sandbag.", "https://www.youtube.com/watch?v=-Y93JkFhDvw"),
    ("Wall Balls", "strength", "wallball", 100, "reps", "Squat and throw a medicine ball to a target repeatedly.", "https://www.youtube.com/watch?v=FYwr_Wpfrjw"),
    ("Swimming", "recovery", "pool", 500, "m", "Low-impact recovery exercise to improve endurance.", "https://www.youtube.com/watch?v=0Xh9vH_NKkw")
]

# General exercises (name, category, equipment, description, goal_tag, muscle_group, youtube_link)
EXERCISES = [
    # Legs
    ("Squats", "strength", "barbell", "Lower hips with a barbell, then stand.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=Dy28eq2PjcM"),
    ("Leg Press", "strength", "gym", "Push weight away with legs on a machine.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=IZxyjW7LWks"),
    ("Lunges", "strength", "dumbbells", "Step forward and lower one knee.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=QOVaHwm-Q6U"),
    ("Step-Ups", "strength", "bench", "Step onto a bench with weight.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=zvZHgjnl0u8"),
    ("Leg Extensions", "strength", "gym", "Extend legs against resistance.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=YyvSfVjQeL0"),
    ("Calf Raises", "strength", "dumbbells", "Raise heels off ground.", "Muscle Gains", "legs", "https://www.youtube.com/watch?v=3YFixsW1R8g"),
    # Glutes
    ("Hip Thrusts", "strength", "barbell", "Thrust hips upward with weight on lap.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=LNvEkoxk-w8"),
    ("Glute Bridges", "strength", "bodyweight", "Lift hips from ground.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=8bbE64NuDTU"),
    ("Romanian Deadlifts", "strength", "barbell", "Hinge at hips with weight.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=JCXUYuzwNrM"),
    ("Bulgarian Split Squats", "strength", "dumbbells", "Lunge with back foot elevated.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=2C-uNgXrS1k"),
    ("Donkey Kicks", "strength", "bodyweight", "Kick leg back from all fours.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=SJ1Xuz9D41Q"),
    ("Cable Kickbacks", "strength", "gym", "Kick leg back with cable resistance.", "Muscle Gains", "glutes", "https://www.youtube.com/watch?v=5s8l_NtWoA0"),
    # Core
    ("Plank", "strength", "bodyweight", "Hold push-up position with elbows bent.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=pSHjTRCQxIw"),
    ("Russian Twists", "strength", "dumbbells", "Twist torso with weight.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=wkD8rjkodUI"),
    ("Hanging Leg Raises", "strength", "gym", "Raise legs while hanging.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=Pr1-mMjR6kk"),
    ("Bicycle Crunches", "strength", "bodyweight", "Alternate elbow to knee.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=9FGilxCbdz8"),
    ("Dead Bug", "strength", "bodyweight", "Extend opposite arm and leg.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=8v0pLPn_6lQ"),
    ("Cable Woodchoppers", "strength", "gym", "Rotate torso with cable.", "Muscle Gains", "core", "https://www.youtube.com/watch?v=5L6eNk9H8sY"),
    # Chest
    ("Bench Press", "strength", "barbell", "Push barbell up from chest on bench.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=vcBig73ojpE"),
    ("Incline Bench Press", "strength", "barbell", "Press barbell on an incline.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=SrqOu55lrYU"),
    ("Dumbbell Flys", "strength", "dumbbells", "Open arms with weights.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=eozdVDA78K0"),
    ("Chest Dips", "strength", "gym", "Lower body between parallel bars.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=2z8JmcrW-As"),
    ("Push-Ups", "strength", "bodyweight", "Push body up from ground.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=IODxDxX7oi4"),
    ("Cable Crossovers", "strength", "gym", "Pull cables across chest.", "Muscle Gains", "chest", "https://www.youtube.com/watch?v=taI4XAnRqs4"),
    # Shoulders
    ("Overhead Press", "strength", "barbell", "Press barbell overhead.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=F3QY5vMz_6I"),
    ("Lateral Raises", "strength", "dumbbells", "Raise arms to sides.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=3VcKaXpzqRo"),
    ("Front Raises", "strength", "dumbbells", "Raise arms forward.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=-t7fuZ0KhDA"),
    ("Arnold Press", "strength", "dumbbells", "Rotate and press dumbbells overhead.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=6Z15_WdXmVw"),
    ("Face Pulls", "strength", "gym", "Pull cable towards face.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=H8HeV1mIQz0"),
    ("Shrugs", "strength", "dumbbells", "Lift shoulders with weight.", "Muscle Gains", "shoulders", "https://www.youtube.com/watch?v=cJRVVxmytaM"),
    # Back
    ("Deadlift", "strength", "barbell", "Lift barbell from ground to hips.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=rT7DgCr-3_I"),
    ("Pull-Ups", "strength", "gym", "Pull body up on a bar.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=eGo4IYlbE5g"),
    ("Bent-Over Rows", "strength", "barbell", "Row barbell to torso.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=pgGixv0R49k"),
    ("Lat Pulldowns", "strength", "gym", "Pull cable down to chest.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=pYcpY20QaE8"),
    ("Single-Arm Dumbbell Rows", "strength", "dumbbells", "Row one dumbbell to side.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=pYcpY20QaE8"),
    ("Reverse Flys", "strength", "dumbbells", "Raise arms backward.", "Muscle Gains", "back", "https://www.youtube.com/watch?v=2-LAMcpzODU"),
    # Biceps
    ("Barbell Curls", "strength", "barbell", "Curl barbell up to shoulders.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=kwG2ipFRgfo"),
    ("Dumbbell Curls", "strength", "dumbbells", "Curl dumbbells up to shoulders.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=sAq_ocpRh_I"),
    ("Hammer Curls", "strength", "dumbbells", "Curl dumbbells with neutral grip.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=TwD-YGVPceI"),
    ("Preacher Curls", "strength", "gym", "Curl weight on a preacher bench.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=fIWP-FRFNU0"),
    ("Concentration Curls", "strength", "dumbbells", "Curl dumbbell while seated.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=Jvj2wBcqMZg"),
    ("Chin-Ups", "strength", "gym", "Pull body up with palms facing you.", "Muscle Gains", "biceps", "https://www.youtube.com/watch?v=mRznU6wJzdA"),
    # Triceps
    ("Tricep Dips", "strength", "gym", "Lower body on parallel bars.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=2z8JmcrW-As"),
    ("Overhead Tricep Extension", "strength", "dumbbells", "Extend weight overhead.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=-Vyt2QdsR7E"),
    ("Close-Grip Bench Press", "strength", "barbell", "Press barbell with narrow grip.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=8wEJ1qDqdhI"),
    ("Tricep Pushdowns", "strength", "gym", "Push cable down with straight bar.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=2-LAMcpzODU"),
    ("Skull Crushers", "strength", "barbell", "Lower barbell to forehead.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=d_KZxkY_0LE"),
    ("Diamond Push-Ups", "strength", "bodyweight", "Push up with hands in diamond shape.", "Muscle Gains", "triceps", "https://www.youtube.com/watch?v=ZKHQG-uFU2Q"),
    # Other goals
    ("Long Run", "endurance", "none", "Run at a steady pace.", "Marathon", "legs", "https://www.youtube.com/watch?v=MWdGxmW6NHw"),
    ("Tempo Run", "cardio", "none", "Run at a challenging pace.", "Half Marathon", "legs", "https://www.youtube.com/watch?v=Au-8JTYvf0M"),
    ("Intervals", "cardio", "treadmill", "Alternate fast running with recovery.", "10K", "legs", "https://www.youtube.com/watch?v=7eQ35TQX_n8"),
    ("Easy Run", "endurance", "none", "Run at a comfortable pace.", "5K", "legs", "https://www.youtube.com/watch?v=9L2whRXbg-A"),
    ("Rowing", "endurance", "rower", "Row on a machine.", "Hyrox", "full body", "https://www.youtube.com/watch?v=3DsF9BaYbJA"),
    ("Wall Balls", "strength", "wallball", "Squat and throw a ball.", "Hyrox", "legs", "https://www.youtube.com/watch?v=FYwr_Wpfrjw"),
    ("Hill Sprints", "cardio", "none", "Short, intense uphill sprints.", "Stay Lean", "legs", "https://www.youtube.com/watch?v=6QwKDJRrKHA"),
    ("Circuit Training", "strength", "dumbbells", "Cycle through exercises.", "Stay Lean", "full body", "https://www.youtube.com/watch?v=YXGQiW8lQZM"),
    ("Jump Rope", "cardio", "none", "Jump continuously over a rope.", "Lose Weight", "full body", "https://www.youtube.com/watch?v=0KzX8lQ24"),
    ("Burpees", "strength", "bodyweight", "Jump squat followed by push-up.", "Lose Weight", "full body", "https://www.youtube.com/watch?v=TU8QYVW0gDU"),
]

# Database connection singleton
class DBConnection:
    """Singleton class for managing a single SQLite database connection."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance.conn = sqlite3.connect(DB_PATH, timeout=10)
                cls._instance.conn.execute("PRAGMA journal_mode=WAL;")
                logging.info(f"Database connection established at {DB_PATH}")
            except sqlite3.OperationalError as e:
                logging.error(f"Database connection failed: {e}")
                raise
        return cls._instance
    
    def get_cursor(self):
        """Return a cursor for database operations."""
        return self.conn.cursor()
    
    def commit(self):
        """Commit changes to the database."""
        self.conn.commit()
    
    def rollback(self):
        """Rollback changes in case of an error."""
        self.conn.rollback()

def connect_db():
    """Create a new database connection (legacy function, prefer DBConnection)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        logging.info(f"Legacy database connection created at {DB_PATH}")
        return conn
    except sqlite3.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise

def setup_database(conn, cursor, reset: bool = False):
    """Initialize or reset the SQLite database schema."""
    try:
        if reset:
            logging.warning("Resetting database - all existing data will be dropped!")
            cursor.executescript("""
                DROP TABLE IF EXISTS plans;
                DROP TABLE IF EXISTS training_plans;
                DROP TABLE IF EXISTS users;
                DROP TABLE IF EXISTS exercises;
                DROP TABLE IF EXISTS user_equipment;
                DROP TABLE IF EXISTS feedback;
                DROP TABLE IF EXISTS user_muscle_focus;
                DROP TABLE IF EXISTS user_starting_weights;
            """)

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT,
                satisfaction INTEGER,
                comments TEXT,
                progress_weights TEXT,
                weight_unit TEXT,
                trained_until TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (plan_id) REFERENCES plans(plan_id)
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                email TEXT NOT NULL,  -- Added email column
                goal TEXT NOT NULL,
                training_days_per_week INTEGER NOT NULL,
                experience TEXT NOT NULL,
                available_days TEXT NOT NULL,
                base_distance REAL,
                preferred_time TEXT,
                goal_date TEXT NOT NULL,
                start_date TEXT NOT NULL,
                long_run_day TEXT,
                session_type_preference TEXT,
                distance_unit TEXT
            );

            CREATE TABLE IF NOT EXISTS plans (
                plan_id TEXT PRIMARY KEY,
                user_id INTEGER,
                goal TEXT NOT NULL,
                start_date TEXT NOT NULL,
                goal_date TEXT NOT NULL,
                training_duration INTEGER NOT NULL,
                training_days_per_week INTEGER NOT NULL,
                experience TEXT NOT NULL,
                excel_file TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS training_plans (
                plan_id TEXT,
                week INTEGER NOT NULL,
                day TEXT NOT NULL,
                session TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES plans(plan_id)
            );
            
            CREATE TABLE IF NOT EXISTS user_equipment (
                user_id INTEGER NOT NULL,
                equipment TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS exercises (
                name TEXT PRIMARY KEY,
                category TEXT,
                equipment TEXT,
                description TEXT,
                goal_tag TEXT,
                muscle_group TEXT,
                youtube_link TEXT
            );

            CREATE TABLE IF NOT EXISTS user_muscle_focus (
                user_id INTEGER NOT NULL,
                muscle_group TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS user_starting_weights (
                user_id INTEGER NOT NULL,
                exercise TEXT NOT NULL,
                weight REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)

        cursor.executemany(
            "INSERT OR IGNORE INTO exercises (name, category, equipment, description, goal_tag, muscle_group, youtube_link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            EXERCISES
        )

        # Migration to add email column if it doesn’t exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
            conn.commit()
            logging.info("Added email column to users table")
        except sqlite3.Error as e:
            logging.info(f"Email column already exists or error during migration: {e}")

        # Migration to add start_date and goal_date if they don’t exist
        try:
            cursor.execute("ALTER TABLE plans ADD COLUMN start_date TEXT")
            cursor.execute("ALTER TABLE plans ADD COLUMN goal_date TEXT")
            conn.commit()
            logging.info("Added start_date and goal_date columns to plans table")
        except sqlite3.Error as e:
            logging.info(f"Columns already exist or error during migration: {e}")

        conn.commit()
        logging.info("Database schema initialized successfully")
    except sqlite3.Error as e:
        logging.error(f"Error setting up database: {e}")
        conn.rollback()
        raise