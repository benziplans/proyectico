#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  8 12:28:02 2025

@author: rodrigo

#test live update
"""
from datetime import datetime
from config_db import connect_db, EXPERIENCE_LEVELS, DAYS_OF_WEEK, DISTANCE_UNITS, MUSCLE_GROUPS, WEIGHT_UNITS, EQUIPMENT_OPTIONS, EXERCISE_SUBSTITUTES, EXERCISES, setup_database, GOALS, DBConnection
from generate_plan import generate_training_plan, parse_feedback_comments
import logging
import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

WEIGHT_EXERCISES = ["Squat", "Bench", "Deadlift"]

def validate_date(date_str: str, is_start: bool = False, goal_date: str = None, is_dob: bool = False) -> tuple[bool, str]:
    """Validate a date string in YYYY-MM-DD format."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        if is_dob:
            if date >= today:
                return False, "Date of birth must be in the past"
        else:
            if date < today:
                return False, "Date must be in the future"
            if is_start and goal_date:
                goal = datetime.strptime(goal_date, "%Y-%m-%d")
                if date >= goal:
                    return False, "Start date must be before goal date"
        return True, ""
    except ValueError:
        return False, "Invalid date (use YYYY-MM-DD, e.g., '2025-08-01')"

def validate_distance(distance_str: str) -> tuple[bool, str]:
    """Validate a distance string."""
    if not distance_str:
        return True, ""
    try:
        dist = float(distance_str)
        if dist <= 0:
            return False, "Must be greater than 0"
        return True, ""
    except ValueError:
        return False, "Must be a number (e.g., 5 or 5.5)"

def validate_weight(weight_str: str) -> tuple[bool, str]:
    """Validate a weight string."""
    if not weight_str:
        return True, ""
    try:
        weight = float(weight_str)
        if weight <= 0:
            return False, "Must be greater than 0"
        return True, ""
    except ValueError:
        return False, "Must be a number (e.g., 50 or 50.5)"

def validate_email(email_str: str) -> tuple[bool, str]:
    """Validate an email address format."""
    if not email_str:
        return False, "Required"
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email_str):
        return False, "Invalid email format (e.g., user@example.com)"
    return True, ""

def send_training_plan_email(user_email: str, plan_id: str, excel_file_path: str, sender_email: str, sender_password: str, user_name: str, goal: str):
    """Send the training plan to the user's email with the existing Excel attachment."""
    try:
        # Email configuration
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = f"Your Training Plan (Plan ID: {plan_id})"

        # Create email body with user_name and goal
        body = f"""
Hi {user_name}!

I am Benzi and prepared a bespoke plan for you. Your {goal} training will go great!
The training plan is attached as an Excel file (training_plan_{plan_id}.xlsx) for your convenience.

Keep us updated with your feedback, we can continue optimizing your plan as you train.

💪🏽💪🏽💪🏽
"""
        msg.attach(MIMEText(body, 'plain'))

        # Attach the existing Excel file
        from email.mime.base import MIMEBase
        from email import encoders
        import os
        if not os.path.exists(excel_file_path):
            raise FileNotFoundError(f"Excel file not found at {excel_file_path}")
        
        with open(excel_file_path, 'rb') as attachment:
            part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=training_plan_{plan_id}.xlsx')
        msg.attach(part)

        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        logging.info(f"Training plan sent to {user_email} for Plan ID {plan_id} with Excel attachment")
    except Exception as e:
        logging.error(f"Failed to send email to {user_email}: {e}")
        raise

def register_user(inputs: dict, update_only: bool = False) -> int | None:
    """Register or update a user in the database and generate a training plan."""
    user_id = None
    db = DBConnection()
    cursor = db.get_cursor()
    try:
        setup_database(db.conn, cursor)

        # Validate required fields
        required_fields = ["name", "date_of_birth", "email", "goal", "training_days_per_week", "experience", "start_date", "goal_date"]
        missing = [f for f in required_fields if f not in inputs or not inputs[f]]
        if missing:
            logging.error(f"Missing required fields: {missing}")
            return None

        if inputs["goal"] not in GOALS.keys():
            logging.error(f"Invalid goal '{inputs['goal']}'. Options: {GOALS.keys()}")
            return None
        if inputs["experience"] not in EXPERIENCE_LEVELS:
            logging.error(f"Invalid experience '{inputs['experience']}'. Options: {EXPERIENCE_LEVELS}")
            return None
        if not all(eq in EQUIPMENT_OPTIONS for eq in inputs["equipment"]):
            logging.error(f"Invalid equipment in {inputs['equipment']}. Options: {EQUIPMENT_OPTIONS}")
            return None
        
        # Validate email
        valid_email, email_msg = validate_email(inputs["email"])
        if not valid_email:
            logging.error(f"Invalid email: {email_msg}")
            return None

        # Handle available_days from GUI
        available_days = inputs["available_days"]
        logging.info(f"Raw available_days input from GUI: {available_days}")
        if isinstance(available_days, list):
            # If GUI sends a list, filter valid days and join
            available_days = [day.strip() for day in available_days if day.strip() in DAYS_OF_WEEK]
        elif isinstance(available_days, str):
            # If GUI sends a string, split and validate
            available_days = [day.strip() for day in available_days.split(",") if day.strip()]
            available_days = [day for day in available_days if any(d.lower().startswith(day.lower()) for d in DAYS_OF_WEEK)]
        else:
            logging.warning(f"Invalid available_days format: {available_days}, defaulting to all days")
            available_days = DAYS_OF_WEEK
        
        if not available_days:
            logging.warning(f"No valid days in {inputs['available_days']}, defaulting to all days")
            available_days = DAYS_OF_WEEK
        
        # Ensure we have enough days for training_days_per_week
        if len(available_days) < inputs["training_days_per_week"]:
            logging.warning(f"Too few available days ({len(available_days)}) for {inputs['training_days_per_week']} days per week, using all available")
        
        available_days_str = ",".join(available_days)
        logging.info(f"Processed available_days for DB: {available_days_str}")

        if inputs["goal"] == "Hyrox":
            missing_hyrox_equipment = [eq for eq in ["skierg", "sled", "rower", "kettlebell", "sandbag", "wallball"] if eq not in inputs["equipment"]]
            if missing_hyrox_equipment:
                logging.warning(f"Some Hyrox equipment missing ({', '.join(missing_hyrox_equipment)}). Plan will adapt.")
        if inputs.get("distance_unit", "km") not in DISTANCE_UNITS:
            logging.error(f"Invalid distance unit '{inputs['distance_unit']}'. Options: {DISTANCE_UNITS}")
            return None
        if inputs.get("muscle_focus") and not all(m in MUSCLE_GROUPS for m in inputs["muscle_focus"]):
            logging.error(f"Invalid muscle focus. Options: {MUSCLE_GROUPS}")
            return None

        cursor.execute("SELECT * FROM users WHERE name = ? AND birth_date = ?", (inputs["name"], inputs["date_of_birth"]))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id = existing_user[0]
            old_data = dict(zip([desc[0] for desc in cursor.description], existing_user))
            old_equipment = set([row[0] for row in cursor.execute("SELECT equipment FROM user_equipment WHERE user_id = ?", (user_id,)).fetchall()])
            old_muscle_focus = set([row[0] for row in cursor.execute("SELECT muscle_group FROM user_muscle_focus WHERE user_id = ?", (user_id,)).fetchall()])
            old_weights = {row[0]: row[1] for row in cursor.execute("SELECT exercise, weight FROM user_starting_weights WHERE user_id = ?", (user_id,)).fetchall()}

            logging.info(f"User {inputs['name']} (DOB: {inputs['date_of_birth']}) exists with ID {user_id}. Checking for updates.")
            updates = {k: v for k, v in inputs.items() if k in old_data and old_data.get(k) != v}
            if updates:
                logging.info(f"Updating user fields: {updates}")

            if update_only:
                inputs = {k: inputs.get(k, old_data[k]) for k in old_data}
                inputs["equipment"] = inputs.get("equipment", list(old_equipment))
                inputs["muscle_focus"] = inputs.get("muscle_focus", list(old_muscle_focus))
                inputs["starting_weights"] = inputs.get("starting_weights", old_weights)
                inputs["available_days"] = available_days

            cursor.execute("""
                UPDATE users SET goal = ?, training_days_per_week = ?, experience = ?, available_days = ?, 
                                base_distance = ?, preferred_time = ?, goal_date = ?, start_date = ?, 
                                long_run_day = ?, session_type_preference = ?, distance_unit = ?, email = ?
                WHERE user_id = ?
            """, (inputs["goal"], inputs["training_days_per_week"], inputs["experience"], available_days_str,
                  inputs.get("base_distance"), inputs.get("preferred_time"), inputs["goal_date"], inputs["start_date"],
                  inputs.get("long_run_day"), inputs.get("session_type_preference"), inputs.get("distance_unit", "km"),
                  inputs["email"], user_id))

            new_equipment = set(inputs["equipment"])
            if new_equipment != old_equipment or update_only:
                cursor.execute("DELETE FROM user_equipment WHERE user_id = ?", (user_id,))
                for eq in inputs["equipment"]:
                    cursor.execute("INSERT INTO user_equipment (user_id, equipment) VALUES (?, ?)", (user_id, eq))

            if inputs["goal"] == "Muscle Gains":
                new_muscle_focus = set(inputs["muscle_focus"])
                cursor.execute("SELECT muscle_group FROM user_muscle_focus WHERE user_id = ?", (user_id,))
                previous_muscle_focus = set(row[0] for row in cursor.fetchall()) if cursor.fetchall() else set()
                if new_muscle_focus != previous_muscle_focus or update_only:
                    cursor.execute("DELETE FROM user_muscle_focus WHERE user_id = ?", (user_id,))
                    for muscle in inputs["muscle_focus"]:
                        cursor.execute("INSERT INTO user_muscle_focus (user_id, muscle_group) VALUES (?, ?)", (user_id, muscle))
                
                new_weights = inputs["starting_weights"]
                if new_weights != old_weights or update_only:
                    cursor.execute("DELETE FROM user_starting_weights WHERE user_id = ?", (user_id,))
                    for exercise, weight in new_weights.items():
                        cursor.execute("INSERT INTO user_starting_weights (user_id, exercise, weight) VALUES (?, ?, ?)", (user_id, exercise, weight))
        else:
            base_distance = inputs.get("base_distance") if inputs["goal"] in ["Marathon", "Half Marathon", "10K", "5K"] else None
            long_run_day = inputs.get("long_run_day") if inputs["goal"] in ["Marathon", "Half Marathon", "10K", "5K"] else None
            distance_unit = inputs.get("distance_unit", "km")

            cursor.execute("""
                INSERT INTO users (name, birth_date, email, goal, training_days_per_week, experience, available_days, 
                                  base_distance, preferred_time, goal_date, start_date, long_run_day, 
                                  session_type_preference, distance_unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (inputs["name"], inputs["date_of_birth"], inputs["email"], inputs["goal"], inputs["training_days_per_week"], 
                  inputs["experience"], available_days_str, base_distance, inputs.get("preferred_time"),
                  inputs["goal_date"], inputs["start_date"], long_run_day, inputs.get("session_type_preference"), 
                  distance_unit))
            user_id = cursor.lastrowid

            for equipment in inputs["equipment"]:
                cursor.execute("INSERT INTO user_equipment (user_id, equipment) VALUES (?, ?)", (user_id, equipment))

            if inputs["goal"] == "Muscle Gains":
                for muscle in inputs["muscle_focus"]:
                    cursor.execute("INSERT INTO user_muscle_focus (user_id, muscle_group) VALUES (?, ?)", (user_id, muscle))
                for exercise, weight in inputs["starting_weights"].items():
                    cursor.execute("INSERT INTO user_starting_weights (user_id, exercise, weight) VALUES (?, ?, ?)", (user_id, exercise, weight))

        db.commit()
        logging.info(f"User {inputs['name']} {'updated' if existing_user else 'registered'} with ID {user_id}")

        # Generate training plan
        adjustments = inputs.get("feedback_adjustments", {})
        plan_id, plan = generate_training_plan(cursor, db.conn, user_id, adjustments=adjustments)
        logging.info(f"Generated plan before export for user {user_id}: {plan}")
        print(f"\n✅ Generated Training Plan (Plan ID: {plan_id}):\n")
        if plan:
            logging.debug(f"Raw plan before printing: {plan}")
            for week, days in plan.items():
                if not isinstance(days, dict):
                    logging.error(f"Invalid days structure for Week {week}: {days}")
                    continue
                for day, session in days.items():
                    formatted_session = session.replace("[Video]", "🔗 Watch Here")
                    if day not in DAYS_OF_WEEK:
                        logging.warning(f"Unexpected day '{day}' in plan, expected one of {DAYS_OF_WEEK}")
                    print(f"Week {week}, {day}: {formatted_session}")
            logging.debug(f"Plan after printing: {plan}")
        else:
            print("No plan generated - plan is empty.")
        db.commit()
        logging.info(f"Training plan generated for user {inputs['name']} with Plan ID {plan_id}")

        # Fetch the Excel file path from the plans table
        cursor.execute("SELECT excel_file FROM plans WHERE plan_id = ?", (plan_id,))
        excel_file_result = cursor.fetchone()
        if not excel_file_result or not excel_file_result[0]:
            logging.error("Excel file path not found in plans table")
            raise ValueError("Excel file path not found in plans table")
        excel_file_path = excel_file_result[0]

        # Send training plan via email
        if plan_id:
            sender_email = "benzi.plans@gmail.com"  # Replace with your Gmail address
            sender_password = "istg jcki sner cdtq"  # Replace with your Gmail App Password
            send_training_plan_email(inputs["email"], plan_id, excel_file_path, sender_email, sender_password, inputs["name"], inputs["goal"])
            logging.info(f"Email notification sent to {inputs['email']}")
        
        # Close the entire application after success
        if plan_id:
            tk._default_root.quit()  # Quit the Tkinter mainloop cleanly

    except sqlite3.IntegrityError as e:
        db.rollback()
        logging.error(f"Database integrity error: {e}")
        return None
    except sqlite3.Error as e:
        db.rollback()
        logging.error(f"Database error: {e}")
        return None
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error during registration: {e}")
        return None

    return user_id

def store_feedback(user_id: int, feedback: dict) -> None:
    """Store user feedback in the database."""
    logging.info(f"Storing feedback for user_id={user_id}, feedback={feedback}")
    db = DBConnection()
    cursor = db.get_cursor()
    try:
        weights_str = " ".join([f"{ex}:{w}" for ex, w in feedback.get("progress_weights", {}).items()]) if "progress_weights" in feedback else ""
        cursor.execute("""
            INSERT INTO feedback (user_id, plan_id, satisfaction, comments, progress_weights, weight_unit, trained_until)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, feedback["plan_id"], feedback["satisfaction"], feedback["comments"], weights_str, 
              feedback.get("weight_unit"), feedback["trained_until"]))
        db.commit()
        logging.info(f"Feedback stored successfully for user_id={user_id}, plan_id={feedback['plan_id']}")
    except sqlite3.Error as e:
        db.rollback()
        logging.error(f"Error storing feedback: {e}")
        raise
    finally:
        cursor.close()  # Ensure the cursor is closed

def create_form_field(parent, field: str, desc: str, widget_type, values=None, label_font=None, validate_func=None, field_type="text", height: int = 1) -> tuple:
    """Create a form field with validation and error label."""
    frame = tk.Frame(parent)
    frame.pack(fill="x", pady=5)
    # Add the description label
    tk.Label(frame, text=desc, font=label_font).pack(side="left")

    if widget_type == tk.Entry:
        entry = tk.Entry(frame, width=40, font=label_font if label_font else None)
        entry.pack(side="right", padx=5)
    elif widget_type == ttk.Combobox:
        entry = ttk.Combobox(frame, values=values, width=37, font=label_font if label_font else None)
        entry.set(values[0] if values else "")
        entry.pack(side="right", padx=5)
    elif widget_type == tk.Listbox:
        if field in ["available_days", "muscle_focus"]:
            entry_frame = tk.Frame(frame)
            entry_frame.pack(side="right", padx=5, fill="x")
            entry_vars = {val: tk.BooleanVar(value=False) for val in values}
            current_row = tk.Frame(entry_frame)
            current_row.pack(fill="x")
            total_width = 0
            max_width = 500
            for val in values:
                cb = tk.Checkbutton(current_row, text=val, variable=entry_vars[val], font=label_font if label_font else None, command=lambda v=val, vars=entry_vars: update_checkbutton_state(v, vars))
                cb.pack(side="left", padx=5)
                total_width += (len(val) * 10 + 30)
                if total_width > max_width:
                    current_row = tk.Frame(entry_frame)
                    current_row.pack(fill="x")
                    total_width = 0
                    cb.pack_forget()
                    cb.pack(side="left", padx=5)
            class CheckbuttonGroup:
                def __init__(self, vars_dict):
                    self.vars = vars_dict
                def curselection(self):
                    return [i for i, (val, var) in enumerate(self.vars.items()) if var.get()]
                def get(self, index):
                    return list(self.vars.keys())[index]
            entry = CheckbuttonGroup(entry_vars)
        else:
            entry = tk.Listbox(frame, height=height, selectmode="multiple", exportselection=0, font=label_font if label_font else None)
            entry.pack(side="right", padx=5, fill="x")
            for item in values:
                entry.insert(tk.END, item)
    else:
        raise ValueError(f"Unsupported widget type: {widget_type}")

    error_label = tk.Label(frame, text="", fg="red", font=label_font)
    error_label.pack(side="right", padx=5)

    # Define validation functions based on field_type
    def validate_text(widget, el):
        value = widget.get().strip()
        if not value:
            el.config(text="Required")
        else:
            el.config(text="")

    if validate_func:
        if field_type == "date":
            # Pass the entry widget to validate_func, not the event
            entry.bind("<KeyRelease>", lambda event: validate_func(entry, error_label))
        elif field_type == "text":
            # Pass the entry widget to validate_text, not the event
            entry.bind("<KeyRelease>", lambda event: validate_text(entry, error_label))

    return entry, error_label

# New function to update Checkbutton state dynamically
def update_checkbutton_state(value, vars_dict):
    """Update the Checkbutton state and ensure vars reflects the current selection."""
    for val, var in vars_dict.items():
        if val == value:
            var.set(not var.get())  # Toggle the state

def new_user_basic_info():
    """Collect basic user information via GUI."""
    root = tk.Tk()
    root.title("New User - Basic Information")
    root.geometry("600x400")
    label_font = font.Font(family="Helvetica", size=12)
    button_font = font.Font(family="Helvetica", size=12, weight="bold")

    tk.Label(root, text="Enter your basic information:", font=label_font).pack(pady=20)

    entries = {}
    error_labels = {}
    fields = [
        ("name", "Your full name (e.g., 'John Doe')", tk.Entry),
        ("date_of_birth", "Your date of birth (YYYY-MM-DD)", tk.Entry),
        ("email", "Your email address (e.g., user@example.com)", tk.Entry),
        ("goal", "Your training goal", ttk.Combobox, list(GOALS.keys())),
    ]
    for f, d, w, *o in fields:
        if f == "date_of_birth":
            validate = lambda e, el: el.config(text=validate_date(e.get(), is_dob=True)[1])
        elif f == "email":
            validate = lambda e, el: el.config(text=validate_email(e.get())[1])
        else:
            validate = None
        entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font, validate_func=validate if w == tk.Entry else None)
        entries[f] = entry
        error_labels[f] = error
        if w == ttk.Combobox:
            entry.set(o[0][0])

    def next_step():
        inputs = {field: entries[field].get().strip() for field in entries}
        all_valid = True
        for field in ["name", "date_of_birth", "email", "goal"]:
            if not inputs[field]:
                error_labels[field].config(text="Required")
                all_valid = False
            elif field == "date_of_birth":
                valid, msg = validate_date(inputs[field], is_dob=True)
                error_labels[field].config(text=msg)
                all_valid &= valid
            elif field == "email":
                valid, msg = validate_email(inputs[field])
                error_labels[field].config(text=msg)
                all_valid &= valid

        if all_valid:
            root.destroy()
            new_user_goal_details(inputs["name"], inputs["date_of_birth"], inputs["goal"], inputs["email"])
        else:
            messagebox.showerror("Error", "Please correct all errors.")

    tk.Button(root, text="Next", command=next_step, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=30)
    root.mainloop()

def new_user_goal_details(name: str, date_of_birth: str, goal: str, email: str):
    """Collect goal-specific user details via GUI."""
    root = tk.Tk()
    root.title(f"New User - {goal} Details")
    root.geometry("800x600")
    label_font = font.Font(family="Helvetica", size=12)
    button_font = font.Font(family="Helvetica", size=12, weight="bold")

    tk.Label(root, text=f"User: {name} | Goal: {goal}", font=label_font).pack(pady=20)

    entries = {}
    error_labels = {}
    common_fields = [
        ("start_date", "When would you like to start training? (YYYY-MM-DD)", tk.Entry),
        ("goal_date", "When is the goal? (YYYY-MM-DD, after start date)", tk.Entry),
        ("training_days_per_week", "Number of training days per week (1-7)", ttk.Combobox, list(range(1, 8))),
        ("experience", "Your experience level", ttk.Combobox, EXPERIENCE_LEVELS),
        ("available_days", "Days you can train (select multiple)", tk.Listbox, DAYS_OF_WEEK),
    ]
    running_goals = ["Marathon", "Half Marathon", "10K", "5K"]
    hyrox_fields = [
        ("base_distance", "Current comfortable Hyrox distance (e.g., 1 km)", tk.Entry),
        ("distance_unit", "Distance unit", ttk.Combobox, DISTANCE_UNITS),
    ]
    muscle_fields = [("muscle_focus", "Muscle groups to target (select multiple)", tk.Listbox, MUSCLE_GROUPS)]

    fields = common_fields.copy()
    if goal == "Hyrox":
        fields.extend(hyrox_fields)
    elif goal in ["Muscle Gains", "Stay Lean", "Lose Weight"]:
        fields.extend(muscle_fields)

    available_days_entry = None

    for f, d, w, *o in fields:
        if f in ["start_date", "goal_date"]:
            validate = lambda e, el, f=f: el.config(text=validate_date(e.get(), is_start=(f == "start_date"), goal_date=entries["goal_date"].get())[1])
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font, validate_func=validate)
        elif f == "base_distance":
            validate = lambda e, el: el.config(text=validate_distance(e.get())[1])
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font, validate_func=validate)
        elif f in ["available_days", "muscle_focus"]:
            entry, error = create_form_field(root, f, d, w, o[0], label_font, height=5)
            if f == "available_days":
                available_days_entry = entry
        else:
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font)
        entries[f] = entry
        error_labels[f] = error

    if goal in ["Hyrox", "Muscle Gains"]:
        equipment_frame = tk.Frame(root)
        equipment_frame.pack(pady=10, fill="x", padx=20)
        tk.Label(equipment_frame, text="Equipment Available:", font=label_font).pack(side="left")
        equipment_vars = {eq: tk.BooleanVar(value=False) for eq in EQUIPMENT_OPTIONS}
        eq_inner_frame = tk.Frame(equipment_frame)
        eq_inner_frame.pack(fill="x")
        current_row = tk.Frame(eq_inner_frame)
        current_row.pack(fill="x")
        total_width = 0
        max_width = 600
        for eq in EQUIPMENT_OPTIONS:
            cb = tk.Checkbutton(current_row, text=eq, variable=equipment_vars[eq], font=label_font)
            cb.pack(side="left", padx=5)
            total_width += (len(eq) * 10 + 30)
            if total_width > max_width:
                current_row = tk.Frame(eq_inner_frame)
                current_row.pack(fill="x")
                total_width = 0
                cb.pack_forget()
                cb.pack(side="left", padx=5)

    if goal == "Muscle Gains":
        weights_frame = tk.Frame(root)
        weights_frame.pack(pady=10, fill="x", padx=20)
        tk.Label(weights_frame, text="Starting Weights (optional, in kg):", font=label_font).pack(side="left")
        weight_entries = {}
        weights_inner_frame = tk.Frame(weights_frame)
        weights_inner_frame.pack(fill="x")
        current_row = tk.Frame(weights_inner_frame)
        current_row.pack(fill="x")
        total_width = 0
        max_width = 500
        for exercise in WEIGHT_EXERCISES:
            frame = tk.Frame(current_row)
            frame.pack(side="left", padx=10)
            tk.Label(frame, text=f"{exercise}:", font=label_font).pack(side="left")
            entry = tk.Entry(frame, width=15)
            entry.pack(side="left")
            weight_error = tk.Label(frame, text="", fg="red", font=label_font)
            weight_error.pack(side="left")
            weight_entries[exercise] = (entry, weight_error)
            entry.bind("<KeyRelease>", lambda e, ex=exercise: weight_entries[ex][1].config(text=validate_weight(e.get())[1]))
            total_width += (len(exercise) * 10 + 120)
            if total_width > max_width:
                current_row = tk.Frame(weights_inner_frame)
                current_row.pack(fill="x")
                total_width = 0
                frame.pack_forget()
                frame.pack(side="left", padx=10)

        unit_frame = tk.Frame(root)
        unit_frame.pack(pady=10, fill="x", padx=20)
        tk.Label(unit_frame, text="Weight Unit:", font=label_font).pack(side="left")
        weight_unit = ttk.Combobox(unit_frame, values=WEIGHT_UNITS, width=15)
        weight_unit.set("kg")
        weight_unit.pack(side="left", padx=10)

    def submit_initial():
        inputs = {
            "name": name,
            "date_of_birth": date_of_birth,
            "goal": goal,
            "email": email,
        }
        inputs.update({field: (entries[field].get().strip() if isinstance(entries[field], (tk.Entry, ttk.Combobox)) else
                               ",".join([val for val, var in entries[field].vars.items() if var.get()]) if field == "available_days" else
                               ",".join([val for val, var in entries[field].vars.items() if var.get()]) if hasattr(entries[field], 'vars') else
                               ",".join([entries[field].get(i) for i in entries[field].curselection()])) 
                       for field in entries})
        print(f"Debug: Captured available_days = {inputs['available_days']}")
        if goal in ["Hyrox", "Muscle Gains"]:
            inputs["equipment"] = [eq for eq, var in equipment_vars.items() if var.get()]
        else:
            inputs["equipment"] = []
        inputs["muscle_focus"] = [mg for mg in MUSCLE_GROUPS if mg in inputs.get("muscle_focus", [])] if "muscle_focus" in inputs else []
        if goal == "Muscle Gains":
            inputs["starting_weights"] = {ex: float(entry.get().strip()) for ex, (entry, _) in weight_entries.items() if entry.get().strip()}
            inputs["weight_unit"] = weight_unit.get()
        else:
            inputs["starting_weights"] = {}
            inputs["weight_unit"] = "kg"

        all_valid = True
        required_fields = ["start_date", "goal_date", "training_days_per_week", "experience", "available_days"]
        for field in required_fields:
            if not inputs[field]:
                error_labels[field].config(text="Required")
                all_valid = False
            elif field in ["start_date", "goal_date"]:
                valid, msg = validate_date(inputs[field], field == "start_date", inputs["goal_date"] if field == "start_date" else None)
                error_labels[field].config(text=msg)
                all_valid &= valid
            elif field == "base_distance" and inputs[field]:
                valid, msg = validate_distance(inputs[field])
                error_labels[field].config(text=msg)
                all_valid &= valid
            elif field == "training_days_per_week":
                try:
                    inputs[field] = int(inputs[field])
                    if not 1 <= inputs[field] <= 7:
                        error_labels[field].config(text="Must be 1-7")
                        all_valid = False
                except ValueError:
                    error_labels[field].config(text="Must be a number")
                    all_valid = False

        if not all_valid:
            messagebox.showerror("Error", "Please correct all errors.")
            return

        root.destroy()
        if goal in running_goals:
            show_running_details_window(name, date_of_birth, goal, inputs)
        else:
            user_id_result = register_user(inputs)
            if user_id_result:
                messagebox.showinfo("Success", f"User registered with ID {user_id_result}")
            else:
                messagebox.showerror("Error", "Failed to register user")

    tk.Button(root, text="Next", command=submit_initial, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=30)

    root.mainloop()

def show_running_details_window(name, date_of_birth, goal, initial_inputs):
    """Show a second window for running-specific details."""
    root = tk.Tk()
    root.title(f"New User - {goal} Running Details")
    root.geometry("800x600")
    label_font = font.Font(family="Helvetica", size=12)
    button_font = font.Font(family="Helvetica", size=12, weight="bold")

    tk.Label(root, text=f"User: {name} | Goal: {goal}", font=label_font).pack(pady=20)

    entries = {}
    error_labels = {}
    available_days = initial_inputs["available_days"].split(",") if initial_inputs["available_days"] else DAYS_OF_WEEK
    print(f"Debug: Available days passed to second window = {available_days}")
    running_fields = [
        ("base_distance", "Current comfortable running distance (e.g., 5)", tk.Entry),
        ("distance_unit", "Distance unit", ttk.Combobox, DISTANCE_UNITS),
        ("long_run_day", "Preferred long run day (from available days)", ttk.Combobox, available_days),
    ]

    for f, d, w, *o in running_fields:
        if f == "base_distance":
            validate = lambda e, el: el.config(text=validate_distance(e.get())[1])
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font, validate_func=validate)
        elif f == "long_run_day":
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font)
            entry.set(available_days[0] if available_days else "")
        else:
            entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font)
        entries[f] = entry
        error_labels[f] = error

    def submit_running():
        inputs = initial_inputs.copy()
        inputs.update({field: entries[field].get().strip() for field in entries})
        
        all_valid = True
        required_fields = ["base_distance", "distance_unit", "long_run_day"]
        for field in required_fields:
            if not inputs[field]:
                error_labels[field].config(text="Required")
                all_valid = False
            elif field == "base_distance":
                valid, msg = validate_distance(inputs[field])
                error_labels[field].config(text=msg)
                all_valid &= valid
            elif field == "long_run_day":
                available_days = initial_inputs["available_days"].split(",") if initial_inputs["available_days"] else []
                if not available_days:
                    error_labels[field].config(text="No available days selected")
                    all_valid = False
                elif inputs["long_run_day"] not in available_days:
                    error_labels[field].config(text="Must be in available days")
                    all_valid = False
                else:
                    error_labels[field].config(text="")

        if not all_valid:
            messagebox.showerror("Error", "Please correct all errors.")
            return

        user_id_result = register_user(inputs)
        if user_id_result:
            root.destroy()
            messagebox.showinfo("Success", f"User registered with ID {user_id_result}")
        else:
            messagebox.showerror("Error", "Failed to register user")

    tk.Button(root, text="Submit", command=submit_running, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=30)

    root.mainloop()

def registration_form(user_id: int = None):
    """Handle new user registration or updates."""
    if user_id is None:
        new_user_basic_info()
    else:
        root = tk.Tk()
        root.title("Update User Details")
        root.geometry("800x600")
        label_font = font.Font(family="Helvetica", size=12)
        button_font = font.Font(family="Helvetica", size=12, weight="bold")

        entries = {}
        error_labels = {}
        prefilled_data = {}
        goal = None
        db = DBConnection()
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            if not user_data:
                messagebox.showerror("Error", "User ID not found in database.")
                root.destroy()
                return
            prefilled_data = dict(zip([desc[0] for desc in cursor.description], user_data))
            goal = prefilled_data["goal"]
            cursor.execute("SELECT equipment FROM user_equipment WHERE user_id = ?", (user_id,))
            prefilled_data["equipment"] = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT muscle_group FROM user_muscle_focus WHERE user_id = ?", (user_id,))
            prefilled_data["muscle_focus"] = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT exercise, weight FROM user_starting_weights WHERE user_id = ?", (user_id,))
            prefilled_data["starting_weights"] = dict(cursor.fetchall())

        tk.Label(root, text="Enter your details below:", font=label_font).pack(pady=10)

        fields = [
            ("name", "Your full name (e.g., 'John Doe')", tk.Entry),
            ("date_of_birth", "Your date of birth (YYYY-MM-DD)", tk.Entry),
            ("email", "Your email address (e.g., user@example.com)", tk.Entry),
            ("training_days_per_week", "Number of training days per week (1-7)", ttk.Combobox, list(range(1, 8))),
            ("experience", "Your experience level", ttk.Combobox, EXPERIENCE_LEVELS),
            ("available_days", "Days you can train (select multiple)", tk.Listbox, DAYS_OF_WEEK),
            ("goal_date", "Goal date (YYYY-MM-DD, after start date)", tk.Entry),
            ("start_date", "Start date (YYYY-MM-DD, after today)", tk.Entry),
        ]
        running_goals = ["Marathon", "Half Marathon", "10K", "5K"]
        if goal in running_goals:
            fields.extend([
                ("base_distance", "Current comfortable running distance (e.g., 5)", tk.Entry),
                ("long_run_day", "Preferred long run day", ttk.Combobox, DAYS_OF_WEEK),
                ("distance_unit", "Distance unit", ttk.Combobox, DISTANCE_UNITS),
            ])
        elif goal == "Muscle Gains":
            fields.append(("muscle_focus", "Muscle groups to target (select multiple)", tk.Listbox, MUSCLE_GROUPS))

        for f, d, w, *o in fields:
            if f in ["date_of_birth", "goal_date", "start_date"]:
                validate = lambda e, el, f=f: el.config(text=validate_date(e.get(), is_start=(f == "start_date"), goal_date=entries.get("goal_date", "").get(), is_dob=(f == "date_of_birth"))[1])
            elif f == "base_distance":
                validate = lambda e, el: el.config(text=validate_distance(e.get())[1])
            elif f == "email":
                validate = lambda e, el: el.config(text=validate_email(e.get())[1])
            elif f == "available_days":
                validate = lambda e, el: el.config(text="Select at least one day" if not [e.get(i) for i in e.curselection()] else "")
                entry, error = create_form_field(root, f, d, w, o[0], label_font)
                for day in prefilled_data.get(f, "").split(","):
                    if day in o[0]:
                        entry.select_set(o[0].index(day))
                entry.bind("<<ListboxSelect>>", lambda e: validate(entry, error))
            else:
                validate = None
            if f != "available_days":
                entry, error = create_form_field(root, f, d, w, o[0] if o else None, label_font, validate_func=validate)
                entry.insert(0, prefilled_data.get(f, ""))
            entries[f] = entry
            error_labels[f] = error

        equipment_frame = tk.Frame(root)
        equipment_frame.pack(pady=5, padx=10, fill="x")
        tk.Label(equipment_frame, text="Equipment Available:", font=label_font).pack(side="left")
        equipment_vars = {eq: tk.BooleanVar(value=eq in prefilled_data.get("equipment", [])) for eq in EQUIPMENT_OPTIONS}
        for eq in EQUIPMENT_OPTIONS:
            tk.Checkbutton(equipment_frame, text=eq, variable=equipment_vars[eq], font=label_font).pack(side="left", padx=5)

        if goal == "Muscle Gains":
            weights_frame = tk.Frame(root)
            weights_frame.pack(pady=5, padx=10, fill="x")
            tk.Label(weights_frame, text="Starting Weights (optional, in kg):", font=label_font).pack(side="left")
            weight_entries = {}
            for exercise in WEIGHT_EXERCISES:
                frame = tk.Frame(weights_frame)
                frame.pack(side="left", padx=10)
                tk.Label(frame, text=f"{exercise}:", font=label_font).pack(side="left")
                entry = tk.Entry(frame, width=10)
                entry.insert(0, prefilled_data["starting_weights"].get(exercise, ""))
                entry.pack(side="left")
                weight_error = tk.Label(frame, text="", fg="red", font=label_font)
                weight_error.pack(side="left")
                weight_entries[exercise] = (entry, weight_error)
                entry.bind("<KeyRelease>", lambda e, ex=exercise: weight_entries[ex][1].config(text=validate_weight(e.get())[1]))

            unit_frame = tk.Frame(weights_frame)
            unit_frame.pack(pady=5, fill="x")
            tk.Label(unit_frame, text="Weight Unit:", font=label_font).pack(side="left")
            weight_unit = ttk.Combobox(unit_frame, values=WEIGHT_UNITS, width=5)
            weight_unit.set(prefilled_data.get("weight_unit", "kg"))
            weight_unit.pack(side="left", padx=5)

        def submit():
            inputs = {field: (entries[field].get().strip() if isinstance(entries[field], (tk.Entry, ttk.Combobox)) else
                              ",".join([entries[field].get(i) for i in entries[field].curselection()])) 
                      for field in entries}
            inputs["equipment"] = [eq for eq, var in equipment_vars.items() if var.get()]
            inputs["muscle_focus"] = [mg for mg in MUSCLE_GROUPS if mg in inputs.get("muscle_focus", [])] if "muscle_focus" in inputs else []
            inputs["starting_weights"] = {ex: float(entry.get().strip()) for ex, (entry, _) in weight_entries.items() if entry.get().strip()} if goal == "Muscle Gains" else {}
            inputs["weight_unit"] = weight_unit.get() if goal == "Muscle Gains" else "kg"

            all_valid = True
            required_fields = ["name", "date_of_birth", "email", "training_days_per_week", "experience", "goal_date", "start_date"]
            for field in required_fields:
                if not inputs[field]:
                    error_labels[field].config(text="Required")
                    all_valid = False
                elif field in ["date_of_birth", "goal_date", "start_date"]:
                    valid, msg = validate_date(inputs[field], field == "start_date", inputs["goal_date"] if field == "start_date" else None, field == "date_of_birth")
                    error_labels[field].config(text=msg)
                    all_valid &= valid
                elif field == "email":
                    valid, msg = validate_email(inputs[field])
                    error_labels[field].config(text=msg)
                    all_valid &= valid
                elif field == "base_distance" and inputs[field]:
                    valid, msg = validate_distance(inputs[field])
                    error_labels[field].config(text=msg)
                    all_valid &= valid
                elif field == "training_days_per_week":
                    try:
                        inputs[field] = int(inputs[field])
                        if not 1 <= inputs[field] <= 7:
                            error_labels[field].config(text="Must be 1-7")
                            all_valid = False
                    except ValueError:
                        error_labels[field].config(text="Must be a number")
                        all_valid = False

            if not inputs["available_days"]:
                error_labels["available_days"].config(text="Select at least one day")
                all_valid = False

            if goal == "Muscle Gains":
                for ex, (entry, error) in weight_entries.items():
                    value = entry.get().strip()
                    if value:
                        valid, msg = validate_weight(value)
                        error.config(text=msg)
                        all_valid &= valid

            if not all_valid:
                messagebox.showerror("Error", "Please correct all errors.")
                return

            user_id_result = register_user(inputs, update_only=True)
            if user_id_result:
                root.destroy()
                messagebox.showinfo("Success", f"User updated with ID {user_id_result}")
            else:
                messagebox.showerror("Error", "Failed to update user.")

        tk.Button(root, text="Submit", command=submit, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=20)
        root.mainloop()

def feedback_input_form():
    """Initial feedback form to lookup user."""
    root = tk.Tk()
    root.title("Leave Feedback - User Lookup")
    label_font = font.Font(family="Helvetica", size=12)

    entries = {}
    tk.Label(root, text="Identify yourself:", font=label_font).pack(pady=5)
    
    for f, d in [("name", "Your full name (e.g., 'John Doe')"), ("date_of_birth", "Your date of birth (YYYY-MM-DD)")]:
        entry, error = create_form_field(
            root, 
            f, 
            d, 
            tk.Entry, 
            label_font=label_font, 
            validate_func=lambda widget, el: el.config(text=validate_date(widget.get(), is_dob=True)[1]), 
            field_type="date" if f == "date_of_birth" else "text"
        )
        entries[f] = entry

    def lookup_user():
        name = entries["name"].get().strip()
        dob = entries["date_of_birth"].get().strip()
        if not name or not dob:
            messagebox.showerror("Error", "Name and date of birth are required.")
            return
        if not validate_date(dob, is_dob=True)[0]:
            messagebox.showerror("Error", "Invalid date of birth format (use YYYY-MM-DD).")
            return
        
        db = DBConnection()
        cursor = db.get_cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE name = ? AND birth_date = ?", (name, dob))
            user = cursor.fetchone()
            if not user:
                messagebox.showerror("Error", "User not found. Please register first.")
                return
            
            cursor.execute("SELECT plan_id, goal FROM plans WHERE user_id = ?", (user[0],))
            plans = cursor.fetchall()
            if not plans:
                messagebox.showerror("Error", "No training plans found for this user.")
                return
            
            root.destroy()
            select_plan_form(user[0], name, dob, plans)
        except sqlite3.Error as e:
            logging.error(f"Database error in lookup_user: {e}")
            messagebox.showerror("Error", "An error occurred while accessing the database.")
            return

    tk.Button(root, text="Next", command=lookup_user).pack(pady=10)
    root.mainloop()

def select_plan_form(user_id: int, name: str, dob: str, plans: list):
    """Select a plan for feedback."""
    root = tk.Tk()
    root.title("Select Training Plan")
    label_font = font.Font(family="Helvetica", size=12)

    tk.Label(root, text="Select the training plan to leave feedback for:", font=label_font).pack(pady=5)
    
    plan_options = [f"{plan[0]} ({plan[1]})" for plan in plans]
    plan_var = tk.StringVar(value=plan_options[0] if plan_options else "")
    plan_dropdown = ttk.Combobox(root, textvariable=plan_var, values=plan_options, state="readonly")
    plan_dropdown.pack(pady=5)

    def proceed():
        selected_plan = plan_var.get()
        plan_id = selected_plan.split(" (")[0]
        goal = selected_plan.split("(")[1].rstrip(")")
        root.destroy()
        feedback_form(user_id, name, dob, plan_id, goal)

    tk.Button(root, text="Next", command=proceed).pack(pady=10)
    root.mainloop()

def feedback_form(user_id: int, name: str, dob: str, plan_id: str, goal: str):
    """Collect feedback for a specific plan."""
    logging.info(f"Opening feedback form for user_id={user_id}, plan_id={plan_id}, goal={goal}")
    root = tk.Tk()
    root.title(f"Feedback Form - {plan_id}")
    root.geometry("600x400")  # Set a reasonable window size to ensure content is visible
    label_font = font.Font(family="Helvetica", size=12)
    button_font = font.Font(family="Helvetica", size=12, weight="bold")

    feedback = {"plan_id": plan_id}
    entries = {}
    error_labels = {}
    
    # Fetch exercises from the database
    db = DBConnection()
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT session FROM training_plans WHERE plan_id = ?", (plan_id,))
        sessions = cursor.fetchall()
        logging.info(f"Fetched {len(sessions)} sessions for plan_id={plan_id}")
        exercises = set()
        for session in sessions:
            session_text = session[0]
            for ex in EXERCISES:
                if ex[0] in session_text:
                    exercises.add(ex[0])
        exercise_info = f"Exercises in this plan: {', '.join(sorted(exercises))}" if exercises else "No specific exercises recorded."
        logging.info(f"Exercise info: {exercise_info}")
    except sqlite3.Error as e:
        logging.error(f"Database error while fetching sessions: {e}")
        exercise_info = "Error fetching exercises."
    
    tk.Label(root, text=f"Feedback for Plan: {plan_id} (Goal: {goal})", font=label_font).pack(pady=5)
    tk.Label(root, text=exercise_info, wraplength=400, justify="left", font=label_font).pack(pady=5)

    fields = [
        ("satisfaction", "Satisfaction (1-5)", ttk.Combobox, [1, 2, 3, 4, 5]),
        ("comments", "Comments (e.g., 'Squat is too heavy')", tk.Entry),
        ("trained_until", "Trained until (YYYY-MM-DD)", tk.Entry),
    ]
    for f, d, w, *o in fields:
        validate_func = lambda widget, el: el.config(text=validate_date(widget.get())[1]) if f == "trained_until" else None
        entry, error = create_form_field(
            root, 
            f, 
            d, 
            w, 
            values=o[0] if o else None, 
            label_font=label_font, 
            validate_func=validate_func, 
            field_type="date" if f == "trained_until" else "text"
        )
        entries[f] = entry
        error_labels[f] = error
        if f == "satisfaction":
            entry.set(3)
        logging.info(f"Created field: {f}")

    if goal == "Muscle Gains":
        logging.info("Adding Muscle Gains-specific fields")
        weight_frame = tk.Frame(root)
        weight_frame.pack(pady=5, fill="x")
        tk.Label(weight_frame, text="Updated Weights (optional):", font=label_font).pack(side="left")
        weight_entries = {}
        for exercise in WEIGHT_EXERCISES:
            frame = tk.Frame(root)
            frame.pack(pady=2, fill="x")
            tk.Label(frame, text=f"{exercise} Weight:", font=label_font).pack(side="left")
            entry = tk.Entry(frame, width=10, font=label_font)
            entry.pack(side="left", padx=5)
            error_label = tk.Label(frame, text="", fg="red", font=label_font)
            error_label.pack(side="left")
            weight_entries[exercise] = (entry, error_label)
            entry.bind("<KeyRelease>", lambda event, ex=exercise: weight_entries[ex][1].config(text=validate_weight(weight_entries[ex][0].get())[1]))
            logging.info(f"Created weight entry for {exercise}")

        unit_frame = tk.Frame(root)
        unit_frame.pack(pady=5, fill="x")
        tk.Label(unit_frame, text="Weight Unit:", font=label_font).pack(side="left")
        weight_unit = ttk.Combobox(unit_frame, values=WEIGHT_UNITS, width=5, font=label_font)
        weight_unit.set("kg")
        weight_unit.pack(side="left", padx=5)

    def submit_feedback():
        feedback["satisfaction"] = int(entries["satisfaction"].get() or 0)
        feedback["comments"] = entries["comments"].get().strip() or ""
        feedback["trained_until"] = entries["trained_until"].get().strip()
        logging.info(f"Submitting feedback: {feedback}")
        
        all_valid = True
        if feedback["satisfaction"] not in range(1, 6):
            error_labels["satisfaction"].config(text="Must be 1-5")
            all_valid = False
        if not feedback["trained_until"] or not validate_date(feedback["trained_until"])[0]:
            error_labels["trained_until"].config(text="Required valid date")
            all_valid = False
        
        if goal == "Muscle Gains":
            feedback["progress_weights"] = {ex: float(entry.get().strip()) for ex, (entry, _) in weight_entries.items() if entry.get().strip()}
            feedback["weight_unit"] = weight_unit.get()
            for ex, (entry, label) in weight_entries.items():
                if entry.get().strip() and not validate_weight(entry.get().strip())[0]:
                    all_valid = False

        if not all_valid:
            messagebox.showerror("Error", "Please correct all errors.")
            return

        store_feedback(user_id, feedback)
        
        inputs = {"name": name, "date_of_birth": dob, "email": ""}
        db = DBConnection()
        cursor = db.get_cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_data = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
            if "available_days" in user_data and user_data["available_days"]:
                user_data["available_days"] = user_data["available_days"].split(",")
            inputs.update(user_data)
            cursor.execute("SELECT equipment FROM user_equipment WHERE user_id = ?", (user_id,))
            inputs["equipment"] = [row[0] for row in cursor.fetchall()]
            if goal == "Muscle Gains":
                cursor.execute("SELECT muscle_group FROM user_muscle_focus WHERE user_id = ?", (user_id,))
                inputs["muscle_focus"] = [row[0] for row in cursor.fetchall()]
            else:
                inputs["muscle_focus"] = []
            if "progress_weights" in feedback and feedback["progress_weights"]:
                inputs["starting_weights"] = feedback["progress_weights"]
            adjustments = parse_feedback_comments(feedback["comments"], feedback["trained_until"])
            logging.info(f"Parsed feedback adjustments: {adjustments}")
            if adjustments.get("start_date"):
                inputs["start_date"] = adjustments["start_date"]
            inputs["feedback_adjustments"] = adjustments
            user_id_updated = register_user(inputs, update_only=True)
        except sqlite3.Error as e:
            logging.error(f"Database error in submit_feedback: {e}")
            messagebox.showerror("Error", "An error occurred while updating the plan.")
            return
        
        root.destroy()
        if user_id_updated:
            messagebox.showinfo("Success", f"Feedback submitted and plan updated for user ID {user_id_updated}")
        else:
            messagebox.showerror("Error", "Failed to process feedback.")

    tk.Button(root, text="Submit Feedback", command=submit_feedback, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)
    logging.info("Feedback form fully rendered")
# %%
    root.mainloop()


def update_user_prompt():
    """Prompt to lookup a user for updating their details."""
    root = tk.Tk()
    root.title("Update User - Lookup")
    label_font = font.Font(family="Helvetica", size=12)
    button_font = font.Font(family="Helvetica", size=12, weight="bold")

    entries = {}
    tk.Label(root, text="Enter your details to update:", font=label_font).pack(pady=5)
    
    for f, d in [("name", "Your full name (e.g., 'John Doe')"), ("date_of_birth", "Your date of birth (YYYY-MM-DD)")]:
        entry, error = create_form_field(root, f, d, tk.Entry, font=label_font, validate_func=lambda e, el: el.config(text=validate_date(e.get(), is_dob=True)[1] if f == "date_of_birth" else ""))
        entries[f] = entry

    def lookup_user():
        name = entries["name"].get().strip()
        dob = entries["date_of_birth"].get().strip()
        if not name or not dob:
            messagebox.showerror("Error", "Name and date of birth are required.")
            return
        if not validate_date(dob, is_dob=True)[0]:
            messagebox.showerror("Error", "Invalid date of birth format (use YYYY-MM-DD).")
            return
        
        db = DBConnection()
        with db.get_cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE name = ? AND birth_date = ?", (name, dob))
            user = cursor.fetchone()
            if not user:
                messagebox.showerror("Error", "User not found.")
                return
            
            root.destroy()
            registration_form(user_id=user[0])

    tk.Button(root, text="Next", command=lookup_user, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)
    root.mainloop()

def main_menu():
    """Display the main menu for the training plan generator."""
    logging.info("Starting main_menu function")
    try:
        # Check if we're in an IPython environment (like Spyder) and adjust Tkinter's backend
        if 'IPython' in sys.modules:
            logging.info("Detected IPython environment, applying Tkinter workaround for Spyder")
            try:
                # Switch to a non-interactive backend to avoid conflicts with IPython's event loop
                from IPython import get_ipython
                ipython = get_ipython()
                if ipython:
                    ipython.run_line_magic('gui', 'tk')  # Enable Tkinter GUI integration with IPython
            except Exception as e:
                logging.warning(f"Failed to enable Tkinter GUI integration with IPython: {e}")

        root = tk.Tk()
        root.title("Training Plan Generator")
        root.geometry("400x300")

        label_font = font.Font(family="Helvetica", size=12)
        button_font = font.Font(family="Helvetica", size=12, weight="bold")

        tk.Label(root, text="Welcome to the Training Plan Generator!", font=label_font).pack(pady=20)
        tk.Button(root, text="Register New User", command=registration_form, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)
        tk.Button(root, text="Update User", command=update_user_prompt, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)
        tk.Button(root, text="Leave Feedback", command=feedback_input_form, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)
        tk.Button(root, text="Exit", command=root.quit, font=button_font, bg="gray80", fg="black", padx=10, pady=5).pack(pady=10)

        logging.info("Main menu window created, entering mainloop")
        root.mainloop()
        logging.info("Main menu mainloop exited")
    except Exception as e:
        logging.error(f"Error in main_menu: {e}")
        raise

if __name__ == "__main__":
    import sys
    logging.info("Starting script execution")
    main_menu()
    logging.info("Script execution completed")
    