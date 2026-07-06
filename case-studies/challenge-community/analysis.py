"""
12-week creator-challenge community: submission-log analysis.

A 19-person cohort ran a 12-week content-creation challenge with Discord-bot
check-ins, logged to a public Google Sheet (one row per verified submission).
This script fetches that log, normalizes participant identity to anonymous
P01..P19 codes, applies a biweekly-cadence correction, and computes:

  1. weekly active participants (naive count vs. cadence-corrected count)
  2. completion / survival rate per week (naive vs. corrected)
  3. submissions-per-participant Pareto concentration (top-5 share)
  4. platform mix

Run:
    uv venv .venv && source .venv/bin/activate
    uv pip install -r requirements.txt
    python analysis.py              # tries the live sheet, falls back to --cached
    python analysis.py --cached     # skip the network call, read data/ only

ANONYMIZATION -- read before touching this file
------------------------------------------------
The source sheet logs a free-text Discord nickname per row, and several
participants used more than one nickname (a Discord handle in some rows, a
real name in others). Folding those aliases into one canonical identity
requires a nickname roster -- an EXTERNAL file (members.json, a sibling
project, read-only) that is never copied into this repo.

The map below (HASH_TO_PCODE) goes the *other* direction: it is keyed by a
one-way SHA-256 hash of the canonical identity string, not by the identity
itself, so this committed script never contains a real name, a Discord
nickname, or a table that reverses P-code -> identity. That satisfies this
repo's case-study rule ("never commit a mapping back to identities") while
still letting the live-fetch path re-derive the same anonymous codes anyone
regenerating this file would get.

Nobody needs any of this to reproduce the analysis: `--cached` (the default
whenever the live sheet or the external roster is unreachable, e.g. for
anyone who clones this repo without that sibling project) reads
data/submissions_anonymized.csv directly -- it already carries p_code, and
cadence is looked up from CADENCE_BY_PCODE (an anonymous code -> "weekly" /
"biweekly" flag, which identifies no one).
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date

import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ASSETS_DIR = os.path.join(HERE, "assets")
CACHED_CSV = os.path.join(DATA_DIR, "submissions_anonymized.csv")

SHEET_ID = "1CKyVexXErtbkAVm6I-30fh3tei6J4B9HtCjq0-fmvvU"
GVIZ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json"

# External, read-only, NOT part of this repo. Only consulted on the live-fetch
# path, to fold Discord nickname aliases into one canonical identity before
# hashing. If this path doesn't exist (true for anyone outside the original
# organizer's machine), the script falls back to --cached automatically.
EXTERNAL_ROSTER_PATH = os.path.expanduser(
    "~/Projects/content-designer-challenge/web/members.json"
)

CHALLENGE_START = date(2026, 3, 2)
TOTAL_WEEKS = 12
TOTAL_PARTICIPANTS = 19  # 19 people who submitted at least once; see README limitations

# The source sheet's "number" column is a free-text Korean week label, e.g.
# a string meaning "week 3, submission 2" or a separate string meaning
# "prep period". Written here as \uXXXX escapes (not literal characters) so
# this committed source file stays ASCII-only per this case study's
# no-Korean-text rule, while still matching the real values byte-for-byte
# at runtime (Python decodes \uXXXX to the same character at parse time).
PREP_PERIOD_LABEL = "\uc900\ube44\uae30\uac04"  # "prep period"
WEEK_LABEL_PATTERN = r"(\d+)\s*\uc8fc\ucc28"  # matches "<N> <week-marker>"

# hash(canonical identity, sha256, first 16 hex chars) -> anonymous code.
# One-way hash; see the ANONYMIZATION note above. Never edit this by hand --
# regenerate from the live-fetch path if the roster ever changes.
HASH_TO_PCODE = {
    "7257d901c7df2c38": "P01",
    "2a8998d9d303b6da": "P02",
    "6cfe4338ed4cd491": "P03",
    "8115c1d55dea77c5": "P04",
    "b7758fdf686dc3cc": "P05",
    "bd46c45c66fdbacc": "P06",
    "4f974e21aba3f70b": "P07",
    "ded48e0ebe1a6fe0": "P08",
    "8b4f9b32e9074e37": "P09",
    "cb60864b9d3f5437": "P10",
    "fe5bb6770cb724e1": "P11",
    "911eae60e8ebe387": "P12",
    "282255649d3a2c41": "P13",
    "d635a811df1421b6": "P14",
    "c860b3492adabd9e": "P15",
    "52cac59f121a35f9": "P16",
    "af4aa01f3f6a3db3": "P17",
    "9f6fefd6df5d72dd": "P18",
    "9d83d9a33c349f31": "P19",
}

# anonymous code -> submission cadence. Does not identify anyone; needed for
# the biweekly-cadence correction in both the live and --cached paths.
CADENCE_BY_PCODE = {
    "P01": "biweekly",
    "P02": "biweekly",
    "P03": "biweekly",
    "P04": "weekly",
    "P05": "biweekly",
    "P06": "weekly",
    "P07": "weekly",
    "P08": "biweekly",
    "P09": "weekly",
    "P10": "biweekly",
    "P11": "weekly",
    "P12": "biweekly",
    "P13": "biweekly",
    "P14": "weekly",
    "P15": "weekly",
    "P16": "biweekly",
    "P17": "weekly",
    "P18": "weekly",
    "P19": "weekly",
}


def identity_hash(name: str) -> str:
    return hashlib.sha256(name.strip().encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------


def parse_gviz_date(value):
    """'Date(2026,1,19)' (0-indexed month) -> 'YYYY-MM-DD'."""
    if not (isinstance(value, str) and value.startswith("Date(")):
        return None
    y, m, d = value.replace("Date(", "").replace(")", "").split(",")[:3]
    return f"{int(y):04d}-{int(m) + 1:02d}-{int(d):02d}"


def fetch_live_rows():
    """
    Fetch the public gviz sheet + the external nickname roster, normalize
    identity to P-codes, and return the same row shape as load_cached_rows().
    Raises on any failure (network, missing roster, unrecognized identity) --
    callers should catch and fall back to --cached.
    """
    with urllib.request.urlopen(GVIZ_URL, timeout=15) as resp:
        text = resp.read().decode("utf-8")
    payload = json.loads(text[text.index("{") : text.rindex("}") + 1])
    sheet_rows = payload["table"]["rows"]

    with open(EXTERNAL_ROSTER_PATH, encoding="utf-8") as f:
        roster = json.load(f)
    nickname_map = roster["nickname_map"]

    def canonicalize(raw_user):
        raw = (raw_user or "").strip()
        return nickname_map.get(raw, raw)

    rows = []
    for r in sheet_rows:
        c = r["c"]

        def val(i):
            return c[i]["v"] if i < len(c) and c[i] else None

        def fmt(i):
            return c[i]["f"] if i < len(c) and c[i] else None

        raw_user = val(1)
        platform = val(2)
        number = val(4) or ""
        etc = val(6)

        canon = canonicalize(raw_user)
        h = identity_hash(canon)
        if h not in HASH_TO_PCODE:
            raise ValueError(
                f"Unrecognized identity hash for a canonicalized user -- "
                f"the roster has someone not in the original 19-person cohort. "
                f"Regenerate HASH_TO_PCODE / CADENCE_BY_PCODE before proceeding."
            )
        p_code = HASH_TO_PCODE[h]

        is_prep = PREP_PERIOD_LABEL in number
        m = re.search(WEEK_LABEL_PATTERN, number)
        week = int(m.group(1)) if m else None
        week_index = 0 if is_prep else week

        rows.append(
            {
                "p_code": p_code,
                "date": fmt(0),
                "week_index": week_index,
                "platform": platform,
                "visibility": "private" if etc == "private" else "public",
            }
        )

    rows.sort(key=lambda row: (row["date"], row["p_code"]))
    return rows


def load_cached_rows():
    with open(CACHED_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["week_index"] = int(row["week_index"])
            rows.append(row)
    return rows


def write_cached_csv(rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["p_code", "date", "week_index", "platform", "visibility"]
        )
        writer.writeheader()
        writer.writerows(rows)


def load_rows(use_cached: bool):
    if use_cached:
        print("[data] --cached requested: reading data/submissions_anonymized.csv")
        return load_cached_rows()
    try:
        rows = fetch_live_rows()
        print(f"[data] live fetch OK: {len(rows)} rows from the public sheet")
        write_cached_csv(rows)
        print("[data] refreshed data/submissions_anonymized.csv")
        return rows
    except Exception as exc:  # network error, missing roster, sheet schema change
        print(f"[data] live fetch failed ({exc!r}); falling back to --cached")
        return load_cached_rows()


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def pair_weeks(week: int):
    """Weeks (1,2), (3,4), ... (11,12) -- the biweekly cadence's 2-week unit."""
    k = (week + 1) // 2
    return (2 * k - 1, 2 * k)


def compute_metrics(rows):
    in_challenge = [r for r in rows if r["week_index"] and 1 <= r["week_index"] <= 12]

    week_participants = defaultdict(set)
    for r in in_challenge:
        week_participants[r["week_index"]].add(r["p_code"])

    naive_active, corrected_active = {}, {}
    for w in range(1, TOTAL_WEEKS + 1):
        naive_active[w] = len(week_participants[w])

        active = set()
        for p_code, cadence in CADENCE_BY_PCODE.items():
            if p_code in week_participants[w]:
                active.add(p_code)
            elif cadence == "biweekly":
                w1, w2 = pair_weeks(w)
                if p_code in week_participants.get(w1, set()) or p_code in week_participants.get(
                    w2, set()
                ):
                    active.add(p_code)
        corrected_active[w] = len(active)

    survival_naive = {w: naive_active[w] / TOTAL_PARTICIPANTS for w in naive_active}
    survival_corrected = {
        w: corrected_active[w] / TOTAL_PARTICIPANTS for w in corrected_active
    }

    counts = Counter(r["p_code"] for r in in_challenge)
    total_submissions = sum(counts.values())
    ranked = counts.most_common()
    top5_total = sum(c for _, c in ranked[:5])
    top5_share = top5_total / total_submissions

    platform_counts = Counter(r["platform"] for r in in_challenge)

    return {
        "in_challenge_rows": len(in_challenge),
        "total_rows": len(rows),
        "naive_active": naive_active,
        "corrected_active": corrected_active,
        "survival_naive": survival_naive,
        "survival_corrected": survival_corrected,
        "submission_counts": dict(ranked),
        "total_submissions": total_submissions,
        "top5_share": top5_share,
        "platform_counts": platform_counts,
    }


# --------------------------------------------------------------------------
# Charts -- same validated palette as case-studies/board-game-webapp
# --------------------------------------------------------------------------

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

SEQ_LIGHT = "#86b6ef"
SEQ_MID = "#3987e5"
SEQ_DARK = "#1c5cab"

ACCENT_WARN = "#e34948"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "text.color": INK_PRIMARY,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": INK_SECONDARY,
        "xtick.color": INK_SECONDARY,
        "ytick.color": INK_SECONDARY,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    }
)


def _strip_spines(ax):
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)


def chart_weekly_active(metrics):
    weeks = list(range(1, TOTAL_WEEKS + 1))
    naive = [metrics["naive_active"][w] for w in weeks]
    corrected = [metrics["corrected_active"][w] for w in weeks]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.plot(
        weeks,
        naive,
        marker="o",
        color=ACCENT_WARN,
        linewidth=1.8,
        label="Naive weekly count (this week only)",
        zorder=3,
    )
    ax.plot(
        weeks,
        corrected,
        marker="o",
        color=SEQ_DARK,
        linewidth=2.4,
        label="Cadence-corrected (credits biweekly submitters on their\noff week if they posted in the paired week)",
        zorder=4,
    )
    ax.fill_between(weeks, naive, corrected, color=SEQ_LIGHT, alpha=0.25, zorder=1)

    ax.set_xlabel("Challenge week")
    ax.set_ylabel("Active participants (of 19)")
    ax.set_xticks(weeks)
    ax.set_ylim(0, TOTAL_PARTICIPANTS + 1)
    ax.set_title(
        "Weekly active participants: naive count vs. biweekly-cadence correction\n"
        "(12-week creator challenge, N=19)",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
    )
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    _strip_spines(ax)

    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "01_weekly_active.png"), dpi=160)
    plt.close(fig)


def chart_pareto(metrics):
    ranked = sorted(metrics["submission_counts"].items(), key=lambda kv: -kv[1])
    codes = [c for c, _ in ranked]
    counts = [n for _, n in ranked]
    cum_pct = []
    running = 0
    for n in counts:
        running += n
        cum_pct.append(100 * running / metrics["total_submissions"])

    colors = [SEQ_DARK if i < 5 else SEQ_LIGHT for i in range(len(codes))]

    fig, ax1 = plt.subplots(figsize=(9.5, 5.2))
    ax1.bar(codes, counts, color=colors, width=0.65, zorder=3)
    ax1.set_ylabel("Submissions (count)")
    ax1.set_xlabel("Participant (ranked by volume, anonymized)")
    ax1.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax1.set_axisbelow(True)
    _strip_spines(ax1)
    plt.setp(ax1.get_xticklabels(), rotation=0, fontsize=8)

    ax2 = ax1.twinx()
    ax2.plot(codes, cum_pct, color=ACCENT_WARN, marker="o", markersize=3, linewidth=1.6, zorder=4)
    ax2.axhline(metrics["top5_share"] * 100, color=ACCENT_WARN, linestyle="--", linewidth=1, alpha=0.6)
    ax2.set_ylabel("Cumulative share of all submissions (%)", color=ACCENT_WARN)
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", colors=ACCENT_WARN)
    ax2.spines["top"].set_visible(False)

    ax1.set_title(
        f"Submissions-per-participant Pareto (N=19, {metrics['total_submissions']} in-challenge submissions)\n"
        f"Top 5 participants = {metrics['top5_share'] * 100:.1f}% of all submissions",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
    )

    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "02_pareto.png"), dpi=160)
    plt.close(fig)


def chart_platform_mix(metrics):
    ranked = metrics["platform_counts"].most_common()
    platforms = [p for p, _ in ranked]
    counts = [n for _, n in ranked]
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(platforms, counts, color=SEQ_MID, zorder=3)
    ax.invert_yaxis()

    for bar, count in zip(bars, counts):
        pct = 100 * count / total
        ax.text(
            bar.get_width() + total * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{count} ({pct:.1f}%)",
            va="center",
            fontsize=9,
            color=INK_PRIMARY,
        )

    ax.set_xlabel("Submissions (count)")
    ax.set_title(
        "Platform mix, in-challenge submissions (weeks 1-12, n={})".format(total),
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
    )
    ax.set_xlim(0, max(counts) * 1.25)
    ax.grid(axis="x", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    _strip_spines(ax)

    fig.tight_layout()
    fig.savefig(os.path.join(ASSETS_DIR, "03_platform_mix.png"), dpi=160)
    plt.close(fig)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def print_report(metrics):
    print("\n=== Weekly active participants (naive vs. cadence-corrected) ===")
    print("week | naive | corrected")
    for w in range(1, TOTAL_WEEKS + 1):
        print(f"{w:>4} | {metrics['naive_active'][w]:>5} | {metrics['corrected_active'][w]:>9}")

    print("\n=== Survival / completion rate (share of 19 participants active) ===")
    print("week | naive   | corrected")
    for w in range(1, TOTAL_WEEKS + 1):
        n = metrics["survival_naive"][w] * 100
        c = metrics["survival_corrected"][w] * 100
        print(f"{w:>4} | {n:>5.1f}% | {c:>7.1f}%")

    print(
        f"\nWeek 1 naive vs. corrected: {metrics['naive_active'][1]}/19 "
        f"({metrics['survival_naive'][1] * 100:.1f}%) vs. "
        f"{metrics['corrected_active'][1]}/19 ({metrics['survival_corrected'][1] * 100:.1f}%)"
    )
    print(
        f"Week 12 survival (naive == corrected here): "
        f"{metrics['naive_active'][12]}/19 ({metrics['survival_naive'][12] * 100:.1f}%)"
    )

    print(f"\n=== Pareto concentration (in-challenge submissions, n={metrics['total_submissions']}) ===")
    ranked = sorted(metrics["submission_counts"].items(), key=lambda kv: -kv[1])
    for code, n in ranked:
        print(f"  {code}: {n}")
    print(f"Top 5 share: {metrics['top5_share'] * 100:.1f}%")

    print("\n=== Platform mix (in-challenge submissions) ===")
    total = sum(metrics["platform_counts"].values())
    for platform, n in metrics["platform_counts"].most_common():
        print(f"  {platform}: {n} ({100 * n / total:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Skip the live fetch; read data/submissions_anonymized.csv directly.",
    )
    args = parser.parse_args()

    os.makedirs(ASSETS_DIR, exist_ok=True)

    rows = load_rows(use_cached=args.cached)
    metrics = compute_metrics(rows)

    chart_weekly_active(metrics)
    chart_pareto(metrics)
    chart_platform_mix(metrics)
    print("\n[charts] wrote assets/01_weekly_active.png, 02_pareto.png, 03_platform_mix.png")

    print_report(metrics)


if __name__ == "__main__":
    main()
