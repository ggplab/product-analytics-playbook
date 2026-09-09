"""
Synthetic assignment tables for an A/B test readout.

Same product as ../funnel-weekly: a B2B SaaS onboarding whose step 1 loses
most of the people who enter it. There, a change was judged by comparing
before and after a ship date, and the traffic mix moved underneath the
comparison. Here the same change is run as a randomized experiment
instead, so the mix cannot move between arms.

Two files are written, from the same parameters and the same seed:

  experiment_clean.csv  — assignment works correctly
  experiment_srm.csv    — variant B's onboarding ships as a separate JS
                          bundle that fails to load on older mobile
                          browsers. Those users never reach step 1 and
                          never fire an assignment event, so they are
                          silently missing from the log.

The second file is what a sample-ratio-mismatch check is for. Its bug
both under-fills B and skews B's device mix toward desktop, which
converts better — so skipping the check reads as a larger win than the
experiment actually produced.

Assignment happens at signup, not at first visit: the treatment is the
post-signup onboarding, so signups are the population that can be
affected. That keeps the denominator clean and free of dilution.

Reproducibility: seeded with a numpy Generator (seed=42). Parameters are
exposed as constants below.

Run:
    python generate_data.py
    -> writes data/experiment_clean.csv and data/experiment_srm.csv
"""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# ========== Parameters ==========
SEED = 42

# Planned sample size, computed in analysis.py from the baseline and the
# minimum detectable effect below. 593 per arm rounds up to 600.
N_PER_ARM = 600
RUN_DAYS = 14
START = datetime(2025, 6, 2, tzinfo=timezone.utc)  # a Monday

# Device mix of signups, taken from the funnel-weekly recipe's post-ship era
MOBILE_SHARE = 0.55

# True step-1 survival by device. Control matches funnel-weekly's baseline
# (blended 0.379); treatment adds a flat 8 points to each device.
P_CONTROL = {"desktop": 0.50, "mobile": 0.28}
P_TREATMENT = {"desktop": 0.58, "mobile": 0.36}

# The seeded bug: this share of mobile users assigned to B never appear
# in the log at all, because the variant's bundle failed to load for them.
SRM_MOBILE_B_LOSS = 0.35

rng = np.random.default_rng(SEED)


def assignment_stream():
    """One row per signup: when, which arm, which device, and the outcome.

    The outcome is drawn once per participant from that participant's true
    probability, so the clean and SRM files describe the same underlying
    people — the SRM file just fails to record some of them.
    """
    rows = []
    per_day = N_PER_ARM * 2 // RUN_DAYS
    uid = 0
    for day in range(RUN_DAYS):
        for _ in range(per_day):
            uid += 1
            ts = START + timedelta(
                days=day,
                hours=int(rng.integers(0, 24)),
                minutes=int(rng.integers(0, 60)),
                seconds=int(rng.integers(0, 60)),
            )
            variant = "B" if rng.random() < 0.5 else "A"
            device = "mobile" if rng.random() < MOBILE_SHARE else "desktop"
            p = (P_TREATMENT if variant == "B" else P_CONTROL)[device]
            rows.append(
                {
                    "user_id": f"u{uid:05d}",
                    "assigned_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "variant": variant,
                    "device": device,
                    "survived_step1": int(rng.random() < p),
                    # drawn per participant so the bug is a property of the
                    # logging path, not of who survives
                    "_bundle_failed": int(rng.random() < SRM_MOBILE_B_LOSS),
                }
            )
    rows.sort(key=lambda r: r["assigned_at"])
    return rows


def write(path, rows):
    fields = ["user_id", "assigned_at", "variant", "device", "survived_step1"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    return len(rows)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = assignment_stream()

    n_clean = write(DATA_DIR / "experiment_clean.csv", rows)

    broken = [
        r for r in rows
        if not (r["variant"] == "B" and r["device"] == "mobile" and r["_bundle_failed"])
    ]
    n_srm = write(DATA_DIR / "experiment_srm.csv", broken)

    print(f"experiment_clean.csv — {n_clean:,} rows")
    print(f"experiment_srm.csv   — {n_srm:,} rows ({n_clean - n_srm} dropped by the seeded bug)")
    for label, data in (("clean", rows), ("srm", broken)):
        a = [r for r in data if r["variant"] == "A"]
        b = [r for r in data if r["variant"] == "B"]
        rate = lambda rs: 100 * sum(r["survived_step1"] for r in rs) / len(rs)
        mob = lambda rs: 100 * sum(r["device"] == "mobile" for r in rs) / len(rs)
        print(f"  {label:5s}  A n={len(a):4d} rate={rate(a):5.1f}% mobile={mob(a):4.1f}%   "
              f"B n={len(b):4d} rate={rate(b):5.1f}% mobile={mob(b):4.1f}%")


if __name__ == "__main__":
    main()
