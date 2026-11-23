import argparse
import csv
import json
import random
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

import ast
from collections import defaultdict
source = (Path(__file__).with_name('app.py')).read_text(encoding='utf-8')
parsed = ast.parse(source)
function = next(node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name == 'build_schedule')
namespace = {'random': random, 'defaultdict': defaultdict,
             'DAYS': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 'HOURS': list(range(8,17))}
exec(compile(ast.Module(body=[function], type_ignores=[]), 'app.py', 'exec'), namespace)
build_schedule, DAYS, HOURS = namespace['build_schedule'], namespace['DAYS'], namespace['HOURS']

ALL_SLOTS = [(day, hour) for day in DAYS for hour in HOURS]


def create_students(db, n, available, rng, min_available=1):
    db.executescript('''
        CREATE TABLE users(email TEXT PRIMARY KEY, role TEXT NOT NULL);
        CREATE TABLE availability(email TEXT NOT NULL, day TEXT NOT NULL, hour INTEGER NOT NULL,
                                  PRIMARY KEY(email, day, hour));
    ''')
    for number in range(1, n + 1):
        email = f'{number}@test.invalid'
        db.execute('INSERT INTO users VALUES (?, ?)', (email, 'student'))
        # Availability is independently randomized for each student.
        # -a is the maximum, not a fixed count for everybody.
        count = rng.randint(min_available, available)
        for day, hour in rng.sample(ALL_SLOTS, count):
            db.execute('INSERT INTO availability VALUES (?, ?, ?)', (email, day, hour))
    db.commit()
    rows = db.execute('''SELECT u.email, a.day, a.hour FROM users u
                        LEFT JOIN availability a ON u.email=a.email
                        ORDER BY CAST(SUBSTR(u.email,1,INSTR(u.email,'@')-1) AS INTEGER)''').fetchall()
    students = {}
    for email, day, hour in rows:
        students.setdefault(email, {'email': email, 'availability': []})
        if day is not None:
            students[email]['availability'].append({'day': day, 'hour': hour})
    return list(students.values())


def validate(schedule, students, target, cap):
    available = {s['email']: {(a['day'], a['hour']) for a in s['availability']} for s in students}
    used = set()
    slot_load = Counter()
    per_student = Counter()
    errors = []
    for a in schedule['assignments']:
        email, slot = a['email'], (a['day'], a['hour'])
        if email not in available or slot not in available[email]:
            errors.append('assignment outside student availability')
        if (email, slot) in used:
            errors.append('duplicate student-hour assignment')
        used.add((email, slot))
        slot_load[slot] += 1
        per_student[email] += 1
    if any(v > cap for v in slot_load.values()):
        errors.append('maximum employees per slot exceeded')
    if any(per_student[email] > len(slots) for email, slots in available.items()):
        errors.append('student assigned more than available hours')
    if len(used) != schedule['total_hours']:
        errors.append('total_hours does not equal assignment count')
    if schedule['total_hours'] > target:
        errors.append('total target exceeded')
    if schedule['unassigned_hours'] != target - schedule['total_hours']:
        errors.append('unassigned_hours mismatch')
    if sum(s['end_hour'] - s['start_hour'] for s in schedule['shifts']) != schedule['total_hours']:
        errors.append('shift durations do not equal scheduled hours')
    return sorted(set(errors)), per_student


def run_test(args):
    if args.students < 1 or args.runs < 1 or args.target_hours < 0 or args.max_per_slot < 1:
        raise ValueError('students and runs must be positive; target-hours >= 0; max-per-slot >= 1')
    if not 0 <= args.min_availability <= args.availability <= len(ALL_SLOTS):
        raise ValueError(f'require 0 <= min-availability <= availability <= {len(ALL_SLOTS)}')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    summaries = []
    student_rows = []
    examples = []
    for run in range(1, args.runs + 1):
        rng = random.Random(args.seed + run - 1)
        with sqlite3.connect(':memory:') as db:
            students = create_students(db, args.students, args.availability, rng, args.min_availability)
        schedule = build_schedule(students, args.target_hours, args.max_per_slot, seed=args.seed + 100000 + run)
        available_hours = [len(s["availability"]) for s in students]
        before_std = statistics.pstdev(available_hours)
        errors, per_student = validate(schedule, students, args.target_hours, args.max_per_slot)
        hours = [per_student[s['email']] for s in students]
        active = sum(h > 0 for h in hours)
        row = {
            'run': run, 'students': args.students, 'min_availability': args.min_availability, 'max_availability': args.availability,
            'mean_available_hours': round(statistics.mean(len(s['availability']) for s in students), 3),
            'target_hours': args.target_hours, 'assigned_hours': schedule['total_hours'],
            'unassigned_hours': schedule['unassigned_hours'], 'students_assigned': active,
            'min_student_hours': min(hours), 'max_student_hours': max(hours),
            'mean_student_hours': round(statistics.mean(hours), 3),
            'stddev_available_hours': round(before_std, 3),
            'stddev_student_hours': round(statistics.pstdev(hours), 3),
            'stddev_change': round(statistics.pstdev(hours) - before_std, 3),
            'passed': len(errors) == 0, 'errors': '; '.join(errors)
        }
        summaries.append(row)
        for student in students:
            student_rows.append({'run': run, 'student': student['email'],
                                 'available_hours': len(student['availability']),
                                 'assigned_hours': per_student[student['email']]})
        if run <= args.print_runs:
            print('  Student         Available   Assigned')
            for student in students:
                print(f"  {student['email']:<16} {len(student['availability']):>3} {per_student[student['email']]:>10}")
            examples.append({'run': run, 'students': students, 'schedule': schedule, 'validation_errors': errors})
        print(f"Run {run:>4}/{args.runs}: assigned={row['assigned_hours']:>3}/{args.target_hours:<3} "
              f"unassigned={row['unassigned_hours']:>3} active={active:>3}/{args.students} "
              f"range={row['min_student_hours']}-{row['max_student_hours']} "
              f"{'PASS' if row['passed'] else 'FAIL'}")
    def write_csv(filename, rows):
        with (out / filename).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    write_csv('run_results.csv', summaries)
    write_csv('student_results.csv', student_rows)
    (out / 'sample_runs.json').write_text(json.dumps(examples, indent=2), encoding='utf-8')
    total_pass = sum(r['passed'] for r in summaries)
    mean_assigned = statistics.mean(r['assigned_hours'] for r in summaries)
    mean_gap = statistics.mean(r['unassigned_hours'] for r in summaries)
    mean_spread = statistics.mean(r['max_student_hours'] - r['min_student_hours'] for r in summaries)
    report = f'''# Shift Board Scheduling Algorithm Test Report

## Configuration

- Students per test (n): **{args.students}**
- Available hours randomly sampled per student: **{args.min_availability} to {args.availability}**, inclusive (out of {len(ALL_SLOTS)} possible hours/week)
- Repeated randomized tests (j): **{args.runs}**
- Target total hours: **{args.target_hours}**
- Maximum students per hour slot: **{args.max_per_slot}**
- Random seed: **{args.seed}**
- Implementation tested: original `build_schedule()` function extracted unchanged from supplied `app.py`.
- Data: generated in temporary SQLite tables and loaded back into the scheduling function. Existing database is untouched.

## Results

| Metric | Result |
|---|---:|
| Passed test runs | {total_pass}/{args.runs} |
| Failed test runs | {args.runs - total_pass}/{args.runs} |
| Mean assigned hours | {mean_assigned:.2f} |
| Mean unassigned hours | {mean_gap:.2f} |
| Mean (maximum minus minimum student-assigned hours) | {mean_spread:.2f} |
| Runs that met total target | {sum(r['unassigned_hours'] == 0 for r in summaries)}/{args.runs} |

## Validated properties

Every test checks that assignments are within submitted availability, that a student cannot be assigned twice to the same slot or beyond their number of available hours, that slot-capacity constraints hold, that assigned hours do not exceed the faculty target, and that shift-duration and unassigned-hour totals are internally consistent.

**Interpretation:** A PASS means the stated constraints held for that run. It does **not** prove the allocation is optimal or that its fairness meets a defined policy. Student-hour spread is a descriptive fairness indicator; when the total target cannot be filled, the algorithm is not guaranteed to find the mathematically maximum feasible allocation.

## Files

- `run_results.csv`: one summary row per test run.
- `student_results.csv`: one row per student per test run.
- `sample_runs.json`: full generated student availability and assignments for the first {min(args.print_runs,args.runs)} runs.
'''
    (out / 'TEST_REPORT.md').write_text(report, encoding='utf-8')
    print(f'\nCompleted: {total_pass}/{args.runs} passed. Results saved to {out.resolve()}')
    return 0 if total_pass == args.runs else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--students', '-n', type=int, default=20, help='number of generated students')
    p.add_argument('--availability', '-a', type=int, default=12, help='MAXIMUM number of random one-hour available slots per student; actual amount varies for each student')
    p.add_argument('--min-availability', type=int, default=1, help='minimum random available slots per student (default 1; choose 0 to include students without availability)')
    p.add_argument('--runs', '-j', type=int, default=100, help='number of separate randomized test runs')
    p.add_argument('--target-hours', type=int, default=30)
    p.add_argument('--max-per-slot', type=int, default=3)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--print-runs', type=int, default=3, help='full examples recorded to JSON')
    p.add_argument('--output', default='test_results')
    raise SystemExit(run_test(p.parse_args()))
