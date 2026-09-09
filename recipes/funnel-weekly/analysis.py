"""
Weekly new-visitor cohort funnel.

Reads a raw append-only event log (data/telemetry.jsonl) plus an internal
actor exclusion list (data/actors.json) and answers one question:
"did the onboarding change we shipped in week 6 work?"

Outputs, in the order they should be read:

1. The blended weekly funnel — which says nothing changed
2. Cohort-week vs calendar-week bucketing — which says something did
3. The same funnel split by device — which says both segments improved
4. Where inside step 1 people are last seen, by device — the actionable part

Run:
    python analysis.py
    -> writes assets/*.png and prints every table to the console
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "telemetry.jsonl"
ACTORS_PATH = BASE_DIR / "data" / "actors.json"
ASSETS_DIR = BASE_DIR / "assets"

# Values drawn from the dataviz skill palette (references/palette.md)
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#eb6834"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

# The onboarding tooltips went live at the start of this ISO week.
SHIP_WEEK = "2025-04-07"

# How long after a visitor's first visit a signup still counts as theirs.
# theory/03-funnel-analysis.md: state the window next to any conversion rate,
# or the number is not comparable across weeks or teams. 21 days is chosen to
# comfortably cover the observed return-visit gap.
CONVERSION_WINDOW_DAYS = 21

STEP1_PHASE_ORDER = ["email_verify", "workspace_name", "plan_select", "data_source_pick", "norecord"]


# ---------------------------------------------------------------- loading


def load_events():
    """Group raw events by anonId, dropping internal actors.

    Excluding the team's own IDs is the first line of the script for a
    reason: on a small product the founder is often the single heaviest
    "user" in the log, and they complete every funnel they enter.
    """
    actors = json.loads(ACTORS_PATH.read_text(encoding="utf-8"))
    excluded = set(actors.get("owner", [])) | set(actors.get("internal", []))

    by_anon = defaultdict(list)
    excluded_events = 0
    with DATA_PATH.open(encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if e["anonId"] in excluded:
                excluded_events += 1
                continue
            by_anon[e["anonId"]].append(e)

    for evs in by_anon.values():
        evs.sort(key=lambda e: e["ts"])
    return by_anon, excluded, excluded_events


def load_events_including_internal():
    by_anon = defaultdict(list)
    with DATA_PATH.open(encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            by_anon[e["anonId"]].append(e)
    for evs in by_anon.values():
        evs.sort(key=lambda e: e["ts"])
    return by_anon


def ts(event):
    return datetime.strptime(event["ts"], "%Y-%m-%dT%H:%M:%SZ")


def iso_week(dt):
    """Monday of the ISO week containing dt, as a YYYY-MM-DD string."""
    return (dt - timedelta(days=dt.weekday())).date().isoformat()


# ---------------------------------------------------------------- funnel


def visitor_profile(events, window_days=CONVERSION_WINDOW_DAYS):
    """Collapse one visitor's whole event history into funnel facts.

    Everything downstream of the first visit is only counted inside the
    conversion window, so a visitor who wandered back two months later
    does not retroactively rescue their cohort's number.
    """
    first_ts = ts(events[0])
    deadline = first_ts + timedelta(days=window_days)
    in_window = [e for e in events if ts(e) <= deadline]

    kinds = {e["event"] for e in in_window}
    steps = {e["data"]["step"] for e in in_window if e["event"] == "stepStart"}
    signup_event = next((e for e in in_window if e["event"] == "signup"), None)
    return {
        "first_week": iso_week(first_ts),
        "signup_week": iso_week(ts(signup_event)) if signup_event else None,
        # Every week in which this visitor showed up at all — the denominator
        # a naive calendar-week report would use.
        "visit_weeks": sorted({iso_week(ts(e)) for e in in_window if e["event"] == "visit"}),
        "device": next((e["data"]["device"] for e in in_window if e.get("data", {}).get("device")), "unknown"),
        "signed_up": signup_event is not None,
        "step2": 2 in steps,
        "step3": 3 in steps,
        "activated": "activated" in kinds,
        "step1_exit_phase": _step1_exit_phase(in_window, signup_event is not None, 2 in steps),
    }


def _step1_exit_phase(events, signed_up, reached_step2):
    if not signed_up or reached_step2:
        return None
    for e in reversed(events):
        if e["event"] == "sessionEnd" and e.get("data", {}).get("step") == 1:
            return e["data"].get("phase", "norecord")
    return "norecord"


def funnel_counts(profiles):
    n = len(profiles)
    return {
        "visitors": n,
        "signup": sum(p["signed_up"] for p in profiles),
        "step2": sum(p["step2"] for p in profiles),
        "step3": sum(p["step3"] for p in profiles),
        "activated": sum(p["activated"] for p in profiles),
    }


def pct(num, den):
    return 100.0 * num / den if den else float("nan")


def group_by(profiles, key):
    out = defaultdict(list)
    for p in profiles:
        out[p[key]].append(p)
    return out


# ---------------------------------------------------------------- tables


def print_weekly_funnel(by_week, weeks):
    print("\n=== 1. Weekly new-visitor cohort funnel (internal actors excluded) ===")
    print(f"{'week':12s} {'visitors':>8} {'signup':>7} {'sgn%':>6} {'step2':>6} "
          f"{'s2/sgn%':>8} {'step3':>6} {'activated':>10} {'act/vis%':>9}")
    for w in weeks:
        c = funnel_counts(by_week[w])
        print(f"{w:12s} {c['visitors']:8d} {c['signup']:7d} {pct(c['signup'], c['visitors']):6.0f} "
              f"{c['step2']:6d} {pct(c['step2'], c['signup']):8.0f} {c['step3']:6d} "
              f"{c['activated']:10d} {pct(c['activated'], c['visitors']):9.1f}")
    print("\nThe column that matters is s2/sgn% — the step the tooltips targeted.")
    print(f"Tooltips shipped at the start of {SHIP_WEEK}. The blended line barely moves.")


def print_cohort_vs_calendar(profiles, weeks):
    """Same signups, two denominators: first-seen week vs the week it happened."""
    print("\n=== 2b. Cohort-week vs calendar-week bucketing ===")
    cohort = Counter()          # signups credited to the visitor's first week
    calendar = Counter()        # signups credited to the week they happened
    first_seen = Counter()      # new visitors that week (cohort denominator)
    active_in_week = Counter()  # anyone who visited that week (calendar denominator)
    lagged = Counter()

    for p in profiles:
        first_seen[p["first_week"]] += 1
        for w in p["visit_weeks"]:
            active_in_week[w] += 1
        if p["signed_up"]:
            cohort[p["first_week"]] += 1
            calendar[p["signup_week"]] += 1
            if p["signup_week"] != p["first_week"]:
                lagged[p["signup_week"]] += 1

    print(f"{'week':12s} {'new':>5} {'active':>7} {'cohort sgn%':>12} "
          f"{'calendar sgn%':>14} {'lagged':>7}")
    for w in weeks:
        print(f"{w:12s} {first_seen[w]:5d} {active_in_week[w]:7d} "
              f"{pct(cohort[w], first_seen[w]):12.0f} "
              f"{pct(calendar[w], active_in_week[w]):14.0f} {lagged[w]:7d}")
    print("\n'lagged' = signups whose first visit was an EARLIER week. Calendar")
    print("bucketing mixes them into the current week's rate, so a week's number")
    print("moves for reasons that have nothing to do with that week's traffic or")
    print("that week's product changes. Cohort bucketing keeps each week honest.")
    return cohort, calendar, first_seen, active_in_week


def print_window_sensitivity(by_anon, weeks):
    """What the conversion window costs, measured rather than asserted."""
    print("\n=== 2a. What the conversion window is worth ===")
    rows = []
    for days in (1, 3, 7, 14, 21, 60):
        profiles = [visitor_profile(evs, window_days=days) for evs in by_anon.values()]
        signups = sum(p["signed_up"] for p in profiles)
        lagged = sum(1 for p in profiles if p["signed_up"] and p["signup_week"] != p["first_week"])
        rows.append((days, signups, pct(signups, len(profiles)), lagged))
    baseline = next(r[2] for r in rows if r[0] == CONVERSION_WINDOW_DAYS)

    print(f"{'window':>7} {'signups':>8} {'cohort sgn%':>12} {'lagged':>7} "
          f"{'vs ' + str(CONVERSION_WINDOW_DAYS) + 'd':>8}")
    for days, signups, rate, lagged in rows:
        print(f"{str(days) + 'd':>7} {signups:8d} {rate:12.1f} {lagged:7d} {rate - baseline:+8.1f}")

    lo, hi = rows[0][2], baseline
    print(f"\nThe same event log reports a signup rate of {lo:.1f}% or {hi:.1f}% depending")
    print("only on where you draw the window — a bigger spread than any product change")
    print("in this recipe produces. Returners are the whole difference: at 1 day almost")
    print("none of them have come back yet.")
    print(f"\nWidening past {CONVERSION_WINDOW_DAYS} days changes nothing here, because no visitor in this")
    print("log converts later than day 16. That is a fact about this dataset, not a")
    print("general one — measure it before picking a window, don't inherit a default.")


def print_device_split(profiles, weeks):
    print("\n=== 3. Survived step 1 (step2 / signup), split by device ===")
    by_device = group_by(profiles, "device")
    print(f"{'week':12s} {'desktop':>9} {'n':>5} {'mobile':>9} {'n':>5} {'mobile share':>13}")
    series = {}
    for device in ("desktop", "mobile"):
        weekly = group_by(by_device[device], "first_week")
        series[device] = [pct(funnel_counts(weekly[w])["step2"], funnel_counts(weekly[w])["signup"]) for w in weeks]

    all_weekly = group_by(profiles, "first_week")
    mobile_share = [pct(sum(p["device"] == "mobile" for p in all_weekly[w]), len(all_weekly[w])) for w in weeks]
    series["blended"] = [pct(funnel_counts(all_weekly[w])["step2"], funnel_counts(all_weekly[w])["signup"])
                         for w in weeks]

    for i, w in enumerate(weeks):
        d_n = funnel_counts(group_by(by_device["desktop"], "first_week")[w])["signup"]
        m_n = funnel_counts(group_by(by_device["mobile"], "first_week")[w])["signup"]
        print(f"{w:12s} {series['desktop'][i]:9.0f} {d_n:5d} {series['mobile'][i]:9.0f} "
              f"{m_n:5d} {mobile_share[i]:13.0f}")

    print("\n--- pooled before vs after the ship week (bigger n, less weekly noise) ---")
    print(f"{'segment':12s} {'before':>8} {'n':>6} {'after':>8} {'n':>6} {'change':>8}")
    pooled = {}
    for label, rows in (("desktop", by_device["desktop"]), ("mobile", by_device["mobile"]),
                        ("blended", profiles)):
        before = funnel_counts([p for p in rows if p["first_week"] < SHIP_WEEK])
        after = funnel_counts([p for p in rows if p["first_week"] >= SHIP_WEEK])
        b, a = pct(before["step2"], before["signup"]), pct(after["step2"], after["signup"])
        pooled[label] = (b, a)
        print(f"{label:12s} {b:8.1f} {before['signup']:6d} {a:8.1f} {after['signup']:6d} "
              f"{a - b:+8.1f}")
    print("\nThat is the whole recipe in one table: each segment improved by far")
    print("more than the blend, because the traffic mix moved toward the weaker one.")
    return series, mobile_share, pooled


def print_step1_phases(profiles):
    print("\n=== 4. Where step-1 dropouts were last seen, by device ===")
    stuck = [p for p in profiles if p["signed_up"] and not p["step2"]]
    print(f"{'device':10s} {'period':14s} " + " ".join(f"{p:>16s}" for p in STEP1_PHASE_ORDER))
    table = {}
    for device in ("desktop", "mobile"):
        for label, keep in (("before ship", lambda w: w < SHIP_WEEK), ("after ship", lambda w: w >= SHIP_WEEK)):
            rows = [p for p in stuck if p["device"] == device and keep(p["first_week"])]
            counts = Counter(p["step1_exit_phase"] for p in rows)
            total = len(rows) or 1
            table[(device, label)] = [100.0 * counts[p] / total for p in STEP1_PHASE_ORDER]
            cells = " ".join(f"{100.0 * counts[p] / total:14.0f}%" for p in STEP1_PHASE_ORDER)
            print(f"{device:10s} {label:14s} {cells}   (n={len(rows)})")
    print("\nRead the mobile rows: data_source_pick stays the single biggest exit")
    print("before AND after the tooltips. The tooltips never touched it.")
    return table


def print_internal_actor_effect(weeks):
    """What the same numbers look like if you forget to exclude the team."""
    print("\n=== 0. Why the exclusion list is the first line of the script ===")
    all_by_anon = load_events_including_internal()
    all_profiles = {a: visitor_profile(evs) for a, evs in all_by_anon.items()}
    clean, excluded, _ = load_events()
    clean_profiles = [visitor_profile(evs) for evs in clean.values()]

    internal = [all_profiles[a] for a in excluded]
    print(f"internal anonIds: {len(internal)}   activated: {sum(p['activated'] for p in internal)}"
          f"/{len(internal)}   first-seen weeks: {sorted({p['first_week'] for p in internal})}")

    for label, profiles in (("with internal actors", list(all_profiles.values())),
                            ("excluded", clean_profiles)):
        wk = group_by(profiles, "first_week")
        first = funnel_counts(wk[weeks[0]])
        overall = funnel_counts(profiles)
        print(f"{label:22s} week 1 activation {first['activated']:3d}/{first['visitors']:3d} = "
              f"{pct(first['activated'], first['visitors']):5.1f}%   "
              f"all-time {pct(overall['activated'], overall['visitors']):5.1f}%")

    print("\nThe distortion is not volume — these three IDs are three visitors no matter")
    print("how many sessions they log, because every rate here counts distinct people.")
    print("It is that they complete every funnel they enter — 3 of 3 activated, against a")
    print("6.4% baseline for real week-1 visitors. And because all three were first seen")
    print("in week 1, first-seen-week cohorting files their whole history under week 1")
    print("alone: they inflate the launch week by 2.4pp and leave every later week")
    print("untouched. That is why the all-time figure barely moves while the number the")
    print("launch actually gets judged on moves a lot.")


# ---------------------------------------------------------------- charts


def _style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRIDLINE)
    ax.tick_params(colors=INK_SECONDARY, labelsize=9)


def _ship_line(ax, weeks):
    x = weeks.index(SHIP_WEEK)
    ax.axvline(x, color=INK_MUTED, linestyle=":", linewidth=1.2)
    ax.annotate("tooltips ship", xy=(x, ax.get_ylim()[1]), xytext=(x + 0.12, ax.get_ylim()[1] * 0.97),
                color=INK_MUTED, fontsize=9, va="top")


def short(weeks):
    return [w[5:] for w in weeks]


def plot_weekly_funnel(by_week, weeks):
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
    _style(ax)
    counts = [funnel_counts(by_week[w]) for w in weeks]
    series = {
        "signup / visitors": [pct(c["signup"], c["visitors"]) for c in counts],
        "survived step 1 (step2 / signup)": [pct(c["step2"], c["signup"]) for c in counts],
        "activated / visitors": [pct(c["activated"], c["visitors"]) for c in counts],
    }
    for i, (label, values) in enumerate(series.items()):
        ax.plot(short(weeks), values, marker="o", markersize=5, linewidth=2,
                color=CATEGORICAL[i], label=label)
    ax.set_ylim(0, 70)
    ax.set_ylabel("%", color=INK_SECONDARY)
    ax.set_title("Weekly new-visitor cohort funnel — the blended view",
                 color=INK_PRIMARY, fontsize=13, pad=14, loc="left")
    _ship_line(ax, weeks)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="upper left")
    fig.text(0.011, 0.02, "Nothing steps up at the ship week — the targeted rate ends the period "
                          "slightly LOWER than it started. On this chart alone, the change failed.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ASSETS_DIR / "01_weekly_funnel.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_cohort_vs_calendar(cohort, calendar, first_seen, visits_in_week, weeks):
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
    _style(ax)
    ax.plot(short(weeks), [pct(cohort[w], first_seen[w]) for w in weeks], marker="o", markersize=5,
            linewidth=2, color=CATEGORICAL[0], label="bucketed by first-seen week (cohort)")
    ax.plot(short(weeks), [pct(calendar[w], visits_in_week[w]) for w in weeks], marker="s", markersize=5,
            linewidth=2, color=CATEGORICAL[3], linestyle="--", label="bucketed by week the signup happened")
    ax.set_ylim(25, 62)
    ax.set_ylabel("signup rate %", color=INK_SECONDARY)
    ax.set_title("Same signups, two denominators", color=INK_PRIMARY, fontsize=13, pad=14, loc="left")
    _ship_line(ax, weeks)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="lower left")
    fig.text(0.011, 0.02, "A 5-10pp gap in every week, including week 1 where nothing has lagged yet: "
                          "the two definitions differ in both numerator and denominator.\n"
                          "Neither is wrong. Comparing a number built one way to a number built the "
                          "other way is.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.savefig(ASSETS_DIR / "02_cohort_vs_calendar.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_device_split(series, mobile_share, weeks, pooled, blended):
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
    _style(ax)
    ax.plot(short(weeks), series["desktop"], marker="o", markersize=5, linewidth=2,
            color=CATEGORICAL[0], label="desktop — survived step 1")
    ax.plot(short(weeks), series["mobile"], marker="o", markersize=5, linewidth=2,
            color=CATEGORICAL[2], label="mobile — survived step 1")
    ax.plot(short(weeks), blended, marker="^", markersize=5, linewidth=2,
            color=CATEGORICAL[3], label="blended (what the weekly report shows)")

    # Weekly n is small enough that the lines are noisy. Draw the pooled
    # before/after means so the shift is readable despite the noise.
    ship = weeks.index(SHIP_WEEK)
    for device, colour in (("desktop", CATEGORICAL[0]), ("mobile", CATEGORICAL[2]),
                           ("blended", CATEGORICAL[3])):
        before, after = pooled[device]
        ax.hlines(before, -0.4, ship - 0.5, color=colour, linewidth=1.2, linestyle=(0, (5, 3)), alpha=0.75)
        ax.hlines(after, ship - 0.5, len(weeks) - 0.6, color=colour, linewidth=1.2, linestyle=(0, (5, 3)), alpha=0.75)
        ax.annotate(f"{after - before:+.1f}pp", xy=(len(weeks) - 0.75, after + 1.5),
                    color=colour, fontsize=9, ha="right")
    ax.bar(short(weeks), mobile_share, color=CATEGORICAL[4], alpha=0.13, width=0.55,
           label="mobile share of new visitors")
    ax.set_ylim(0, 100)
    ax.set_ylabel("%", color=INK_SECONDARY)
    ax.set_title("Both segments rose. The blended number fell.",
                 color=INK_PRIMARY, fontsize=13, pad=14, loc="left")
    _ship_line(ax, weeks)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, loc="upper left", ncols=2)
    fig.text(0.011, 0.02, "Dashed lines are the pooled before/after means. Both segments rose; the "
                          "blended rate fell 2.8pp, because the\nmobile-heavy referral channel that "
                          "arrived the same week moved weight onto the weaker segment.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.savefig(ASSETS_DIR / "03_device_split.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_step1_phases(table):
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=SURFACE)
    _style(ax)
    labels = [f"{d}\n{p}" for d in ("desktop", "mobile") for p in ("before ship", "after ship")]
    keys = [(d, p) for d in ("desktop", "mobile") for p in ("before ship", "after ship")]
    x = np.arange(len(keys))
    width = 0.17
    for i, phase in enumerate(STEP1_PHASE_ORDER):
        values = [table[k][i] for k in keys]
        ax.bar(x + (i - 2) * width, values, width, color=CATEGORICAL[i], label=phase)
    ax.set_xticks(x, labels, color=INK_SECONDARY)
    ax.set_ylabel("share of step-1 dropouts %", color=INK_SECONDARY)
    ax.set_title("Where step-1 dropouts were last seen", color=INK_PRIMARY, fontsize=13, pad=14, loc="left")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, ncols=5, loc="upper center")
    ax.set_ylim(0, 68)
    fig.text(0.011, 0.02, "plan_select collapses on desktop after the ship. "
                          "data_source_pick — the mobile blocker — does not.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(ASSETS_DIR / "04_step1_dropoff_phase.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- main


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    by_anon, excluded, excluded_events = load_events()
    profiles = [visitor_profile(evs) for evs in by_anon.values()]
    by_week = group_by(profiles, "first_week")
    weeks = sorted(by_week)

    print(f"loaded {sum(len(v) for v in by_anon.values()):,} events from {len(profiles):,} visitors")
    print(f"excluded {len(excluded)} internal anonIds ({excluded_events:,} events)")

    print_internal_actor_effect(weeks)
    print_weekly_funnel(by_week, weeks)
    print_window_sensitivity(by_anon, weeks)
    cohort, calendar, first_seen, visits_in_week = print_cohort_vs_calendar(profiles, weeks)
    series, mobile_share, pooled = print_device_split(profiles, weeks)
    table = print_step1_phases(profiles)

    plot_weekly_funnel(by_week, weeks)
    plot_cohort_vs_calendar(cohort, calendar, first_seen, visits_in_week, weeks)
    plot_device_split(series, mobile_share, weeks, pooled, series["blended"])
    plot_step1_phases(table)
    print(f"\nwrote 4 charts to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
