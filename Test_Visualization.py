import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from scipy.stats import ttest_1samp
from scipy.stats import ttest_rel

file = r"C:\Users\User\Documents\Personal\BridgeWater Uni\Class\Fall 2026\INTD 485\shift_board_random_availability_fixed\shift_board_database_hours_fixed\shift_board\Result\100 students 10k run 500 hours.csv"

df = pd.read_csv(file)

before = df["stddev_available_hours"].dropna()
after = df["stddev_student_hours"].dropna()

print("Number of runs:", len(df))
print("Before Mean STD:", before.mean())
print("After Mean STD:", after.mean())
print("STD Difference:", after.mean() - before.mean())

if before.mean() > 0:
    reduction = (before.mean() - after.mean()) / before.mean() * 100
    print(f"STD Reduction: {reduction:.2f}%")

plt.figure(figsize=(10, 6))

plt.hist(before, bins=30, density=True,
         alpha=0.5, color="orange", edgecolor="black",
         label="Before Scheduling")

plt.hist(after, bins=30, density=True,
         alpha=0.5, color="steelblue", edgecolor="black",
         label="After Scheduling")

for data, color, label in [
    (before, "darkorange", "Before Normal Curve"),
    (after, "blue", "After Normal Curve")
]:
    mean = data.mean()
    std = data.std()

    if std > 0:
        x = np.linspace(mean - 4 * std, mean + 4 * std, 300)
        y = norm.pdf(x, mean, std)
        plt.plot(x, y, color=color, linewidth=2, label=label)

plt.xlabel("Standard Deviation of Hours")
plt.ylabel("Probability Density")
plt.title(f"Before vs After Scheduling ({len(df)} Runs)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()

result1 = ttest_rel(
    df["stddev_available_hours"],
    df["stddev_student_hours"],
    alternative="greater"
)

print("\nTEST 1: BEFORE vs AFTER")
print("T-statistic:", result1.statistic)
print("P-value:", result1.pvalue)

result2 = ttest_1samp(
    df["stddev_student_hours"],
    popmean=0
)

print("\nTEST 2: AFTER vs ZERO")
print("T-statistic:", result2.statistic)
print("P-value:", result2.pvalue)