"""
Regenerates the two charts used in this case study from the AGGREGATE numbers
already published in the source telemetry report. No raw log rows, anonymous
IDs, or nicknames are read or referenced anywhere in this script -- every
number below is a count or a rate that appears in the case study's README.

Run:
    uv venv .venv && source .venv/bin/activate
    uv pip install -r requirements.txt
    python generate_charts.py
"""

import matplotlib.pyplot as plt

# --- palette (validated categorical/sequential slots, light-surface set) ---
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

SEQ_LIGHT = "#86b6ef"   # ordinal ramp, lightest step allowed on light surface
SEQ_MID = "#3987e5"
SEQ_DARK = "#1c5cab"

SEG_BOUNCE = "#2a78d6"  # categorical slot 1 (blue) -- "first-impression bounce"
SEG_CLIFF = "#e34948"   # categorical slot 6 (red)  -- "rules cliff"
SEG_NEUTRAL = "#c3c2b7"  # baseline gray -- sessions that don't define either segment

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


def chart_1_funnel():
    """Visits -> game starts -> completions, aggregate counts + stated conversion."""
    stages = ["Visits", "Game starts", "Completions"]
    counts = [312, 93, 22]
    colors = [SEQ_LIGHT, SEQ_MID, SEQ_DARK]
    # conversion labels as stated in the source telemetry report (not re-derived here)
    conversions = ["", "40% of visitors", "17% of started sessions\n(83% drop-off)"]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(stages, counts, color=colors, width=0.55, zorder=3)

    for bar, count, label in zip(bars, counts, conversions):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 8,
            f"{count}",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color=INK_PRIMARY,
        )
        if label:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 30,
                label,
                ha="center",
                va="bottom",
                fontsize=8.5,
                color=INK_SECONDARY,
            )

    ax.set_ylabel("Sessions (count)")
    ax.set_title(
        "Funnel: visits -> game starts -> completions\n(~38-hour closed-beta window, aos.ggplab.xyz)",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
    )
    ax.set_ylim(0, 370)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)

    fig.tight_layout()
    fig.savefig("assets/01_funnel.png", dpi=160)
    plt.close(fig)


def chart_2_churn_segments():
    """
    Session-length distribution of the 60 sessions that churned at turn 0-1,
    split into duration buckets. The bimodal shape is what separates the two
    churn segments: a same-second "bounce" cluster and a much smaller
    long-session "rules cliff" cluster, with a thin middle that belongs to
    neither story.
    """
    buckets = ["<30 sec\n(median 9s)", "30 sec - 2 min", "2 - 10 min", ">10 min"]
    counts = [40, 9, 2, 9]
    colors = [SEG_BOUNCE, SEG_NEUTRAL, SEG_NEUTRAL, SEG_CLIFF]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars = ax.bar(buckets, counts, color=colors, width=0.6, zorder=3)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"{count}",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color=INK_PRIMARY,
        )

    ax.annotate(
        "Segment: first-impression bounce\n(n=40, 67% of turn-0/1 churn)",
        xy=(0, 40),
        xytext=(0.15, 46),
        fontsize=8.5,
        color=SEG_BOUNCE,
        ha="left",
    )
    ax.annotate(
        "Segment: rules cliff\n(n=9, stuck >10 min then quit)",
        xy=(3, 9),
        xytext=(1.65, 24),
        fontsize=8.5,
        color=SEG_CLIFF,
        ha="left",
    )

    ax.set_ylabel("Churned sessions (count)")
    ax.set_title(
        "Churn segments, by time-on-page before quitting\n"
        "(sessions that never reached turn 2, n=60)",
        fontsize=12,
        color=INK_PRIMARY,
        pad=14,
    )
    ax.set_ylim(0, 52)
    ax.grid(axis="y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)

    fig.tight_layout()
    fig.savefig("assets/02_churn_segments.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    chart_1_funnel()
    chart_2_churn_segments()
    print("Wrote assets/01_funnel.png and assets/02_churn_segments.png")
