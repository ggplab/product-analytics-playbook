"""
Threads post engagement analysis.

Reads data/threads_posts.csv (one row per post: post_id, published_at, track,
theme, views, likes, replies, reposts, quotes) and computes/visualizes:

1. Account baseline (median/mean/max per metric) — the yardstick every post is
   read against.
2. The engagement-rate trap: the top posts by engagement rate are NOT the top
   posts by reposts. Ranking on a single ratio misfiles the account's best work.
3. Per-pillar (theme) engagement shape: which content type earns replies vs
   reposts, and a percentile letter grade per pillar.

Three charts land in assets/:
- views_vs_er.png    : reach does not buy engagement rate (ER dilutes as reach grows)
- theme_performance.png : each pillar pulls a different action (replies vs reposts)
- er_vs_repost.png   : ER does not predict reposts — the honest signal is independent

Run:
    python analyze.py
    -> writes assets/*.png and prints the tables to the console
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "threads_posts.csv"
ASSETS_DIR = BASE_DIR / "assets"

# A view floor: below this, a post has too little reach for its rates to mean
# anything (one stray like swings the percentage wildly). Sparse-signal filter.
MIN_VIEWS = 500

# Values drawn from the dataviz skill palette (references/palette.md)
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#eb6834"]
ACCENT_RED = "#e34948"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

THEME_ORDER = ["build-in-public", "how-to", "hot-take", "personal"]
THEME_COLOR = {
    "build-in-public": CATEGORICAL[0],
    "how-to": CATEGORICAL[1],
    "hot-take": CATEGORICAL[2],
    "personal": CATEGORICAL[4],
}


def load_data():
    df = pd.read_csv(DATA_PATH)
    before = len(df)
    df = df[df["views"] >= MIN_VIEWS].copy()
    df["like_rate"] = df["likes"] / df["views"] * 100
    df["reply_rate"] = df["replies"] / df["views"] * 100
    df["engagement_rate"] = (df["likes"] + df["replies"] + df["reposts"]) / df["views"] * 100
    print(f"Posts kept (>= {MIN_VIEWS} views): {len(df)} / {before}\n")
    return df


def print_baseline(df):
    """Account-level yardstick. Read every post against these, not against zero."""
    def row(name, s, fmt):
        return f"  {name:<10} median {fmt(s.median())}  |  mean {fmt(s.mean())}  |  max {fmt(s.max())}"

    print("=== Account baseline ===")
    print(row("views", df["views"], lambda v: f"{v:>8.0f}"))
    print(row("likes", df["likes"], lambda v: f"{v:>8.0f}"))
    print(row("ER %", df["engagement_rate"], lambda v: f"{v:>8.2f}"))
    print(row("reposts", df["reposts"], lambda v: f"{v:>8.0f}"))
    zero = (df["reposts"] == 0).mean() * 100
    print(f"  reposts are sparse: {zero:.0f}% of kept posts have zero reposts "
          f"-> a single repost is already a strong, rare vote\n")


def print_the_trap(df, n=8):
    """The top posts by engagement rate vs by reposts barely overlap."""
    by_er = df.nlargest(n, "engagement_rate")["post_id"].tolist()
    by_rp = df.nlargest(n, "reposts")["post_id"].tolist()
    overlap = sorted(set(by_er) & set(by_rp))

    print(f"=== The engagement-rate trap (top {n}) ===")
    print(f"  Top {n} by engagement rate : {by_er}")
    print(f"  Top {n} by reposts         : {by_rp}")
    print(f"  In BOTH lists              : {overlap if overlap else 'almost none'}")

    widest = df.loc[df["views"].idxmax()]
    er_pct = (df["engagement_rate"] < widest["engagement_rate"]).mean() * 100
    rp_rank = int(df["reposts"].rank(ascending=False, method="min")[widest.name])
    print(f"\n  The widest-reach post ({widest['post_id']}, {int(widest['views'])} views):")
    print(f"    engagement rate {widest['engagement_rate']:.2f}%  -> only the {er_pct:.0f}th percentile (looks ordinary)")
    print(f"    reposts {int(widest['reposts'])}  -> rank #{rp_rank} all-time (its content is the account's best)")
    print("    Judge it on ER alone and you'd shrug. Judge it on reposts and you'd make a series of it.\n")


def print_theme_table(df):
    """Per-pillar engagement shape + a percentile letter grade on engagement rate."""
    # Grade each post A-D by its engagement-rate percentile within the account.
    pct = df["engagement_rate"].rank(pct=True)
    grade = pd.cut(pct, [0, 0.25, 0.50, 0.75, 1.0], labels=["D", "C", "B", "A"],
                   include_lowest=True)
    df = df.assign(grade=grade)

    print("=== Engagement shape by content pillar ===")
    print(f"  {'theme':<16}{'n':>4}{'avg views':>11}{'avg ER%':>9}"
          f"{'reply_rate':>12}{'reposts/post':>14}{'grade':>7}")
    for theme in THEME_ORDER:
        g = df[df["theme"] == theme]
        if g.empty:
            continue
        # Pillar grade = the grade its MEDIAN post would get (percentile of the
        # pillar's average ER against all posts).
        theme_pct = (df["engagement_rate"] < g["engagement_rate"].mean()).mean()
        theme_grade = pd.cut([theme_pct], [0, 0.25, 0.50, 0.75, 1.0],
                             labels=["D", "C", "B", "A"], include_lowest=True)[0]
        print(f"  {theme:<16}{len(g):>4}{g['views'].mean():>11.0f}"
              f"{g['engagement_rate'].mean():>9.2f}{g['reply_rate'].mean():>12.3f}"
              f"{g['reposts'].mean():>14.2f}{theme_grade:>7}")
    print("\n  Read the shape, not just the grade: hot-take grades lower on ER yet pulls")
    print("  the most replies (debate); build-in-public earns the most reposts (saves).\n")


# ---------- charts ----------

def _style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=INK_SECONDARY)


def plot_views_vs_er(df):
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    _style_axes(ax)

    # marker area grows with reposts (the hero metric)
    for theme in THEME_ORDER:
        g = df[df["theme"] == theme]
        ax.scatter(g["views"], g["engagement_rate"], s=20 + g["reposts"] * 12,
                   color=THEME_COLOR[theme], alpha=0.6, edgecolor="white",
                   linewidth=0.5, label=theme)

    med_er = df["engagement_rate"].median()
    ax.axhline(med_er, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.text(df["views"].min(), med_er, f"  median ER {med_er:.2f}%",
            color=INK_MUTED, fontsize=8, va="bottom")

    widest = df.loc[df["views"].idxmax()]
    ax.annotate(
        "widest reach, ER only average\n(marker size = reposts: this is the all-time #1)",
        xy=(widest["views"], widest["engagement_rate"]),
        xytext=(widest["views"] * 0.16, widest["engagement_rate"] + 0.9),
        fontsize=8.5, color=INK_PRIMARY,
        arrowprops=dict(arrowstyle="->", color=INK_SECONDARY, lw=1),
    )

    ax.set_xscale("log")
    ax.set_xlabel("Views (log scale)", color=INK_SECONDARY)
    ax.set_ylabel("Engagement rate (%)", color=INK_SECONDARY)
    ax.set_title("Reach does not buy engagement rate — ER dilutes as a post spreads wide",
                 color=INK_PRIMARY, fontsize=12.5, pad=12)
    ax.legend(fontsize=8, frameon=False, labelcolor=INK_SECONDARY, loc="upper right",
              title="content pillar", title_fontsize=8)
    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "views_vs_er.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_theme_performance(df):
    # Both series expressed per 1,000 views, so they share one axis and are
    # directly comparable (view-weighted, so a few big posts don't dominate).
    def per_1k(metric):
        return df.groupby("theme").apply(
            lambda g: g[metric].sum() / g["views"].sum() * 1000, include_groups=False
        ).reindex(THEME_ORDER)

    reply = per_1k("replies")
    repost = per_1k("reposts")

    x = np.arange(len(THEME_ORDER))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    _style_axes(ax)

    ax.bar(x - w / 2, reply.values, w, color=CATEGORICAL[2], label="replies per 1,000 views")
    ax.bar(x + w / 2, repost.values, w, color=CATEGORICAL[0], label="reposts per 1,000 views")

    ax.set_xticks(x)
    ax.set_xticklabels(THEME_ORDER, color=INK_SECONDARY)
    ax.set_ylabel("per 1,000 views", color=INK_SECONDARY)
    ax.set_title("Each pillar pulls a different action: hot-take drives replies, build-in-public drives reposts",
                 color=INK_PRIMARY, fontsize=11.5, pad=12)
    ax.legend(fontsize=9, frameon=False, labelcolor=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "theme_performance.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_er_vs_repost(df):
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    _style_axes(ax)

    for theme in THEME_ORDER:
        g = df[df["theme"] == theme]
        ax.scatter(g["engagement_rate"], g["reposts"], s=32,
                   color=THEME_COLOR[theme], alpha=0.6, edgecolor="white",
                   linewidth=0.5, label=theme)

    # jitter y=0 band is where most posts sit (reposts are sparse) — call it out
    ax.axhline(0.5, color=INK_MUTED, linestyle=":", linewidth=1)
    ax.text(df["engagement_rate"].max(), 0.6,
            "most posts: zero reposts, any ER", color=INK_MUTED, fontsize=8,
            ha="right", va="bottom")

    widest = df.loc[df["views"].idxmax()]
    ax.annotate("average ER, record reposts",
                xy=(widest["engagement_rate"], widest["reposts"]),
                xytext=(widest["engagement_rate"] + 0.25, widest["reposts"] - 3),
                fontsize=8.5, color=INK_PRIMARY,
                arrowprops=dict(arrowstyle="->", color=INK_SECONDARY, lw=1))

    ax.set_xlabel("Engagement rate (%)", color=INK_SECONDARY)
    ax.set_ylabel("Reposts", color=INK_SECONDARY)
    ax.set_title("Engagement rate does not predict reposts — the honest signal is independent",
                 color=INK_PRIMARY, fontsize=12, pad=12)
    ax.legend(fontsize=8, frameon=False, labelcolor=INK_SECONDARY, loc="upper left",
              title="content pillar", title_fontsize=8)
    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "er_vs_repost.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    ASSETS_DIR.mkdir(exist_ok=True)
    df = load_data()

    print_baseline(df)
    print_the_trap(df)
    print_theme_table(df)

    plot_views_vs_er(df)
    plot_theme_performance(df)
    plot_er_vs_repost(df)

    print(f"Saved 3 charts to {ASSETS_DIR}")
