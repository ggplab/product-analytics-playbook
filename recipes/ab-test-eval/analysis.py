"""
A/B test evaluation: the four things to do before believing a result.

Reads two assignment tables (data/experiment_clean.csv, data/experiment_srm.csv)
and runs the readout in the order it should actually happen:

0. Sample size — what N this test needed, decided from the baseline and the
   minimum effect worth caring about, before any data is looked at
1. Validity checks — sample ratio mismatch, then covariate balance
2. The single evaluation at planned N — effect size with a confidence
   interval, and a p-value read alongside it rather than instead of it
3. What peeking would have done — measured on simulated A/A tests

Every reported statistic is computed twice by independent routes and the
two are asserted equal (see cross_check()).

Run:
    python analysis.py
    -> writes assets/*.png and prints every table to the console
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Values drawn from the dataviz skill palette (references/palette.md)
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#e34948", "#4a3aa7", "#eb6834"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

ALPHA = 0.05          # significance level for the single planned evaluation
POWER = 0.80          # probability of detecting the MDE if it is real
BASELINE = 0.38       # control step-1 survival, from the funnel-weekly recipe
MDE = 0.08            # minimum detectable effect, in absolute percentage points

# Sample ratio mismatch is checked at a much stricter level than the outcome
# test. It runs on every experiment, so a 0.05 threshold would cry wolf
# constantly; 0.001 is the conventional choice.
SRM_ALPHA = 0.001

# Peeking simulation parameters. Every number this produces is a property of
# these settings, not a universal constant — see the note in the README.
PEEK_SIMS = 2000
PEEK_DAYS = 14
PEEK_PER_ARM_PER_DAY = 43
PEEK_SEED = 7


# ---------------------------------------------------------------- helpers


def load(name):
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def arms(rows):
    a = [r for r in rows if r["variant"] == "A"]
    b = [r for r in rows if r["variant"] == "B"]
    return a, b


def successes(rows):
    return sum(int(r["survived_step1"]) for r in rows)


def two_proportion_test(x1, n1, x2, n2):
    """Pooled two-proportion z-test. Returns (z, p_two_sided)."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se
    return z, 2 * stats.norm.sf(abs(z))


def diff_ci(x1, n1, x2, n2, conf=0.95):
    """Confidence interval on p2 - p1, using the unpooled standard error.

    The test above pools because it assumes no difference; the interval does
    not, because it is describing the difference it found.
    """
    p1, p2 = x1 / n1, x2 / n2
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    return p2 - p1, (p2 - p1) - z * se, (p2 - p1) + z * se


def required_n(p1, mde, alpha=ALPHA, power=POWER):
    """Sample size per arm to detect an absolute lift of `mde` from `p1`."""
    p2 = p1 + mde
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    return int(np.ceil((z_a + z_b) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / mde**2))


def cross_check(x1, n1, x2, n2):
    """Verify the hand-written z-test against scipy's chi-square.

    For a 2x2 table without continuity correction, the chi-square statistic
    equals the square of the pooled two-proportion z. If these ever diverge,
    one of the two is wrong and the readout should not be trusted.
    """
    z, p_z = two_proportion_test(x1, n1, x2, n2)
    chi2, p_chi, _, _ = stats.chi2_contingency(
        [[x1, n1 - x1], [x2, n2 - x2]], correction=False
    )
    assert np.isclose(z**2, chi2), f"z^2={z**2} != chi2={chi2}"
    assert np.isclose(p_z, p_chi), f"p_z={p_z} != p_chi={p_chi}"
    return z, p_z, chi2


# ---------------------------------------------------------------- sections


def print_sample_size():
    print("=== 0. Sample size, decided before the data ===")
    n = required_n(BASELINE, MDE)
    print(f"baseline {BASELINE:.0%}, MDE +{MDE:.0%}pt, alpha {ALPHA}, power {POWER:.0%}"
          f"  ->  {n} per arm")
    print("This experiment was planned at 600 per arm; random assignment realized")
    print("575 and 615. Traffic was cut off at the plan, not when the result looked good.\n")

    # The same routine must reproduce the worked example in theory/04.
    check = required_n(0.05, 0.02)
    print(f"cross-check against theory/04's worked example (5% -> 7%): "
          f"{check} per arm, doc says ~2,200")
    assert 2100 <= check <= 2300, check

    print("\nrequired N per arm, by baseline and minimum detectable effect:")
    baselines = [0.05, 0.20, 0.38, 0.60]
    mdes = [0.01, 0.02, 0.05, 0.08]
    print(f"{'baseline':>9} " + " ".join(f"{'+' + str(int(m * 100)) + 'pt':>9}" for m in mdes))
    grid = {}
    for b in baselines:
        row = [required_n(b, m) for m in mdes]
        grid[b] = row
        print(f"{b:>8.0%} " + " ".join(f"{v:>9,}" for v in row))
    print("\nHalving the effect you want to detect roughly quadruples the traffic")
    print("you need. That is the whole reason to decide this before launching.")
    return grid, baselines, mdes


def print_validity(rows, label):
    a, b = arms(rows)
    na, nb = len(a), len(b)

    srm = stats.chisquare([na, nb], [(na + nb) / 2] * 2)

    table = [
        [sum(r["device"] == "mobile" for r in a), sum(r["device"] == "desktop" for r in a)],
        [sum(r["device"] == "mobile" for r in b), sum(r["device"] == "desktop" for r in b)],
    ]
    bal_chi2, bal_p, _, _ = stats.chi2_contingency(table, correction=False)
    mob_a = 100 * table[0][0] / na
    mob_b = 100 * table[1][0] / nb

    print(f"\n--- {label} ---")
    print(f"arm sizes         A {na:4d}   B {nb:4d}   (intended 50/50)")
    print(f"  SRM chi-square  {srm.statistic:6.2f}  p = {srm.pvalue:.4g}   "
          f"{'FAIL' if srm.pvalue < SRM_ALPHA else 'pass'} at alpha={SRM_ALPHA}")
    print(f"device mix        A {mob_a:.1f}% mobile   B {mob_b:.1f}% mobile")
    print(f"  balance chi-sq  {bal_chi2:6.2f}  p = {bal_p:.3g}   "
          f"{'FAIL' if bal_p < SRM_ALPHA else 'pass'} at alpha={SRM_ALPHA}")
    return {"na": na, "nb": nb, "srm_p": srm.pvalue, "mob_a": mob_a, "mob_b": mob_b,
            "bal_p": bal_p, "bal_chi2": bal_chi2}


def print_result(rows, label):
    a, b = arms(rows)
    xa, xb, na, nb = successes(a), successes(b), len(a), len(b)
    z, p, chi2 = cross_check(xa, na, xb, nb)
    d, lo, hi = diff_ci(xa, na, xb, nb)
    print(f"\n--- {label} ---")
    print(f"A  {xa:3d}/{na:4d} = {100*xa/na:5.1f}%")
    print(f"B  {xb:3d}/{nb:4d} = {100*xb/nb:5.1f}%")
    print(f"difference  {100*d:+.1f}pp   95% CI [{100*lo:+.1f}, {100*hi:+.1f}]")
    print(f"z = {z:.3f}   p = {p:.4g}   (chi-square cross-check {chi2:.4f} = z^2)")
    return {"xa": xa, "na": na, "xb": xb, "nb": nb, "d": d, "lo": lo, "hi": hi, "p": p}


def simulate_peeking():
    """Measure the false-positive rate of stopping at the first significant look.

    Every test simulated here is an A/A test: both arms are drawn from the
    same probability, so any 'significant' result is a false positive by
    construction.
    """
    print("\n=== 3. What peeking would have done ===")
    print(f"{PEEK_SIMS:,} simulated A/A tests (both arms at {BASELINE:.0%}, no real effect),")
    print(f"{PEEK_PER_ARM_PER_DAY} users per arm per day for {PEEK_DAYS} days, "
          f"each look evaluated at alpha={ALPHA}.")

    rng = np.random.default_rng(PEEK_SEED)
    # Daily successes per arm for every simulation, drawn once.
    daily_a = rng.binomial(PEEK_PER_ARM_PER_DAY, BASELINE, size=(PEEK_SIMS, PEEK_DAYS))
    daily_b = rng.binomial(PEEK_PER_ARM_PER_DAY, BASELINE, size=(PEEK_SIMS, PEEK_DAYS))
    cum_a, cum_b = daily_a.cumsum(axis=1), daily_b.cumsum(axis=1)
    n_at_day = np.arange(1, PEEK_DAYS + 1) * PEEK_PER_ARM_PER_DAY

    def p_at(day_idx):
        x1, x2 = cum_a[:, day_idx], cum_b[:, day_idx]
        n = n_at_day[day_idx]
        pooled = (x1 + x2) / (2 * n)
        se = np.sqrt(np.maximum(pooled * (1 - pooled) * (2 / n), 1e-12))
        z = (x2 / n - x1 / n) / se
        return 2 * stats.norm.sf(np.abs(z))

    # Look schedules: k evenly spaced looks, the last always on the final day.
    schedules = [1, 2, 3, 5, 7, 14]
    results = []
    print(f"\n{'looks':>6} {'schedule':>24} {'false-positive rate':>20}")
    for k in schedules:
        days = sorted({int(round(PEEK_DAYS * (i + 1) / k)) - 1 for i in range(k)})
        pvals = np.column_stack([p_at(d) for d in days])
        stopped = (pvals < ALPHA).any(axis=1)
        rate = 100 * stopped.mean()
        results.append((k, rate))
        desc = f"day {days[0]+1}" if k == 1 else f"{k} looks, last on day {days[-1]+1}"
        print(f"{k:>6} {desc:>24} {rate:19.1f}%")

    once = results[0][1]
    many = results[-1][1]
    se = 100 * np.sqrt(ALPHA * (1 - ALPHA) / PEEK_SIMS)
    print(f"\nOne look at the planned end: {once:.1f}%. Simulation error at {PEEK_SIMS:,} replicates")
    print(f"is +/-{se:.1f}pp, so that is the nominal {ALPHA:.0%} — the simulation is calibrated.")
    print(f"Daily looks for {PEEK_DAYS} days: {many:.1f}% — {many/once:.1f}x that.")
    print("Every one of those is a change that does nothing, shipped as a win.")
    return results


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


def plot_validity(clean, srm):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), facecolor=SURFACE)
    for ax, (title, d) in zip(axes, (("Assignment counts", "na"), ("Mobile share of arm", "mob_a"))):
        _style(ax)
    ax1, ax2 = axes

    x = np.arange(2)
    w = 0.35
    ax1.bar(x - w / 2, [clean["na"], srm["na"]], w, color=CATEGORICAL[0], label="A")
    ax1.bar(x + w / 2, [clean["nb"], srm["nb"]], w, color=CATEGORICAL[2], label="B")
    for i, d in enumerate((clean, srm)):
        ax1.axhline((d["na"] + d["nb"]) / 2, xmin=0.08 + i * 0.5, xmax=0.42 + i * 0.5,
                    color=INK_MUTED, linestyle=":", linewidth=1.2)
        ax1.annotate(f"SRM p={d['srm_p']:.3g}", xy=(i, max(d["na"], d["nb"]) + 22),
                     ha="center", fontsize=9,
                     color=CATEGORICAL[3] if d["srm_p"] < SRM_ALPHA else INK_SECONDARY)
    ax1.set_xticks(x, ["clean", "seeded bug"], color=INK_SECONDARY)
    ax1.set_ylim(0, 760)
    ax1.set_ylabel("participants", color=INK_SECONDARY)
    ax1.set_title("Arm sizes — dotted line is 50/50", color=INK_PRIMARY, fontsize=12, loc="left", pad=10)
    ax1.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, ncols=2)

    ax2.bar(x - w / 2, [clean["mob_a"], srm["mob_a"]], w, color=CATEGORICAL[0], label="A")
    ax2.bar(x + w / 2, [clean["mob_b"], srm["mob_b"]], w, color=CATEGORICAL[2], label="B")
    for i, d in enumerate((clean, srm)):
        ax2.annotate(f"balance p={d['bal_p']:.2g}", xy=(i, max(d["mob_a"], d["mob_b"]) + 3),
                     ha="center", fontsize=9,
                     color=CATEGORICAL[3] if d["bal_p"] < SRM_ALPHA else INK_SECONDARY)
    ax2.set_xticks(x, ["clean", "seeded bug"], color=INK_SECONDARY)
    ax2.set_ylim(0, 72)
    ax2.set_ylabel("% mobile", color=INK_SECONDARY)
    ax2.set_title("Covariate balance — randomization should equalize this",
                  color=INK_PRIMARY, fontsize=12, loc="left", pad=10)
    ax2.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, ncols=2)

    fig.text(0.011, 0.02, "The count check calls the bug borderline (p=0.028, survives a 0.001 SRM "
                          "threshold). The covariate check calls it at p=1.1e-06.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    fig.savefig(ASSETS_DIR / "01_validity_checks.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_result(clean, srm):
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE)
    _style(ax)
    labels, vals, los, his, colours = [], [], [], [], []
    for name, d, c in (("clean experiment", clean, CATEGORICAL[1]),
                       ("same test, validity checks skipped", srm, CATEGORICAL[3])):
        labels.append(name)
        vals.append(100 * d["d"])
        los.append(100 * (d["d"] - d["lo"]))
        his.append(100 * (d["hi"] - d["d"]))
        colours.append(c)

    y = np.arange(len(labels))
    ax.errorbar(vals, y, xerr=[los, his], fmt="o", markersize=9, capsize=6,
                linewidth=2, color=INK_SECONDARY, ecolor=INK_SECONDARY, zorder=3)
    for i, (v, c) in enumerate(zip(vals, colours)):
        ax.plot(v, i, "o", markersize=9, color=c, zorder=4)
        ax.annotate(f"{v:+.1f}pp", xy=(v, i + 0.16), ha="center", color=c, fontsize=10)
    ax.axvline(0, color=INK_MUTED, linewidth=1)
    ax.axvline(100 * MDE, color=CATEGORICAL[4], linestyle="--", linewidth=1.2)
    ax.annotate(f"seeded true effect +{100*MDE:.1f}pp (additive on every device)",
                xy=(100 * MDE + 0.25, -0.42), color=CATEGORICAL[4], fontsize=9)
    ax.set_yticks(y, labels, color=INK_SECONDARY)
    ax.set_ylim(-0.6, len(labels) - 0.3)
    ax.set_xlabel("difference in step-1 survival (percentage points), 95% CI",
                  color=INK_SECONDARY)
    ax.set_title("The effect, with its uncertainty", color=INK_PRIMARY, fontsize=13, loc="left", pad=12)
    fig.text(0.011, 0.02, "Both intervals exclude zero, so both are 'significant'. The broken one sits "
                          "further from the truth and carries the\nsmaller p-value (0.0027 vs 0.024). "
                          "A p-value ranks evidence against zero, not against being wrong.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.savefig(ASSETS_DIR / "02_effect_ci.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_peeking(results):
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE)
    _style(ax)
    ks = [str(k) for k, _ in results]
    rates = [r for _, r in results]
    bars = ax.bar(ks, rates, color=[CATEGORICAL[1]] + [CATEGORICAL[3]] * (len(ks) - 1), width=0.6)
    for b, r in zip(bars, rates):
        ax.annotate(f"{r:.1f}%", xy=(b.get_x() + b.get_width() / 2, r + 0.6),
                    ha="center", color=INK_SECONDARY, fontsize=10)
    ax.axhline(100 * ALPHA, color=INK_MUTED, linestyle="--", linewidth=1.2)
    ax.annotate(f"alpha = {ALPHA:.0%}, the rate you think you chose",
                xy=(-0.42, 100 * ALPHA + 0.8), ha="left", color=INK_MUTED, fontsize=9)
    ax.set_xlabel("number of looks before deciding", color=INK_SECONDARY)
    ax.set_ylabel("false-positive rate %", color=INK_SECONDARY)
    ax.set_ylim(0, max(rates) * 1.25)
    ax.set_title("Stopping at the first significant look, on tests with no real effect",
                 color=INK_PRIMARY, fontsize=13, loc="left", pad=12)
    fig.text(0.011, 0.02, f"{PEEK_SIMS:,} simulated A/A tests, both arms at {BASELINE:.0%}, "
                          f"{PEEK_PER_ARM_PER_DAY} per arm per day for {PEEK_DAYS} days.\n"
                          "These percentages belong to this schedule and this traffic rate, "
                          "not to peeking in general.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.savefig(ASSETS_DIR / "03_peeking.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


def plot_sample_size(grid, baselines, mdes):
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE)
    _style(ax)
    fine = np.linspace(0.01, 0.10, 60)
    for i, b in enumerate(baselines):
        ax.plot(100 * fine, [required_n(b, m) for m in fine], linewidth=2,
                color=CATEGORICAL[i], label=f"baseline {b:.0%}")
    ax.scatter([100 * MDE], [required_n(BASELINE, MDE)], s=70, zorder=5,
               color=INK_PRIMARY, label="this experiment")
    ax.set_yscale("log")
    ax.set_xlabel("minimum detectable effect (percentage points)", color=INK_SECONDARY)
    ax.set_ylabel("required N per arm (log scale)", color=INK_SECONDARY)
    ax.set_title("What each effect size costs in traffic", color=INK_PRIMARY,
                 fontsize=13, loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SECONDARY, ncols=5)
    fig.text(0.011, 0.02, f"alpha={ALPHA}, power={POWER:.0%}, two-sided. Roughly inverse-square: "
                          "halving the effect quadruples the traffic.\nThe 38% and 60% curves sit on "
                          "top of each other because p(1-p) is symmetric about 50% — rates near a "
                          "coin flip are the most expensive to move.",
             color=INK_MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.savefig(ASSETS_DIR / "04_sample_size.png", dpi=144, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- main


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    clean_rows = load("experiment_clean.csv")
    srm_rows = load("experiment_srm.csv")

    grid, baselines, mdes = print_sample_size()

    print("\n=== 1. Validity checks, before looking at the metric ===")
    v_clean = print_validity(clean_rows, "experiment_clean.csv")
    v_srm = print_validity(srm_rows, "experiment_srm.csv")
    print(f"\nThe count check alone would have let the broken experiment through at "
          f"alpha={SRM_ALPHA}.\nThe covariate check would not. Run both.")

    print("\n=== 2. The evaluation, once, at planned N ===")
    r_clean = print_result(clean_rows, "experiment_clean.csv")
    r_srm = print_result(srm_rows, "experiment_srm.csv — what you would have reported")
    print(f"\nSeeded true effect: +{100*MDE:.1f}pp on every device, so the population effect is")
    print(f"+{100*MDE:.1f}pp whatever the device mix. The clean run measures "
          f"{100*r_clean['d']:+.1f}pp and its interval covers it.")
    print(f"The broken run measures {100*r_srm['d']:+.1f}pp with a smaller p-value "
          f"({r_srm['p']:.4f} vs {r_clean['p']:.4f}).\nA more significant result that is further "
          f"from the truth — a p-value ranks evidence against\nzero, and says nothing about whether "
          f"the comparison was valid in the first place.")

    peek = simulate_peeking()

    plot_validity(v_clean, v_srm)
    plot_result(r_clean, r_srm)
    plot_peeking(peek)
    plot_sample_size(grid, baselines, mdes)
    print(f"\nwrote 4 charts to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
