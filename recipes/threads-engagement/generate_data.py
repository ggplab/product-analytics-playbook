"""
Synthetic data generator for a Threads (or any social) engagement analysis.

Simulates the post history of a single content account: for each post it
draws a reach (views) from a heavy right-skewed distribution, then draws
likes / replies / reposts as per-view rates that depend on the post's
content pillar (theme). The result is written to one CSV, one row per post.

Design points (used as interpretation exercises in the README):
- Each theme has a different engagement "shape": build-in-public earns
  reposts (save value), hot-take earns replies (debate) but few likes,
  how-to earns reposts too, personal is wide-but-shallow.
- Reposts are a SPARSE signal on purpose (most posts get zero), mirroring
  real accounts where a repost is a strong, rare vote.
- One injected anomaly: a single build-in-public post gets an algorithmic
  blast (~15x reach) that DILUTES its engagement rate to merely average,
  even though its absolute likes and reposts are all-time highs. This is
  the headline lesson: engagement rate alone would mislabel the account's
  best post as mediocre.

Reproducibility: seeded with a numpy Generator (seed=42). Parameters are
exposed as constants at the top of the file, so changing them regenerates
data with different patterns.

Run:
    python generate_data.py
    -> writes data/threads_posts.csv
       (post_id, published_at, track, theme, views, likes, replies, reposts, quotes)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ========== Parameters ==========
SEED = 42
N_POSTS = 240

# Posting window
START_DATE = pd.Timestamp("2025-01-01")
END_DATE = pd.Timestamp("2025-04-30")

# Reach (views) is heavy-tailed: most posts land small, a few go wide.
# Drawn as lognormal(mu, sigma) so median = exp(mu) ~ 1,100 views and the
# tail reaches into the tens of thousands, matching a real small account.
VIEWS_LOG_MU = 7.0
VIEWS_LOG_SIGMA = 1.05

# Content pillars. "track" is the coarse professional/daily split; "theme"
# is the content pillar. Each theme carries a per-view engagement shape and
# a share of how often the account posts it.
#   like_rate  : likes per view
#   reply_rate : replies per view  (debate pull)
#   repost_rate: reposts per view  (save value — sparse)
#   quote_rate : quotes per view
THEMES = {
    "build-in-public": dict(
        track="professional", share=0.30,
        like_rate=0.0115, reply_rate=0.0016, repost_rate=0.00095, quote_rate=0.00035,
    ),
    "how-to": dict(
        track="professional", share=0.25,
        like_rate=0.0082, reply_rate=0.0012, repost_rate=0.00060, quote_rate=0.00025,
    ),
    "hot-take": dict(
        track="professional", share=0.20,
        like_rate=0.0070, reply_rate=0.0040, repost_rate=0.00024, quote_rate=0.00060,
    ),
    "personal": dict(
        track="daily", share=0.25,
        like_rate=0.0060, reply_rate=0.0009, repost_rate=0.00012, quote_rate=0.00010,
    ),
}

# Per-post multiplicative noise on each engagement stream (lognormal, so it
# is always positive and occasionally spikes) — keeps posts within a theme
# from looking identical.
ENGAGEMENT_NOISE_SIGMA = 0.35

# Injected anomaly: the account's single widest-reach post gets an algorithmic
# blast. Its reach multiplies 8x, but that extra audience is far less targeted,
# so its like/reply RATES fall below the account's niche peak — its engagement
# rate lands merely upper-middle, not a standout. Reposts, however, are set to
# an all-time high: wide reach + genuinely useful = the account's save record.
# The lesson: engagement rate would file this post as ordinary, while reposts
# reveal it as the best thing the account ever published.
ANOMALY_VIEWS_MULT = 8.0
ANOMALY_DILUTED_LIKE_RATE = 0.0095   # below the build-in-public niche peak (0.0115) -> ER dilutes
ANOMALY_DILUTED_REPLY_RATE = 0.0013
ANOMALY_DILUTED_QUOTE_RATE = 0.0004
ANOMALY_REPOST_MARGIN = 11           # reposts = (next-highest reposts) + this margin


def weighted_themes(rng, size):
    names = list(THEMES.keys())
    weights = np.array([THEMES[n]["share"] for n in names])
    weights = weights / weights.sum()
    return rng.choice(names, size=size, p=weights)


def draw_engagement(rng, views, rate):
    """Poisson draw of an engagement count at `rate` per view, with per-post
    lognormal noise on the rate."""
    noise = rng.lognormal(mean=0.0, sigma=ENGAGEMENT_NOISE_SIGMA)
    expected = views * rate * noise
    return int(rng.poisson(max(expected, 0.0)))


def generate():
    rng = np.random.default_rng(SEED)

    # Post timestamps spread uniformly across the window, then sorted.
    span_seconds = int((END_DATE - START_DATE).total_seconds())
    offsets = np.sort(rng.integers(0, span_seconds, size=N_POSTS))
    timestamps = [START_DATE + pd.Timedelta(seconds=int(o)) for o in offsets]

    themes = weighted_themes(rng, N_POSTS)
    views_all = rng.lognormal(mean=VIEWS_LOG_MU, sigma=VIEWS_LOG_SIGMA, size=N_POSTS)

    rows = []
    for i in range(N_POSTS):
        theme = themes[i]
        spec = THEMES[theme]
        views = int(views_all[i])

        likes = draw_engagement(rng, views, spec["like_rate"])
        replies = draw_engagement(rng, views, spec["reply_rate"])
        reposts = draw_engagement(rng, views, spec["repost_rate"])
        quotes = draw_engagement(rng, views, spec["quote_rate"])

        rows.append([
            f"p{i + 1:04d}",
            timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),
            spec["track"],
            theme,
            views,
            likes,
            replies,
            reposts,
            quotes,
        ])

    df = pd.DataFrame(
        rows,
        columns=["post_id", "published_at", "track", "theme",
                 "views", "likes", "replies", "reposts", "quotes"],
    )

    # Inject the anomaly: take the widest-reach build-in-public post and blast
    # its reach further, so it is unambiguously the account's single viral post.
    bip = df[df["theme"] == "build-in-public"]
    target_idx = bip["views"].idxmax()

    next_highest_reposts = int(df.drop(index=target_idx)["reposts"].max())
    blasted_views = int(df.loc[target_idx, "views"] * ANOMALY_VIEWS_MULT)
    df.loc[target_idx, "views"] = blasted_views
    df.loc[target_idx, "likes"] = int(blasted_views * ANOMALY_DILUTED_LIKE_RATE)
    df.loc[target_idx, "replies"] = int(blasted_views * ANOMALY_DILUTED_REPLY_RATE)
    df.loc[target_idx, "quotes"] = int(blasted_views * ANOMALY_DILUTED_QUOTE_RATE)
    df.loc[target_idx, "reposts"] = next_highest_reposts + ANOMALY_REPOST_MARGIN

    return df


def print_summary(df):
    er = (df["likes"] + df["replies"] + df["reposts"]) / df["views"] * 100
    print(f"Posts: {len(df)}")
    print(f"Window: {df['published_at'].min()} .. {df['published_at'].max()}")
    print("\nTheme distribution:")
    print(df["theme"].value_counts().to_string())
    print("\nViews  — median {:.0f} / mean {:.0f} / max {:.0f}".format(
        df["views"].median(), df["views"].mean(), df["views"].max()))
    print("Likes  — median {:.0f} / mean {:.1f} / max {:.0f}".format(
        df["likes"].median(), df["likes"].mean(), df["likes"].max()))
    print("ER%    — median {:.2f} / mean {:.2f} / max {:.2f}".format(
        er.median(), er.mean(), er.max()))
    zero_reposts = (df["reposts"] == 0).mean() * 100
    print("Reposts— max {:.0f} / share of posts with zero reposts: {:.0f}%".format(
        df["reposts"].max(), zero_reposts))


if __name__ == "__main__":
    df = generate()
    print_summary(df)

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "threads_posts.csv"
    df.to_csv(out_path, index=False)

    print(f"\nWritten: {out_path}")
    print(f"Size: {out_path.stat().st_size / 1024:.1f} KB")
