"""
Synthetic event-log generator for a weekly new-visitor cohort funnel.

Simulates raw telemetry from a small self-hosted analytics setup (an
append-only JSONL event log plus a hand-maintained list of internal
actor IDs) for a hypothetical B2B SaaS product over 10 ISO weeks, then
writes the events exactly as a real instrumentation endpoint would.

Design points (used as interpretation exercises):
- Onboarding tooltips ship at the start of week 6, lifting the
  "survived step 1" rate for BOTH device segments
- The same week, the product gets picked up by a mobile-heavy referral
  channel, so the traffic mix flips from ~30% mobile to ~60% mobile.
  Mobile converts far worse, so the blended weekly rate barely moves
  even though both segments improved (a mix-shift / Simpson's-style effect)
- Some visitors return in a later week and convert then, and returners
  convert better than first-time visitors. Bucketing by calendar week
  instead of by first-seen week therefore credits the wrong week
- Three internal actor IDs (the founder + two testers) are first seen in
  week 1 and almost always activate, so first-seen-week cohorting files
  their whole history under the launch week alone

Reproducibility: seeded with a numpy Generator (seed=42). Parameters are
exposed as constants at the top of the file, so changing them regenerates
data with different patterns.

Run:
    python generate_data.py
    -> writes data/telemetry.jsonl  (one JSON event per line)
       writes data/actors.json      (internal/owner anonIds to exclude)
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# ========== Parameters ==========
SEED = 42

# 10 ISO weeks of acquisition, each starting on a Monday. The log keeps
# running for TAIL_WEEKS after the last cohort so that every cohort gets a
# full conversion window (see CONVERSION_WINDOW_DAYS in analysis.py) —
# without the tail, the newest cohort is right-censored and looks worse
# than it is purely because its returners had nowhere to land.
FIRST_MONDAY = datetime(2025, 3, 3, tzinfo=timezone.utc)
N_WEEKS = 10
TAIL_WEEKS = 3

# New (first-ever-seen) visitors per week. Week 6 is the referral pickup.
NEW_VISITORS = [110, 130, 144, 160, 172, 300, 264, 224, 196, 180]

# Share of new visitors arriving on mobile. The referral channel that hits
# in week 6 is read mostly on phones.
MOBILE_SHARE = [0.28, 0.30, 0.29, 0.31, 0.30, 0.64, 0.62, 0.62, 0.60, 0.58]

# Onboarding tooltips ship at the start of this week (0-indexed)
SHIP_WEEK_INDEX = 5

# visit -> signup
P_SIGNUP = {"desktop": 0.42, "mobile": 0.30}
# signup -> reached step 2 ("survived step 1"): the step the tooltips target
P_STEP2 = {"desktop": 0.44, "mobile": 0.18}
TOOLTIP_LIFT = {"desktop": 1.45, "mobile": 1.44}
# step 2 -> step 3, step 3 -> activated
P_STEP3 = {"desktop": 0.72, "mobile": 0.66}
P_ACTIVATE = {"desktop": 0.68, "mobile": 0.58}

# Returning behaviour: a visitor who did not sign up on the first visit may
# come back days later, and returners are more motivated than cold traffic.
RETURN_RATE = 0.28
RETURN_GAP_DAYS = (3, 16)
RETURN_SIGNUP_MULT = 1.6

# Where inside step 1 a signup who never reached step 2 was last seen.
# "norecord" = the browser closed without firing a sessionEnd, which every
# real client-side event log has some of.
STEP1_EXIT_PHASES = ["email_verify", "workspace_name", "plan_select", "data_source_pick", "norecord"]
STEP1_EXIT_WEIGHTS = {
    ("desktop", False): [0.18, 0.14, 0.34, 0.19, 0.15],
    ("desktop", True): [0.22, 0.17, 0.16, 0.28, 0.17],
    ("mobile", False): [0.12, 0.10, 0.21, 0.43, 0.14],
    ("mobile", True): [0.13, 0.11, 0.11, 0.49, 0.16],
}

# Internal actors: the founder and two testers, on the exclusion list.
INTERNAL_IDS = ["0f4c1a77e2b93d10", "6b8e05d3a417cc92", "c92d7f10b4e86a35"]
INTERNAL_SESSIONS_PER_WEEK = [26, 22, 11, 8, 7, 9, 7, 6, 6, 5]
P_INTERNAL_ACTIVATE = 0.82

rng = np.random.default_rng(SEED)


def week_start(i):
    return FIRST_MONDAY + timedelta(weeks=i)


def random_ts_in_week(i):
    """A plausible visit timestamp inside week i (daytime-weighted)."""
    day = int(rng.integers(0, 7))
    hour = int(rng.choice(range(24), p=_HOUR_WEIGHTS))
    return week_start(i) + timedelta(
        days=day, hours=hour, minutes=int(rng.integers(0, 60)), seconds=int(rng.integers(0, 60))
    )


# Daytime-weighted hour-of-day distribution (UTC), normalised.
_HOUR_RAW = np.array(
    [2, 1, 1, 1, 1, 2, 4, 7, 11, 14, 15, 14, 13, 14, 15, 15, 14, 12, 10, 9, 8, 6, 4, 3],
    dtype=float,
)
_HOUR_WEIGHTS = _HOUR_RAW / _HOUR_RAW.sum()


def new_anon_id():
    return "".join(f"{b:02x}" for b in rng.integers(0, 256, size=8))


def iso(ts):
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(events, ts, anon_id, event, data=None):
    row = {"ts": iso(ts), "anonId": anon_id, "event": event}
    if data:
        row["data"] = data
    events.append((ts, row))


def tooltips_active(ts):
    return ts >= week_start(SHIP_WEEK_INDEX)


def simulate_onboarding(events, anon_id, device, start_ts):
    """Emit the post-signup part of a session. Returns the deepest step reached."""
    lift = TOOLTIP_LIFT[device] if tooltips_active(start_ts) else 1.0
    t = start_ts

    emit(events, t, anon_id, "signup", {"device": device})
    t += timedelta(seconds=int(rng.integers(20, 180)))
    emit(events, t, anon_id, "stepStart", {"step": 1})

    if rng.random() >= min(P_STEP2[device] * lift, 0.95):
        # Died inside step 1 — record where, the way a real client would.
        weights = STEP1_EXIT_WEIGHTS[(device, tooltips_active(start_ts))]
        phase = str(rng.choice(STEP1_EXIT_PHASES, p=weights))
        t += timedelta(seconds=int(rng.integers(10, 900)))
        if phase != "norecord":
            emit(
                events,
                t,
                anon_id,
                "sessionEnd",
                {"step": 1, "phase": phase, "dwellSec": int((t - start_ts).total_seconds())},
            )
        return 1

    t += timedelta(seconds=int(rng.integers(60, 600)))
    emit(events, t, anon_id, "stepStart", {"step": 2})

    if rng.random() >= P_STEP3[device]:
        t += timedelta(seconds=int(rng.integers(30, 900)))
        emit(
            events,
            t,
            anon_id,
            "sessionEnd",
            {"step": 2, "phase": "invite_teammate", "dwellSec": int((t - start_ts).total_seconds())},
        )
        return 2

    t += timedelta(seconds=int(rng.integers(60, 600)))
    emit(events, t, anon_id, "stepStart", {"step": 3})

    if rng.random() >= P_ACTIVATE[device]:
        t += timedelta(seconds=int(rng.integers(30, 900)))
        emit(
            events,
            t,
            anon_id,
            "sessionEnd",
            {"step": 3, "phase": "run_report", "dwellSec": int((t - start_ts).total_seconds())},
        )
        return 3

    t += timedelta(seconds=int(rng.integers(60, 480)))
    emit(events, t, anon_id, "activated", {"device": device})
    return 4


def simulate_visitor(events, week_index):
    device = "mobile" if rng.random() < MOBILE_SHARE[week_index] else "desktop"
    anon_id = new_anon_id()

    first_visit = random_ts_in_week(week_index)
    emit(events, first_visit, anon_id, "visit", {"device": device})

    if rng.random() < P_SIGNUP[device]:
        simulate_onboarding(events, anon_id, device, first_visit + timedelta(seconds=int(rng.integers(15, 240))))
        return

    # Did not sign up on the first visit. Some come back later — and the ones
    # who bother to come back are more motivated than the cold traffic was.
    if rng.random() >= RETURN_RATE:
        return

    gap = timedelta(
        days=int(rng.integers(*RETURN_GAP_DAYS)),
        hours=int(rng.integers(0, 24)),
        minutes=int(rng.integers(0, 60)),
    )
    return_visit = first_visit + gap
    if return_visit >= week_start(N_WEEKS + TAIL_WEEKS):
        return

    emit(events, return_visit, anon_id, "visit", {"device": device})
    if rng.random() < min(P_SIGNUP[device] * RETURN_SIGNUP_MULT, 0.95):
        simulate_onboarding(events, anon_id, device, return_visit + timedelta(seconds=int(rng.integers(15, 240))))


def simulate_internal(events, week_index):
    for _ in range(INTERNAL_SESSIONS_PER_WEEK[week_index]):
        anon_id = str(rng.choice(INTERNAL_IDS))
        device = "desktop" if rng.random() < 0.85 else "mobile"
        ts = random_ts_in_week(week_index)
        emit(events, ts, anon_id, "visit", {"device": device})
        t = ts + timedelta(seconds=int(rng.integers(5, 60)))
        emit(events, t, anon_id, "signup", {"device": device})
        for step in (1, 2, 3):
            t += timedelta(seconds=int(rng.integers(20, 200)))
            emit(events, t, anon_id, "stepStart", {"step": step})
        t += timedelta(seconds=int(rng.integers(20, 200)))
        if rng.random() < P_INTERNAL_ACTIVATE:
            emit(events, t, anon_id, "activated", {"device": device})
        else:
            emit(events, t, anon_id, "sessionEnd", {"step": 3, "phase": "run_report", "dwellSec": 120})


def main():
    events = []
    for w in range(N_WEEKS):
        for _ in range(NEW_VISITORS[w]):
            simulate_visitor(events, w)
        simulate_internal(events, w)

    # A real append-only log is ordered by arrival time, not by user.
    events.sort(key=lambda pair: pair[0])

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "telemetry.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for _, row in events:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    actors = {
        "owner": [INTERNAL_IDS[0]],
        "internal": INTERNAL_IDS[1:],
        "note": "anonIds belonging to the team. Excluded from every funnel number.",
    }
    (DATA_DIR / "actors.json").write_text(json.dumps(actors, indent=2) + "\n", encoding="utf-8")

    visitors = {row["anonId"] for _, row in events}
    print(f"wrote {out} — {len(events):,} events, {len(visitors):,} distinct anonIds")
    print(f"wrote {DATA_DIR / 'actors.json'} — {len(INTERNAL_IDS)} internal anonIds")
    print(f"file size: {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
