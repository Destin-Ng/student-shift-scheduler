# Shift Board Scheduling Algorithm Test Report

## Configuration

- Students per test (n): **100**
- Available hours randomly sampled per student: **1 to 15**, inclusive (out of 63 possible hours/week)
- Repeated randomized tests (j): **500**
- Target total hours: **500**
- Maximum students per hour slot: **10**
- Random seed: **42**
- Implementation tested: original `build_schedule()` function extracted unchanged from supplied `app.py`.
- Data: generated in temporary SQLite tables and loaded back into the scheduling function. Existing database is untouched.

## Results

| Metric | Result |
|---|---:|
| Passed test runs | 500/500 |
| Failed test runs | 0/500 |
| Mean assigned hours | 500.00 |
| Mean unassigned hours | 0.00 |
| Mean (maximum minus minimum student-assigned hours) | 5.49 |
| Runs that met total target | 500/500 |

## Validated properties

Every test checks that assignments are within submitted availability, that a student cannot be assigned twice to the same slot or beyond their number of available hours, that slot-capacity constraints hold, that assigned hours do not exceed the faculty target, and that shift-duration and unassigned-hour totals are internally consistent.

**Interpretation:** A PASS means the stated constraints held for that run. It does **not** prove the allocation is optimal or that its fairness meets a defined policy. Student-hour spread is a descriptive fairness indicator; when the total target cannot be filled, the algorithm is not guaranteed to find the mathematically maximum feasible allocation.

## Files

- `run_results.csv`: one summary row per test run.
- `student_results.csv`: one row per student per test run.
- `sample_runs.json`: full generated student availability and assignments for the first 3 runs.
