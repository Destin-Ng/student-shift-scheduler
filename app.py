"""
University Scheduler
Flask + SQLite backend

Run:
    python app.py

Then open:
    http://localhost:5000
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APP SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shift_board.db")

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

app.secret_key = os.environ.get(
    "SHIFT_BOARD_SECRET",
    "dev-secret-change-me"
)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 8-9, 9-10, ... 4-5
HOURS = list(range(8, 17))


# ============================================================
# DATABASE
# ============================================================

def get_db():
    """
    Open one SQLite connection for the current request.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """
    Close the database after each request.
    """
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """
    Create the database tables if they do not exist.

    This does NOT delete existing data.
    """

    db = sqlite3.connect(DB_PATH)

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'faculty')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS availability (
            email TEXT NOT NULL,
            day TEXT NOT NULL,
            hour INTEGER NOT NULL,

            PRIMARY KEY (email, day, hour),

            FOREIGN KEY (email)
                REFERENCES users(email)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            max_hours INTEGER NOT NULL DEFAULT 30,
            max_per_slot INTEGER NOT NULL DEFAULT 3
        );
        """
    )

    # Default scheduling rules
    db.execute(
        """
        INSERT OR IGNORE INTO rules
        (id, max_hours, max_per_slot)
        VALUES (1, 30, 3)
        """
    )

    # --------------------------------------------------------
    # Pre-created faculty accounts
    # --------------------------------------------------------

    faculty_seed = [
        ("faculty@bridgew.edu", "faculty123"),
    ]

    for email, password in faculty_seed:

        db.execute(
            """
            INSERT OR IGNORE INTO users
            (email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                email,
                generate_password_hash(password),
                "faculty",
                datetime.now(timezone.utc).isoformat()
            )
        )

    db.commit()
    db.close()


# ============================================================
# AUTHORIZATION HELPER
# ============================================================

def require_role(role):
    """
    Make sure the logged-in user has the required role.
    """

    if "email" not in session:
        return jsonify(error="Not signed in."), 401

    if session.get("role") != role:
        return jsonify(error="Not authorized."), 403

    return None


# ============================================================
# SIGN UP
# ============================================================

@app.post("/api/signup")
def signup():

    data = request.get_json(force=True, silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email:
        return jsonify(error="Enter an email."), 400

    if not password:
        return jsonify(error="Enter a password."), 400

    if len(password) < 4:
        return jsonify(error="Password must be at least 4 characters."), 400

    db = get_db()

    existing = db.execute(
        """
        SELECT role
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if existing:

        if existing["role"] == "faculty":
            return jsonify(
                error="That email is registered as faculty. Please sign in instead."
            ), 409

        return jsonify(
            error="An account already exists for that email."
        ), 409

    db.execute(
        """
        INSERT INTO users
        (email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            email,
            generate_password_hash(password),
            "student",
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()

    return jsonify(ok=True)


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
def login():

    data = request.get_json(force=True, silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(
            error="Enter your email and password."
        ), 400

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if not user:
        return jsonify(
            error="Incorrect email or password."
        ), 401

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify(
            error="Incorrect email or password."
        ), 401

    session.clear()

    session["email"] = user["email"]
    session["role"] = user["role"]

    return jsonify(
        email=user["email"],
        role=user["role"]
    )


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify(ok=True)


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def me():

    if "email" not in session:
        return jsonify(
            error="Not signed in."
        ), 401

    return jsonify(
        email=session["email"],
        role=session["role"]
    )


# ============================================================
# STUDENT AVAILABILITY
# ============================================================

@app.get("/api/availability")
def get_availability():

    err = require_role("student")

    if err:
        return err

    db = get_db()

    rows = db.execute(
        """
        SELECT day, hour
        FROM availability
        WHERE email = ?
        ORDER BY
            CASE day
                WHEN 'Mon' THEN 1
                WHEN 'Tue' THEN 2
                WHEN 'Wed' THEN 3
                WHEN 'Thu' THEN 4
                WHEN 'Fri' THEN 5
                WHEN 'Sat' THEN 6
                WHEN 'Sun' THEN 7
            END,
            hour
        """,
        (session["email"],)
    ).fetchall()

    slots = [
        {
            "day": row["day"],
            "hour": row["hour"]
        }
        for row in rows
    ]

    return jsonify(slots=slots)


@app.put("/api/availability")
def put_availability():

    err = require_role("student")

    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}

    slots = data.get("slots") or []

    # --------------------------------------------------------
    # Validate slots
    # --------------------------------------------------------

    cleaned_slots = []

    for slot in slots:

        day = slot.get("day")
        hour = slot.get("hour")

        if day not in DAYS:
            continue

        try:
            hour = int(hour)
        except (TypeError, ValueError):
            continue

        if hour not in HOURS:
            continue

        cleaned_slots.append(
            (session["email"], day, hour)
        )

    # Remove duplicates
    cleaned_slots = list(dict.fromkeys(cleaned_slots))

    db = get_db()

    # Replace the student's previous availability
    db.execute(
        """
        DELETE FROM availability
        WHERE email = ?
        """,
        (session["email"],)
    )

    if cleaned_slots:

        db.executemany(
            """
            INSERT INTO availability
            (email, day, hour)
            VALUES (?, ?, ?)
            """,
            cleaned_slots
        )

    db.commit()

    return jsonify(
        ok=True,
        count=len(cleaned_slots)
    )


# ============================================================
# FACULTY - EMPLOYEES
# ============================================================

@app.get("/api/employees")
def get_employees():

    err = require_role("faculty")

    if err:
        return err

    db = get_db()

    rows = db.execute(
        """
        SELECT
            u.email,
            a.day,
            a.hour
        FROM users u
        LEFT JOIN availability a
            ON u.email = a.email
        WHERE u.role = 'student'
        ORDER BY
            u.email,
            CASE a.day
                WHEN 'Mon' THEN 1
                WHEN 'Tue' THEN 2
                WHEN 'Wed' THEN 3
                WHEN 'Thu' THEN 4
                WHEN 'Fri' THEN 5
                WHEN 'Sat' THEN 6
                WHEN 'Sun' THEN 7
                ELSE 8
            END,
            a.hour
        """
    ).fetchall()

    students = {}

    for row in rows:

        email = row["email"]

        if email not in students:
            students[email] = {
                "email": email,
                "availability_count": 0,
                "availability": []
            }

        if row["day"] is not None and row["hour"] is not None:
            students[email]["availability"].append({
                "day": row["day"],
                "hour": row["hour"]
            })

            students[email]["availability_count"] += 1

    return jsonify(
        employees=list(students.values())
    )

# ============================================================
# FACULTY - AVAILABILITY DEMAND
# ============================================================

@app.get("/api/demand")
def get_demand():

    err = require_role("faculty")

    if err:
        return err

    db = get_db()

    rows = db.execute(
        """
        SELECT
            day,
            hour,
            COUNT(DISTINCT email) AS student_count
        FROM availability

        GROUP BY day, hour

        ORDER BY
            CASE day
                WHEN 'Mon' THEN 1
                WHEN 'Tue' THEN 2
                WHEN 'Wed' THEN 3
                WHEN 'Thu' THEN 4
                WHEN 'Fri' THEN 5
                WHEN 'Sat' THEN 6
                WHEN 'Sun' THEN 7
            END,
            hour
        """
    ).fetchall()

    demand = {}

    for row in rows:

        key = f"{row['day']}-{row['hour']}"

        demand[key] = row["student_count"]

    return jsonify(
        demand=demand
    )


# ============================================================
# FACULTY - RULES
# ============================================================

@app.get("/api/rules")
def get_rules():

    err = require_role("faculty")

    if err:
        return err

    db = get_db()

    row = db.execute(
        """
        SELECT max_hours, max_per_slot
        FROM rules
        WHERE id = 1
        """
    ).fetchone()

    return jsonify(
        max_hours=row["max_hours"],
        max_per_slot=row["max_per_slot"]
    )


@app.put("/api/rules")
def put_rules():

    err = require_role("faculty")

    if err:
        return err

    data = request.get_json(force=True, silent=True) or {}

    try:
        max_hours = int(data.get("max_hours"))
        max_per_slot = int(data.get("max_per_slot"))
    except (TypeError, ValueError):
        return jsonify(
            error="Rules must be numbers."
        ), 400

    if max_hours < 1:
        return jsonify(
            error="Maximum hours must be at least 1."
        ), 400

    if max_per_slot < 1:
        return jsonify(
            error="Maximum students per timeslot must be at least 1."
        ), 400

    db = get_db()

    db.execute(
        """
        UPDATE rules

        SET
            max_hours = ?,
            max_per_slot = ?

        WHERE id = 1
        """,
        (
            max_hours,
            max_per_slot
        )
    )

    db.commit()

    # Return the persisted values so the browser can immediately update
    # its state without depending on a second request.
    return jsonify(
        ok=True,
        max_hours=max_hours,
        max_per_slot=max_per_slot
    )


# ============================================================
# FACULTY - SCHEDULE GENERATION
# ============================================================

import random
from collections import defaultdict


def build_schedule(students, max_hours, max_per_slot, seed):
    """
    Generate a weekly schedule using a round-robin hour allocator.

    Core rule:
      - TotalHours comes from rules.max_hours in the SQLite database.
      - Each student's usable-hour capacity comes from that student's
        submitted availability rows in the SQLite database.
      - Each pass gives at most one hour to each eligible student.
      - max_per_slot also comes from the rules table.
    """

    rng = random.Random(seed)

    assignments = []
    student_hours = defaultdict(int)
    slot_count = defaultdict(int)
    assigned_slots = defaultdict(set)

    # Keep the student order deterministic. Numeric test accounts such as
    # 1@, 2@, 3@ are ordered numerically; normal emails alphabetically.
    def student_sort_key(student):
        email = student["email"]
        local_part = email.split("@", 1)[0]
        if local_part.isdigit():
            return (0, int(local_part), email)
        return (1, email)

    ordered_students = sorted(students, key=student_sort_key)

    # Do NOT hard-code student hour limits. The availability list on each
    # student was loaded from the availability table in SQLite below in
    # generate_schedule(). Each distinct availability row represents one
    # schedulable hour, so this is the student's database-derived capacity.
    student_max_hours = {
        student["email"]: len({
            (slot["day"], slot["hour"])
            for slot in student["availability"]
        })
        for student in ordered_students
    }

    # Count how many students are available in every slot. Scarcer slots are
    # preferred so the allocator does not waste hard-to-fill availability.
    availability_counts = defaultdict(int)
    for student in ordered_students:
        seen = set()
        for slot in student["availability"]:
            key = (slot["day"], slot["hour"])
            if key not in seen:
                availability_counts[key] += 1
                seen.add(key)

    # Use the saved faculty constraint directly. The previous version used
    # min(30, max_hours), which made saved values above 30 appear broken.
    total_target = max_hours
    remaining_hours = total_target

    # Round-robin: each student can receive at most one hour per pass.
    while remaining_hours > 0:
        made_assignment = False

        # Different seeds produce alternative schedules without changing caps.
        pass_students = ordered_students[:]
        rng.shuffle(pass_students)

        for student in pass_students:
            if remaining_hours <= 0:
                break

            email = student["email"]

            # Stop when this student has used all hours they submitted as
            # available in the database.
            if student_hours[email] >= student_max_hours[email]:
                continue

            eligible = []

            for slot in student["availability"]:
                day = slot["day"]
                hour = slot["hour"]
                slot_key = (day, hour)

                # Do not assign the same student to the same hour twice.
                if slot_key in assigned_slots[email]:
                    continue

                # Respect the existing maximum employees per timeslot.
                if slot_count[slot_key] >= max_per_slot:
                    continue

                eligible.append((day, hour))

            if not eligible:
                continue

            # Prefer scarce slots; random tie-breaking creates Option A/B.
            eligible.sort(
                key=lambda slot: (
                    availability_counts[slot],
                    rng.random()
                )
            )

            day, hour = eligible[0]
            slot_key = (day, hour)

            assignments.append({
                "email": email,
                "day": day,
                "hour": hour
            })

            student_hours[email] += 1
            slot_count[slot_key] += 1
            assigned_slots[email].add(slot_key)
            remaining_hours -= 1
            made_assignment = True

        # Prevent an infinite loop if nobody has any usable availability left.
        if not made_assignment:
            break

    total_hours = total_target - remaining_hours

    assignments.sort(
        key=lambda item: (
            DAYS.index(item["day"]),
            item["hour"],
            item["email"]
        )
    )

    # Group consecutive assigned hours into shifts.
    shifts_by_student = defaultdict(list)

    for assignment in assignments:
        shifts_by_student[assignment["email"]].append((
            assignment["day"],
            assignment["hour"]
        ))

    shifts = []

    for email, slots in shifts_by_student.items():
        slots.sort(key=lambda slot: (DAYS.index(slot[0]), slot[1]))

        current_day = None
        start_hour = None
        end_hour = None

        for day, hour in slots:
            if current_day == day and end_hour == hour:
                end_hour += 1
            else:
                if current_day is not None:
                    shifts.append({
                        "email": email,
                        "day": current_day,
                        "start_hour": start_hour,
                        "end_hour": end_hour
                    })

                current_day = day
                start_hour = hour
                end_hour = hour + 1

        if current_day is not None:
            shifts.append({
                "email": email,
                "day": current_day,
                "start_hour": start_hour,
                "end_hour": end_hour
            })

    return {
        "assignments": assignments,
        "shifts": shifts,
        "total_hours": total_hours,
        "student_hours": dict(student_hours),
        "student_max_hours": student_max_hours,
        "unassigned_hours": remaining_hours
    }


@app.post("/api/generate-schedule")
def generate_schedule():

    err = require_role("faculty")

    if err:
        return err

    db = get_db()

    # Get scheduling rules.
    rules = db.execute(
        """
        SELECT max_hours, max_per_slot
        FROM rules
        WHERE id = 1
        """
    ).fetchone()

    max_hours = int(rules["max_hours"])
    max_per_slot = int(rules["max_per_slot"])

    # Get students and their availability.
    rows = db.execute(
        """
        SELECT
            u.email,
            a.day,
            a.hour
        FROM users u
        LEFT JOIN availability a
            ON u.email = a.email
        WHERE u.role = 'student'
        ORDER BY u.email
        """
    ).fetchall()

    students_by_email = {}

    for row in rows:

        email = row["email"]

        if email not in students_by_email:
            students_by_email[email] = {
                "email": email,
                "availability": []
            }

        if row["day"] is not None:
            students_by_email[email]["availability"].append({
                "day": row["day"],
                "hour": row["hour"]
            })

    students = list(students_by_email.values())

    if not students:
        return jsonify(
            error="No students have registered yet."
        ), 400

    if not any(
        student["availability"]
        for student in students
    ):
        return jsonify(
            error="No students have submitted availability."
        ), 400

    # Generate two alternatives using different random seeds.
    option_a = build_schedule(
        students,
        max_hours,
        max_per_slot,
        seed=42
    )

    option_b = build_schedule(
        students,
        max_hours,
        max_per_slot,
        seed=99
    )

    return jsonify({
        "options": [
            {
                "name": "Option A",
                **option_a
            },
            {
                "name": "Option B",
                **option_b
            }
        ],
        "max_hours": max_hours,
        "max_per_slot": max_per_slot
    })

# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def index():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        port=5000
    )