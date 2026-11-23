# Shift Board

A scheduling webpage with two logins:

- **Students** sign up and mark their weekly availability (Mon–Sun, 8am–5pm).
- **Faculty** (pre-created accounts) set scheduling limits and see how many
  students are available in each timeslot, pulled from the real submissions.

Data lives in a local SQLite database (`shift_board.db`), created automatically
the first time you run the app. Nothing is faked in the browser anymore —
accounts, availability, and rules are all read from and written to that file.

## Setup

```bash
cd shift_board
python -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open **http://localhost:5000** in a browser.

## Try it

Two faculty accounts are seeded automatically:

| Email | Password |
|---|---|
| faculty@bridge.edu | faculty123 |

Sign in with one of those to see the rules/demand page, or click
**"Create an account"** on the sign-in screen to register a new student and
try the availability grid.

These seed passwords are for local testing only — change them (and set a
real `SHIFT_BOARD_SECRET` environment variable) before this touches anyone's
real data.

## What's in here

```
shift_board/
├── app.py              Flask backend — routes + SQLite queries
├── shift_board.db       created on first run
├── index.html            page shell
├── static/
│   ├── style.css
│   └── app.js            talks to the API, builds the grids
├── requirements.txt
└── README.md
```

## API

| Method & path | Who | What |
|---|---|---|
| POST /api/signup | anyone | create a student account |
| POST /api/login | anyone | sign in, starts a session |
| POST /api/logout | signed in | ends the session |
| GET /api/me | signed in | who's currently signed in |
| GET /api/availability | student | that student's saved slots |
| PUT /api/availability | student | replace that student's saved slots |
| GET /api/rules | signed in | current max hours / max per slot |
| PUT /api/rules | faculty | update those limits |
| GET /api/demand | faculty | how many students picked each slot |
