# Product Metrics That Matter

You shipped something. People are signing up. Now what do you actually look at?

Most indie builders start with whatever number their dashboard shows first — usually total signups or total page views. Those numbers only go up, which feels good and tells you almost nothing about whether your product is working. This doc covers the metrics that actually correlate with a product people keep using: a North Star metric, the AARRR funnel stages, and the engagement metrics (DAU/WAU/MAU, stickiness) that tell you if people are coming back.

## Why vanity metrics mislead

A vanity metric is any number that only goes up and never forces a decision. Cumulative signups is the classic one — it's a running total, so even a product that's hemorrhaging users every week still shows a rising line.

| Metric | Cumulative signups | Weekly active users |
|---|---|---|
| Week 1 | 100 | 80 |
| Week 4 | 400 | 60 |
| Week 8 | 900 | 25 |

Both are true. Only one tells you the product is dying. Cumulative signups went up 9x; weekly actives dropped 69%. If you only track the first number, you'll keep spending on acquisition into a leaky bucket.

The same trap applies to page views, total downloads, total API calls, and "total messages sent." They're all counters that can't decrease, so they can't carry bad news. A metric that can't go down can't warn you.

**When you'd actually use this**: before you add any metric to a dashboard, ask "can this number tell me something is wrong?" If the answer is no, it's a vanity metric — fine as a side note, not as a decision input.

## North Star metric

Your North Star metric (NSM) is the single number that best represents the core value your product delivers to users — chosen so that moving it up is (almost) always good for the business, not just good for a dashboard.

A good NSM has three properties:
- It reflects value delivered to the user, not effort spent by the company (don't pick "emails sent by us"; pick "problems solved for the user").
- It's a leading indicator of revenue/retention, not a lagging one (revenue itself is usually a bad NSM — it moves too slowly to guide weekly decisions).
- Teams can actually move it with the levers they control.

Examples from well-known products, for calibration:

| Product | North Star metric (not revenue) |
|---|---|
| Airbnb | Nights booked |
| Spotify | Time spent listening |
| Slack | Messages sent between teammates |
| A habit-tracking app | Days with at least one habit checked off |

For a solo-built app, a reasonable starting NSM is usually "count of the one action that proves the user got value" — e.g., for a note-taking app, "notes created and reopened within 7 days" (creation alone doesn't prove value; reopening does).

**When you'd actually use this**: pick one NSM per product, write down why it's the one, and revisit it quarterly. If you find yourself needing a different metric to explain every decision, your NSM is too narrow or wrong.

## The AARRR funnel (pirate metrics)

AARRR breaks the user lifecycle into five stages, each with its own metric and its own lever:

| Stage | Question | Example metric |
|---|---|---|
| **Acquisition** | How do users find you? | Signups by channel |
| **Activation** | Do they have a good first experience? | % reaching "aha moment" in session 1 |
| **Retention** | Do they come back? | Day-7 / Day-30 retention |
| **Referral** | Do they tell others? | Invites sent, viral coefficient |
| **Revenue** | Do they pay? | Conversion to paid, MRR per user |

The point of splitting these out is that each stage has a different failure mode and a different fix. If Acquisition is fine but Activation is bad, more marketing spend just fills a leaky bucket faster — the fix is onboarding, not ads. If Activation and Retention are both fine but Revenue is flat, you likely have a pricing or packaging problem, not a product problem.

Most early-stage builders over-invest in Acquisition because it's the most visible and the easiest to buy (ads, SEO, launches) — and under-invest in Activation, which is usually the cheapest stage to fix and has the highest leverage, since every downstream stage depends on it.

**When you'd actually use this**: when growth stalls, walk the funnel top to bottom before deciding where to invest. It's tempting to default to "we need more users" — check Activation and Retention first, they're usually the actual leak.

See `../theory/03-funnel-analysis.md` for how to instrument and measure a funnel like this precisely (step definitions, conversion windows, drop-off diagnosis).

## Engagement metrics: DAU / WAU / MAU and stickiness

Once users are activated, the next question is whether they keep coming back and how often. Three counters do most of the work:

- **DAU** — unique users active on a given day
- **WAU** — unique users active in the trailing 7 days
- **MAU** — unique users active in the trailing 30 days

None of these alone means much without the others. The ratio between them — **stickiness** — is where the signal is:

```
Stickiness = DAU / MAU
```

Stickiness estimates the fraction of your monthly user base that's active on a typical day. A daily habit product (chat apps, note apps) tends toward 40–60%+. A monthly-cadence product (payroll software, tax tools) will look "broken" by this yardstick even when it's healthy — the metric assumes daily-use is the right cadence, and it isn't for every product.

| Product type | Expected DAU/MAU | What low stickiness means here |
|---|---|---|
| Daily habit app (journaling, chat) | 40–60%+ | Something's wrong — investigate |
| Weekly-cadence app (meal planning) | 15–25% | Normal |
| Monthly/quarterly tool (tax filing) | <10% | Normal — wrong metric to worry about |

A worked example: an app has 1,000 MAU and 250 DAU → stickiness = 25%. If it's a daily-journaling app, that's a red flag: three-quarters of your "active" base isn't opening the app on any given day. If it's a monthly budgeting app, 25% is actually strong.

```sql
-- DAU / WAU / MAU on a single events table (event_date, user_id)
select
  count(distinct case when event_date = current_date then user_id end)                       as dau,
  count(distinct case when event_date >= current_date - 6 then user_id end)                   as wau,
  count(distinct case when event_date >= current_date - 29 then user_id end)                  as mau
from events;
```

**When you'd actually use this**: track stickiness as a trend, not a snapshot. A single 25% reading means nothing without knowing your product's expected cadence and whether the number is rising or falling month over month.

### Rolling window vs. calendar period

There are two ways to define WAU and MAU, and mixing them up is a common source of confusing dashboards:

- **Rolling (trailing N days)**: "active in the last 7 days, as of right now." Updates every day, smooths out day-of-week noise, and is what most product-analytics tools compute by default.
- **Calendar period**: "active at any point during this specific Monday–Sunday week" or "this specific calendar month." Only finalizes once the period ends, but makes week-over-week and month-over-month comparisons cleaner because every period is the same fixed bucket.

A rolling WAU checked on a Tuesday and a calendar WAU for the current (incomplete) week can differ meaningfully — the calendar version will look artificially low simply because the week isn't over yet. Pick one definition, label it on the chart, and don't compare a rolling number from one report against a calendar number from another.

**When you'd actually use this**: if you're debugging "why does WAU look different in tool A vs. tool B," check this first — it's the single most common cause of two dashboards disagreeing on numbers computed from the same underlying events. For the full set of definition choices behind any rate, and what to do when you inherit a number you can't reproduce, see [07-metric-definitions.md](07-metric-definitions.md).

## Putting it together

A minimal metrics stack for a solo-built app:

1. One North Star metric, tracked weekly.
2. AARRR breakdown to locate where the funnel leaks.
3. DAU/WAU/MAU + stickiness to see if retained users are actually engaged, not just "not yet churned."
4. Cohort retention curves (next doc) to see whether engagement is stabilizing or decaying over time — a snapshot of DAU/MAU on one day can't tell you that.

None of this requires a BI tool on day one — a SQL query against your events table and a spreadsheet gets you 90% of the value. The important habit is picking metrics that can carry bad news, not ones that only ever go up.

## Further reading

- Amplitude — [North Star Metric](https://amplitude.com/blog/north-star-metric)
- Wikipedia — [Lean Startup](https://en.wikipedia.org/wiki/Lean_startup) (origin of the "vanity metrics" framing)
