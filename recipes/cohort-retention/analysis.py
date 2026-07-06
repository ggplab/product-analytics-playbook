"""
SaaS monthly cohort retention analysis.

Reads data/cohort_activity.csv (long format: user_id, signup_month, plan,
channel, activity_month) and computes/visualizes:

1. A cohort (signup month) x month-offset retention matrix + heatmap
2. Per-cohort retention curves (with the anomalous cohort highlighted)
3. Per-channel retention curves (to surface the long-term churn pattern)

Run:
    python analysis.py
    -> writes assets/*.png and prints the retention matrix to the console
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "cohort_activity.csv"
ASSETS_DIR = BASE_DIR / "assets"

# Values drawn from the dataviz skill palette (references/palette.md)
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#eb6834"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"


def load_data():
    df = pd.read_csv(DATA_PATH)
    df["signup_month"] = pd.PeriodIndex(df["signup_month"], freq="M")
    df["activity_month"] = pd.PeriodIndex(df["activity_month"], freq="M")
    df["month_offset"] = (
        (df["activity_month"].astype("int64") - df["signup_month"].astype("int64"))
    )
    return df


def cohort_size(df):
    return df.drop_duplicates("user_id").groupby("signup_month")["user_id"].count()


def build_retention_matrix(df):
    """signup_month x month_offset retention rate (%) matrix. Unobserved cells are NaN."""
    sizes = cohort_size(df)
    active = (
        df.drop_duplicates(["user_id", "month_offset"])
        .groupby(["signup_month", "month_offset"])["user_id"]
        .count()
        .unstack("month_offset")
    )
    retention = active.divide(sizes, axis=0) * 100

    # Explicitly set future offsets not yet reached to NaN (not missing data —
    # simply "hasn't happened yet")
    max_offset = df["month_offset"].max()
    obs_end = df["activity_month"].max()
    for cohort in retention.index:
        max_valid_offset = (obs_end.year - cohort.year) * 12 + (obs_end.month - cohort.month)
        for offset in range(max_valid_offset + 1, max_offset + 1):
            if offset in retention.columns:
                retention.loc[cohort, offset] = np.nan

    return retention.sort_index(axis=1)


def plot_heatmap(retention):
    fig, ax = plt.subplots(figsize=(11, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQUENTIAL_BLUE)
    cmap.set_bad(color="#f2f1ed")

    masked = np.ma.masked_invalid(retention.values)
    im = ax.imshow(masked, cmap=cmap, vmin=0, vmax=100, aspect="auto")

    ax.set_xticks(range(len(retention.columns)))
    ax.set_xticklabels(retention.columns, color=INK_SECONDARY, fontsize=9)
    ax.set_yticks(range(len(retention.index)))
    ax.set_yticklabels([str(m) for m in retention.index], color=INK_SECONDARY, fontsize=9)
    ax.set_xlabel("Months since signup (month offset)", color=INK_SECONDARY)
    ax.set_ylabel("Signup month cohort", color=INK_SECONDARY)
    ax.set_title("Monthly Cohort Retention Heatmap (%)", color=INK_PRIMARY, fontsize=13, pad=12)

    for spine in ax.spines.values():
        spine.set_visible(False)

    for i in range(retention.shape[0]):
        for j in range(retention.shape[1]):
            val = retention.values[i, j]
            if not np.isnan(val):
                text_color = INK_PRIMARY if val > 55 else INK_SECONDARY
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        fontsize=7.5, color=text_color if val < 65 else "#ffffff")

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.ax.tick_params(labelsize=8, colors=INK_SECONDARY)
    cbar.outline.set_visible(False)

    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "retention_heatmap.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_cohort_curves(retention, anomaly_cohort="2024-05"):
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    for idx, (cohort, row) in enumerate(retention.iterrows()):
        is_anomaly = str(cohort) == anomaly_cohort
        color = "#e34948" if is_anomaly else CATEGORICAL[idx % len(CATEGORICAL)]
        alpha = 1.0 if is_anomaly else 0.55
        lw = 2.6 if is_anomaly else 1.6
        label = f"{cohort} (anomalous cohort)" if is_anomaly else str(cohort)
        ax.plot(row.index, row.values, color=color, alpha=alpha, linewidth=lw,
                 marker="o", markersize=3, label=label)

    ax.set_xlabel("Months since signup (month offset)", color=INK_SECONDARY)
    ax.set_ylabel("Retention rate (%)", color=INK_SECONDARY)
    ax.set_title("Retention Curves by Cohort", color=INK_PRIMARY, fontsize=13, pad=12)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=INK_SECONDARY)
    ax.legend(fontsize=8, frameon=False, labelcolor=INK_SECONDARY, loc="upper right")

    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "cohort_curves.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def plot_channel_retention(df):
    sizes = df.drop_duplicates("user_id").groupby("channel")["user_id"].count()
    active = (
        df.drop_duplicates(["user_id", "month_offset"])
        .groupby(["channel", "month_offset"])["user_id"]
        .count()
        .unstack("month_offset")
    )
    retention = active.divide(sizes, axis=0) * 100
    retention = retention[[c for c in retention.columns if c <= 9]]  # keep only the window with enough sample size

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    for idx, (channel, row) in enumerate(retention.iterrows()):
        is_paid = channel == "paid_search"
        color = "#e34948" if is_paid else CATEGORICAL[idx % len(CATEGORICAL)]
        lw = 2.6 if is_paid else 1.8
        label = f"{channel} (long-term churn accelerates)" if is_paid else channel
        ax.plot(row.index, row.values, color=color, linewidth=lw,
                 marker="o", markersize=4, label=label)

    ax.axvline(6, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.text(6.1, ax.get_ylim()[1] * 0.95, "6 months", color=INK_MUTED, fontsize=8)

    ax.set_xlabel("Months since signup (month offset)", color=INK_SECONDARY)
    ax.set_ylabel("Retention rate (%)", color=INK_SECONDARY)
    ax.set_title("Retention Curves by Channel", color=INK_PRIMARY, fontsize=13, pad=12)
    ax.grid(True, color=GRIDLINE, linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=INK_SECONDARY)
    ax.legend(fontsize=9, frameon=False, labelcolor=INK_SECONDARY)

    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "channel_retention.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    ASSETS_DIR.mkdir(exist_ok=True)
    df = load_data()

    retention = build_retention_matrix(df)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print("=== Cohort Retention Matrix (%) ===")
    print(retention.round(1))

    plot_heatmap(retention)
    plot_cohort_curves(retention)
    plot_channel_retention(df)

    print(f"\nSaved 3 charts to {ASSETS_DIR}")
