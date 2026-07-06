"""
Synthetic data generator for a SaaS monthly cohort retention analysis.

Simulates, for a hypothetical B2B SaaS product, each user's signup month
(cohort) and whether they stayed active in each subsequent month, then
writes the result to a single long-format CSV.

Design points (used as interpretation exercises):
- Retention increases with plan tier (free/starter/pro/enterprise) — a clear
  step pattern
- The paid_search channel takes an extra retention hit starting 6 months
  after signup (modeling a lower-quality-lead hypothesis)
- The 2024-05 cohort has a sharp retention drop at the 1-month mark
  (an injected anomaly modeling a one-off onboarding issue)

Reproducibility: seeded with a numpy Generator (seed=42). Parameters are
exposed as constants at the top of the file, so changing them regenerates
data with different patterns.

Run:
    python generate_data.py
    -> writes data/cohort_activity.csv (user_id, signup_month, plan, channel, activity_month)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ========== Parameters ==========
SEED = 42
N_USERS = 2500

# Monthly cohorts: 2024-01 through 2024-09 (9 cohorts)
COHORT_MONTHS = pd.period_range("2024-01", "2024-09", freq="M")
# Observation cutoff: 2025-03 (14 months of observation for the earliest cohort)
OBSERVATION_END = pd.Period("2025-03", freq="M")

PLANS = [("free", 0.60), ("starter", 0.22), ("pro", 0.13), ("enterprise", 0.05)]
CHANNELS = [("organic", 0.35), ("paid_search", 0.30), ("referral", 0.20), ("content", 0.15)]

# Monthly retention hazard by plan (probability of still being active next
# month, given the user is active this month)
BASE_MONTHLY_RETENTION = {
    "free": 0.72,
    "starter": 0.85,
    "pro": 0.90,
    "enterprise": 0.95,
}

# Channel-level retention multiplier (relative to organic)
CHANNEL_MULTIPLIER = {
    "organic": 1.00,
    "referral": 1.05,
    "content": 0.98,
    "paid_search": 0.90,
}

# Injected anomaly 1: paid_search retention takes an extra hit from month 6 onward
PAID_SEARCH_LONG_TERM_OFFSET = 6
PAID_SEARCH_LONG_TERM_PENALTY = 0.85

# Injected anomaly 2: the 2024-05 cohort has a sharp drop at the 1-month mark
ANOMALY_COHORT = pd.Period("2024-05", freq="M")
ANOMALY_OFFSET = 1
ANOMALY_PENALTY = 0.45


def weighted_choice(rng, weighted_items, size):
    items = [item for item, _ in weighted_items]
    weights = np.array([w for _, w in weighted_items])
    weights = weights / weights.sum()
    return rng.choice(items, size=size, p=weights)


def monthly_retention(plan, channel, cohort_month, month_offset):
    """month_offset (0 = signup month) -> hazard of surviving from offset-1 to offset."""
    hazard = BASE_MONTHLY_RETENTION[plan] * CHANNEL_MULTIPLIER[channel]

    if channel == "paid_search" and month_offset >= PAID_SEARCH_LONG_TERM_OFFSET:
        hazard *= PAID_SEARCH_LONG_TERM_PENALTY

    if cohort_month == ANOMALY_COHORT and month_offset == ANOMALY_OFFSET:
        hazard *= ANOMALY_PENALTY

    return float(np.clip(hazard, 0.01, 0.99))


def simulate_user_activity(rng, user_id, signup_month, plan, channel):
    """Build the list of (user_id, signup_month, plan, channel, activity_month) rows for one user.

    Month 0 (the signup month) is always counted as active. For each
    subsequent month, survival is a Bernoulli draw against the hazard; once
    a user churns they never come back (the standard "logo retention"
    assumption).
    """
    rows = [(user_id, str(signup_month), plan, channel, str(signup_month))]

    month_offset = 1
    current_month = signup_month + 1
    while current_month <= OBSERVATION_END:
        p_retain = monthly_retention(plan, channel, signup_month, month_offset)
        if rng.random() > p_retain:
            break
        rows.append((user_id, str(signup_month), plan, channel, str(current_month)))
        current_month += 1
        month_offset += 1

    return rows


def generate():
    rng = np.random.default_rng(SEED)

    user_ids = np.arange(1, N_USERS + 1)
    signup_months = rng.choice(COHORT_MONTHS, size=N_USERS)
    plans = weighted_choice(rng, PLANS, N_USERS)
    channels = weighted_choice(rng, CHANNELS, N_USERS)

    all_rows = []
    for uid, signup_month, plan, channel in zip(user_ids, signup_months, plans, channels):
        all_rows.extend(
            simulate_user_activity(rng, int(uid), pd.Period(signup_month, freq="M"), plan, channel)
        )

    df = pd.DataFrame(
        all_rows,
        columns=["user_id", "signup_month", "plan", "channel", "activity_month"],
    )
    return df


def print_summary(df):
    n_users = df["user_id"].nunique()
    print(f"Users: {n_users}")
    print(f"Activity rows: {len(df)}")
    print("Plan distribution:")
    print(df.drop_duplicates("user_id")["plan"].value_counts().to_string())
    print("Channel distribution:")
    print(df.drop_duplicates("user_id")["channel"].value_counts().to_string())
    print("Cohort sizes (signup_month):")
    print(df.drop_duplicates("user_id")["signup_month"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    df = generate()
    print_summary(df)

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "cohort_activity.csv"
    df.to_csv(out_path, index=False)

    print(f"\nWritten: {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
