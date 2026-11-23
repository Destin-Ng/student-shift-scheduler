# Shift Board

Shift Board is a web-based student scheduling system that automatically assigns work hours based on student availability and faculty-defined scheduling constraints.

The system is designed to reduce manual scheduling work, respect student availability, and distribute hours more fairly.

## Features

### Student Features

- Create a student account
- Sign in securely
- Submit weekly availability
- Select available times from Monday through Sunday
- Save availability to the database
- View generated schedule information

### Faculty Features

- Sign in using a faculty account
- View student availability
- See how many students are available during each time slot
- Set scheduling constraints
- Set the total number of hours to assign
- Set the maximum number of students allowed in each time slot
- Generate schedules automatically

## Database

Shift Board uses a local SQLite database:

```text
shift_board.db
```

The database is created automatically the first time the application runs.

The application stores:

- user accounts
- student availability
- faculty scheduling rules
- scheduling constraints

The application reads and writes real data from the SQLite database instead of using fake browser data.

## Scheduling Algorithm

The scheduler uses a round-robin style scheduling approach.

Instead of filling one student's schedule completely before moving to another student, the algorithm repeatedly goes through the students and attempts to assign one available hour to each eligible student.

A student can receive an hour only if:

1. The student is available during that time.
2. The student has not already been assigned to that same time slot.
3. The time slot has not reached the faculty-defined maximum number of students.
4. There are still hours remaining to assign.

The basic scheduling logic is:

```python
while remaining_hours > 0:

    made_assignment = False

    for student in students:

        if remaining_hours <= 0:
            break

        eligible = []

        for slot in student["availability"]:

            if slot not in assigned_slots[student["email"]] \
                    and slot_count[slot] < max_per_slot:

                eligible.append(slot)

        if not eligible:
            continue

        selected_slot = eligible[0]

        student_hours[student["email"]] += 1
        slot_count[selected_slot] += 1
        assigned_slots[student["email"]].add(selected_slot)

        remaining_hours -= 1
        made_assignment = True

    if not made_assignment:
        break
```

The scheduler continues until either:

- the requested total number of hours has been assigned, or
- no more valid assignments can be made.

The second condition prevents the program from entering an infinite loop when student availability is too limited to satisfy all requested hours.

## Database-Driven Scheduling

The scheduler does not hard-code student availability.

Student availability is loaded from the SQLite database:

```python
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
```

Faculty scheduling constraints are also loaded directly from the database:

```python
rules = db.execute(
    """
    SELECT max_hours, max_per_slot
    FROM rules
    WHERE id = 1
    """
).fetchone()
```

The two main scheduling constraints are:

- `max_hours` — total number of hours the scheduler attempts to assign
- `max_per_slot` — maximum number of students allowed in the same time slot

This allows faculty to change scheduling limits through the application instead of modifying the code.

## Fair Scheduling

The round-robin approach gives each eligible student an opportunity to receive hours during each scheduling pass.

For example:

```text
Student 1 → receives one available hour
Student 2 → receives one available hour
Student 3 → receives one available hour

Then another scheduling round begins.
```

If a student cannot receive an hour because they are unavailable or their available time slots are already full, the scheduler skips that student and continues.

The scheduler tracks several important values:

```python
student_hours
slot_count
assigned_slots
```

### `student_hours`

Tracks how many hours each student has received.

### `slot_count`

Tracks how many students are currently assigned to each day and hour.

### `assigned_slots`

Prevents a student from being assigned to the same time slot more than once.

## Setup

Move into the project directory:

```bash
cd shift_board
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment.

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Run

Start the Flask application:

```bash
python app.py
```

Then open:

```text
http://localhost:5000
```

in your browser.

## Test Account

A faculty account is automatically created for local testing.

| Email | Password |
|---|---|
| faculty@bridge.edu | faculty123 |

Students can create their own accounts by clicking **Create an account** on the sign-in page.

> The seeded faculty password is intended for local development and testing only. Change it before using the application with real user data.

You should also set a secure `SHIFT_BOARD_SECRET` environment variable before deploying the application.

## Project Structure

```text
shift_board/
│
├── app.py
├── shift_board.db
├── index.html
│
├── static/
│   ├── style.css
│   └── app.js
│
├── requirements.txt
└── README.md
```

### `app.py`

Contains the Flask backend, application routes, scheduling logic, authentication logic, and SQLite database queries.

### `shift_board.db`

SQLite database containing users, availability, and scheduling rules.

This file is created automatically when needed.

### `index.html`

Contains the main webpage structure.

### `static/style.css`

Contains the styling for the application.

### `static/app.js`

Handles frontend functionality, API requests, availability grids, scheduling controls, and interactions with the Flask backend.

### `requirements.txt`

Contains the Python packages required to run the application.

## API

The frontend communicates with the Flask backend through API endpoints.

| Method & Path | Access | Purpose |
|---|---|---|
| `POST /api/signup` | Anyone | Create a student account |
| `POST /api/login` | Anyone | Sign in and start a session |
| `POST /api/logout` | Signed in | End the current session |
| `GET /api/me` | Signed in | Return the currently signed-in user |
| `GET /api/availability` | Student | Get the student's saved availability |
| `PUT /api/availability` | Student | Replace the student's saved availability |
| `GET /api/rules` | Signed in | Get current scheduling constraints |
| `PUT /api/rules` | Faculty | Update scheduling constraints |
| `GET /api/demand` | Faculty | Get the number of students available in each time slot |

## Technologies

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript

## Example Scheduling Process

Suppose faculty sets:

```text
Total hours: 30
Maximum students per time slot: 2
```

The scheduler:

1. Reads all student availability from the database.
2. Reads the faculty constraints from the database.
3. Goes through the students using the round-robin scheduling process.
4. Finds valid available time slots.
5. Assigns one hour to an eligible student.
6. Updates the student's assigned hours.
7. Updates the number of students assigned to that time slot.
8. Continues until 30 hours are assigned or no more valid assignments are possible.

## Project Purpose

The purpose of Shift Board is to explore how scheduling algorithms can improve student employee scheduling.

The main goals are to:

- reduce manual scheduling work
- respect student availability
- distribute work hours fairly
- automatically enforce scheduling constraints
- make schedule generation faster
- store scheduling data in a structured database

## Future Improvements

Possible future improvements include:

- improved fairness optimization
- student-specific preferred or maximum hours
- schedule quality scoring
- conflict detection
- schedule filtering
- improved visual schedule views
- exporting schedules
- comparing multiple generated schedules
- statistical evaluation of scheduling fairness
- notifications when schedules are published

## Security Notes

The default faculty login is intended only for development and testing.

Before deploying Shift Board:

- change the default faculty password
- use a secure `SHIFT_BOARD_SECRET`
- avoid committing sensitive database files
- use secure production authentication settings
- protect personal student information

## Author

Destin Ng