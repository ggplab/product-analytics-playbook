# Cohort & Retention Analysis

"How many users are active today?" is a snapshot. Snapshots lie — they blend users who signed up yesterday with users who signed up a year ago, and average away the exact thing you need to see: whether people stick around *after* they join. Cohort analysis fixes this by grouping users by when they started, then tracking each group forward through time separately.

This doc covers what a cohort is, how to build a retention matrix, how to read the resulting curves, and the pitfalls that make cohort analysis easy to get subtly wrong. For a runnable, numbers-included version of everything here, see `../recipes/cohort-retention/` (pandas + SQL, same data, cross-verified results). For real analyses built on this pattern, see `../case-studies/`.

## What a cohort is

A cohort is a group of users who share a starting event, almost always "signed up in the same period" (day/week/month). Once defined, a cohort's membership never changes — the 2026-01 cohort is fixed at everyone who signed up in January 2026, forever. What changes over time is how many of them are still active.

You can cohort by other shared starting events too — first purchase date, plan tier at signup, acquisition channel — but time-based signup cohorts are the default because they let you compare "the same age" across groups (see [Retention curve shapes](#retention-curve-shapes) below).

**When you'd actually use this**: any time someone asks "is retention getting better or worse" — that question is meaningless without cohorts, because "retention" measured as a single blended number moves for reasons that have nothing to do with product changes (see next section).

## Why snapshots lie and cohorts don't

Say you look at "% of all-time users active this week" every Monday and it's been declining for three months. Two very different stories produce that same declining line:

1. **Product is getting worse.** Every cohort's retention curve is shifting down — new users churn faster than old users did at the same age.
2. **Growth is accelerating.** Retention per cohort is stable or improving, but you're adding so many new (not-yet-retained) users that they dilute the blended average — new signups always look "less retained" than day-100 users, simply because they haven't had time to prove otherwise.

A blended snapshot cannot distinguish these. A cohort table can, because it lines every group up by *age since signup*, not by calendar date — so you're always comparing like with like.

| | Week 0 | Week 1 | Week 2 | Week 3 |
|---|---|---|---|---|
| Cohort A (500 users) | 100% | 45% | 38% | 35% |
| Cohort B (500 users) | 100% | 48% | 40% | 37% |
| Cohort C (500 users) | 100% | 44% | 37% | — |

Cohorts A, B, and C all decay at roughly the same rate at the same age. That's a stable product. If the blended weekly-active number were falling while this table looks like this, the cause is dilution from growth, not a regression — a very different (and much less alarming) conclusion.

## Building a retention matrix

The retention matrix is a cohort × time-since-signup grid. Construction, conceptually:

1. **Assign each user to a cohort** — usually their signup week or month.
2. **Compute cohort size** — the denominator, fixed at time of cohort formation.
3. **For each cohort, count active users at each offset** (week 0, week 1, week 2, ...) — the numerator.
4. **Divide** — numerator ÷ denominator × 100, per cell.
5. **Leave future cells empty**, not zero — a cohort that signed up 2 weeks ago has no "week 5" data yet. Filling it with 0 makes recent cohorts look like they've churned when they simply haven't reached that age.

```sql
-- retention matrix, month-granularity cohorts
with cohort_size as (
  select signup_month, count(distinct user_id) as n
  from users
  group by signup_month
),
active as (
  select
    u.signup_month,
    (strftime('%Y', a.activity_month) - strftime('%Y', u.signup_month)) * 12
      + (strftime('%m', a.activity_month) - strftime('%m', u.signup_month)) as month_offset,
    count(distinct a.user_id) as active_users
  from activity a
  join users u using (user_id)
  group by u.signup_month, month_offset
)
select active.signup_month, month_offset,
       round(100.0 * active_users / cohort_size.n, 1) as retention_pct
from active join cohort_size using (signup_month)
order by 1, 2;
```

```python
# equivalent in pandas — see ../recipes/cohort-retention/analysis.py for the full version
cohort_size = df.groupby("signup_month")["user_id"].nunique()
active = df.groupby(["signup_month", "month_offset"])["user_id"].nunique().unstack()
retention_matrix = active.div(cohort_size, axis=0) * 100
```

**When you'd actually use this**: any time you want to know whether a specific change (onboarding redesign, pricing change, new acquisition channel) helped or hurt — compare the retention curve of cohorts before vs. after the change, at the same offsets.

### Choosing cohort granularity

Cohorts can be bucketed by day, week, or month of signup. The choice trades off resolution against noise:

| Granularity | Good for | Watch out for |
|---|---|---|
| Daily | High-volume products (thousands of signups/day) where you need to catch a bad deploy within hours | Very noisy for low-volume products — a cohort of 8 users produces a jagged, meaningless curve |
| Weekly | Most indie/early-stage products — enough users per cohort to smooth noise, still granular enough to catch a bad week | Blends together changes shipped mid-week |
| Monthly | Low-volume products, or long-cycle B2B products where the meaningful unit of usage is a month | Too coarse to catch anything that regressed and recovered inside a month |

A rough rule of thumb: pick the coarsest granularity where a typical cohort still has at least 50–100 users. Below that, percentage swings are mostly sampling noise, not signal — going finer just to "see more detail" often means looking at noise more closely, not seeing more truth.

## Retention curve shapes

Plot each cohort's row as a line (x = weeks/months since signup, y = % retained) and you get a retention curve. The shape matters more than any single number:

- **Decaying to zero** — the curve keeps dropping and never levels off. Users are leaving faster than they're replaced by habit; the product hasn't found a stable core user base yet.
- **Flattening (an "elbow")** — the curve drops sharply at first, then bends and stays roughly flat. The users who remain past the elbow have found lasting value and mostly stick around. This flattening is one of the most-cited quantitative signals of product-market fit: it means there's a durable core, even if it's smaller than total signups suggest.
- **Flat near 100%** — extremely rare, usually a sign you're measuring something with no real churn (e.g., a free tool with no concept of "leaving").

```
% retained
100 |●
    | ●
 60 |  ●
    |   ●___
 40 |       ●───●───●───●───●   <- flattening = durable core
    |
  0 +---------------------------------> weeks since signup
     0   1   2   3   4   5   6
```

The exact height where the curve flattens matters less than *whether* it flattens at all — a curve that stabilizes at 20% is a real, working product for a subset of users; a curve still sliding down at week 12 means you don't have product-market fit yet, regardless of the current percentage.

**When you'd actually use this**: instead of asking "is our retention good," ask "does our curve flatten, and around what week?" That's the actionable version of the question — it tells you both whether you have a durable core and how long it takes users to reach it.

## N-day vs. unbounded retention

Two common ways to define "retained at day N":

- **N-day retention (bounded)**: was the user active *on exactly day N* (or within a small window around it, e.g., day 7 ± 1)? Strict, but sensitive to noisy day-to-day usage patterns — a user active on day 6 and day 8 but not day 7 counts as churned that day.
- **Unbounded / rolling retention**: was the user active *at any point on or after day N*? More forgiving of irregular usage (weekly-cadence products, B2B tools used on weekdays only), but can overstate retention for products with a real "did they ever quit" moment.

| Definition | User active days: 1, 3, 8, 9, 30 | Retained at day 7? |
|---|---|---|
| N-day (exact day 7) | — | No (no activity on day 7) |
| N-day (day 7 ± 2 window) | — | Yes (day 8/9 fall in window) |
| Unbounded (any day ≥ 7) | — | Yes (day 8, 9, 30 all qualify) |

Pick the definition based on expected usage cadence, and — this is the important part — **state which one you're using whenever you report a number.** "Day-30 retention: 22%" is ambiguous and often gets misquoted across a team when the underlying definition isn't written down next to it.

**When you'd actually use this**: daily-habit products (chat, journaling) usually want N-day-with-small-window; weekly/monthly-cadence products (B2B SaaS, meal planning) usually want unbounded, or they'll systematically undercount healthy users.

## Common pitfalls

- **Mixing cohort sizes when comparing curves.** A cohort of 20 users and a cohort of 20,000 users can produce visually similar percentage curves, but the small cohort's curve is much noisier — one or two users leaving swings the percentage a lot. Always show (or at least know) the denominator behind each curve before comparing them.

  | Cohort | Size | Week 1 retained | Week 1 % | One user churns → |
  |---|---|---|---|---|
  | Small | 20 | 14 | 70% | 65% (a 5pt swing from 1 person) |
  | Large | 20,000 | 14,000 | 70% | 69.995% (basically unchanged) |

  Same starting percentage, wildly different stability. A "70% → 65%" week-over-week move means something for the large cohort; for the 20-user cohort it's one person having a bad week.
- **Survivorship bias.** If you only analyze users who are still around today to figure out "what do retained users have in common," you've excluded everyone who churned by construction — of course the survivors look engaged, they're the ones who survived. Always compare retained vs. churned cohorts, not just describe the retained ones in isolation.
- **Treating non-random cohorts as clean experiments.** It's tempting to compare "users who used feature X" vs. "users who didn't" as if that's an A/B test. It isn't — users who opted into a feature already differ from users who didn't (more engaged, found the feature through more effort, etc.). Any such comparison is a quasi-experiment at best; name the likely confounders explicitly before drawing conclusions, and prefer a real randomized rollout when the decision matters.

**When you'd actually use this**: before shipping a retention comparison in a deck or a report, check: are the two curves backed by comparable cohort sizes, did I compare against people who left (not just describe who stayed), and if this is a "feature users vs. non-users" comparison, have I named the selection bias out loud?

## Further reading

- Mixpanel — [How to do a cohort analysis](https://mixpanel.com/blog/cohort-analysis/)
- Wikipedia — [Survivorship bias](https://en.wikipedia.org/wiki/Survivorship_bias)
- Lenny's Newsletter — [What is good retention?](https://www.lennysnewsletter.com/p/what-is-good-retention-issue-29)
