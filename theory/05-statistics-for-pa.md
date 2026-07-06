# Statistics for Product Analytics

Most of what gets called "data analysis" in a product context is either summarizing what already happened, or making a claim about what would happen again. Those are different skills that use different tools, and mixing them up is where a lot of shaky product decisions come from — "conversion was up 3% this week" and "the new flow causes a 3% lift" are not the same sentence, even though they're one clause apart. This doc covers the statistics that actually come up when analyzing product data: why your averages might be lying to you, how to test whether a difference is real, and how to read categorical data (funnels, plan tiers, churn) without a spreadsheet full of guesswork.

## Descriptive vs. inferential

**Descriptive statistics** summarize the data you actually have — averages, counts, charts. Almost every dashboard number is descriptive: "1,204 signups this week" is just a fact about the data in front of you, no uncertainty attached.

**Inferential statistics** use a sample to make a claim about something you *haven't* fully observed — usually "would this hold up if we saw more data / more users / a different time period." This is what you need the moment someone asks "is this difference real, or could it just be noise."

**When you'd actually use this**: default to descriptive for reporting ("what happened"), switch to inferential the moment the question becomes a decision ("should we ship this," "is variant B actually better"). Conflating the two is how a good week of numbers turns into a false narrative about a permanent improvement.

## Distributions in product data: why means mislead

Most product metrics that involve money or time — order value, session length, revenue per user — are **right-skewed**: a long tail of high-value outliers pulls the average up, while most users sit well below it.

A worked example: 99 users spend $10 in a month, one user spends $2,000. The mean spend is:

```
(99 × $10 + $2,000) / 100 = $29.90
```

Report "average revenue per user: $29.90" and you've described almost nobody — 99 of your 100 users spent a third of that. The **median** (the middle value once sorted) would show $10, which is what a typical user actually did. For skewed metrics, report both, or lean on the median as the headline number and use percentiles (p50/p90/p99) to describe the tail instead of folding it into one average.

| Metric | Watch for skew | Better summary |
|---|---|---|
| Revenue per user | Yes — few whales | Median + p90 |
| Session duration | Yes — a few very long sessions | Median |
| Feature adoption rate (%) | Rarely skewed | Mean is usually fine |
| Days to first action (count) | Yes — long tail of slow adopters | Median |

**When you'd actually use this**: any time you're about to report "average X," check the distribution's shape first (a histogram takes one line of code). If there's a long tail, lead with the median and put the mean in parentheses, not the other way around.

## The Central Limit Theorem, briefly

Here's the part that makes hypothesis testing on skewed product data legitimate at all: **regardless of the shape of the underlying data, the distribution of the sample *mean* approaches a normal (bell-curve) distribution as sample size grows.** Individual session durations can be as skewed as they like — the *average* session duration across, say, 1,000 sessions still behaves close to normally distributed.

This is why t-tests and z-tests (built on normality assumptions) still work on messy, skewed product data: they're not assuming your raw data is normal, they're relying on the CLT to make the sampling distribution of the average close enough to normal once your sample is reasonably large (a few dozen observations per group is usually enough in practice).

**When you'd actually use this**: this is the theoretical justification, not something you compute directly — but it's worth knowing so "our data isn't normally distributed" doesn't become a reason to avoid running a perfectly valid mean-comparison test on a decent-sized sample.

## Hypothesis testing essentials

The basic machinery, stripped to what you need to read an A/B test result (see [04-ab-testing.md](04-ab-testing.md) for the full applied version):

- **Null hypothesis (H₀)**: the boring default — "no difference between groups."
- **Alternative hypothesis (H₁)**: the thing you're actually hoping to show — "there is a difference."
- **Standard error (SE)**: how much a sample mean would wobble if you re-ran the sample — `SE = σ / √n`. Bigger samples → smaller SE → more precise estimates.
- **Confidence interval**: a range built around your estimate — roughly `estimate ± 2 × SE` for a 95% interval — meant to communicate "here's the range this could plausibly be," not just a single point estimate that hides how much it could be wobbling.
- **p-value**: the probability of seeing a difference this large (or larger) if H₀ were actually true. Small p → the observed difference would be a rare coincidence under "no real effect," which is evidence (not proof) against H₀.
- **Type I error (α)**: falsely rejecting H₀ when there's actually no effect — a false positive. Conventionally capped at 5%.
- **Type II error (β)**: failing to detect a real effect — a false negative. **Power** (1 − β) is your chance of catching a real effect if one exists; 80% power is the industry-standard target when planning sample size.

The interpretation traps for all of this (what p-values do and don't mean, why bigger samples make trivial effects "significant," why "not significant" isn't "no effect") are covered in depth in [04-ab-testing.md](04-ab-testing.md), since they matter most in the A/B-test context where they get misused.

**When you'd actually use this**: any time you're comparing a metric between two groups (test vs. control, plan A vs. plan B, this month vs. last month) and need to say whether the difference is likely real.

A quick reference for which test fits which comparison:

| You're comparing | Data type | Test |
|---|---|---|
| Two group means (e.g., avg session length, A vs. B) | Continuous | t-test |
| Two group proportions (e.g., conversion rate, A vs. B) | Binary / rate | Two-proportion z-test |
| Category counts across two variables (e.g., plan × churned) | Categorical | Chi-square |

## Chi-square: testing categorical product data

A lot of product questions aren't about a mean at all — they're about counts falling into categories: which plan a user is on, whether they churned, which onboarding path they took. For that, you want the **chi-square test**, not a t-test.

Say you're checking whether plan tier is related to churn. You lay out a contingency table of observed counts:

| | Churned | Retained | Total |
|---|---|---|---|
| Plan A | 80 | 220 | 300 |
| Plan B | 40 | 260 | 300 |
| **Total** | 120 | 480 | 600 |

The chi-square test compares these observed counts (O) against the counts you'd *expect* if plan and churn were unrelated (E) — expected counts come from the row/column totals assuming independence:

```
χ² = Σ (O - E)² / E
```

A large χ² (and correspondingly small p-value) means the plan-churn split is unlikely to be this uneven by chance — Plan A really does churn at a different rate than Plan B. In pandas/scipy this is `scipy.stats.chi2_contingency` on the table above; it hands back the statistic, p-value, and expected-count table in one call.

One caveat worth knowing before you trust the result: if any cell's *expected* count drops below 5 (common with a rare category, like a plan tier with only a handful of users), the chi-square approximation gets unreliable — use **Fisher's exact test** instead, which doesn't rely on the same large-sample approximation.

**When you'd actually use this**: any "does X relate to Y" question where both X and Y are categories — onboarding path vs. activation, acquisition channel vs. conversion, feature flag group vs. churned/retained. If you can lay the question out as a contingency table, this is the test.

## Observational vs. experimental data

This distinction is the throughline of both this doc and 04, so it's worth stating on its own: **observational data** is what you get by watching users do whatever they were already going to do (most of your event logs, most historical dashboards). **Experimental data** is what you get by assigning users to conditions yourself before you observe the outcome (an A/B test).

Only experimental data supports a clean causal claim — "this change *caused* that lift" — because random assignment is what neutralizes confounders. Observational data can show you *that* two things are correlated, and can be a genuinely useful source of hypotheses ("plan A users churn more — worth investigating why"), but it can't, on its own, tell you *why*.

**When you'd actually use this**: whenever you're about to write "X drives Y" in a report, check which kind of data you're standing on. If it's observational, soften the claim to "X is associated with Y" and treat 04's playbook for how to actually test causality as the next step, not "case closed."

## Related docs

- [04-ab-testing.md](04-ab-testing.md) — applies the hypothesis-testing and sample-size machinery above to running and reading an actual A/B test
- [Cohort Retention Analysis](../recipes/cohort-retention/) — a hands-on recipe where skewed distributions and observational-data caveats both show up in practice
