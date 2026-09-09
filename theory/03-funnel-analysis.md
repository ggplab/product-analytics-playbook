# Funnel Analysis

A funnel measures how many users move through an ordered sequence of steps toward a goal — signup → onboarding → first action → payment, or whatever your product's path to value looks like. Where cohort analysis (see `../theory/02-cohort-retention.md`) asks "do users come back over time," funnel analysis asks "how far do users get through one specific journey, and where do they drop off." Both matter; they answer different questions from the same event data.

## Funnel vs. cohort: state vs. time

It's easy to conflate these because both start from grouping users, but they're built on different axes:

| | Funnel | Cohort |
|---|---|---|
| Axis | Steps (ordered, no fixed time scale) | Calendar time (days/weeks/months since signup) |
| Question | "Where do people get stuck?" | "Do people stick around?" |
| Typical output | A bar chart shrinking left to right | A curve flattening or decaying over time |
| Denominator | Users who entered step 1 | Users in the cohort at signup |

A funnel is a single pass through a process; a cohort is repeated observation of the same group over time. You can combine them — e.g., "activation funnel completion rate, broken out by signup cohort" — to see if onboarding is improving month over month, but they're conceptually separate tools.

**When you'd actually use this**: if the question is about a specific sequence of actions (checkout, onboarding, upload flow), reach for a funnel. If the question is about whether engagement holds up over weeks or months, reach for cohorts. Using the wrong one is the single most common way people confuse themselves — e.g. blaming "onboarding" for a decline that's actually a retention/dilution effect from `02-cohort-retention.md`.

## Defining steps

The first real decision in any funnel is what counts as a step, and it's more consequential than it looks. Two failure modes:

- **Too coarse**: "Signed up → Paid." You'll see a big drop and learn nothing about *why*. There's no action to point at and fix.
- **Too granular**: tracking every button click and micro-interaction turns the funnel into noise — a hundred near-identical steps with fractional drop-offs at each, none of which represents a real decision point for the user.

A good funnel step is a discrete action that represents a real decision or a real capability the user just gained. For a typical SaaS activation funnel:

```
1. Signed up
2. Verified email
3. Created first project
4. Invited a teammate  (or: connected first integration)
5. Completed first "real" action (e.g., ran first report)
```

Each step should be something you could point to in the product and say "yes, this happened" — a row in an events table, not an inference.

**When you'd actually use this**: if you can't explain, in one sentence, what a user *did* to trigger a step, the step is defined too loosely — go find the concrete event.

## Conversion windows

A funnel step doesn't happen instantly — a user might sign up today and not complete onboarding for five days. A conversion window is the time limit you allow between one step and the next before you count the user as having failed to convert.

Without a window, "conversion rate" is ambiguous — do you count someone who took 6 months to go from signup to first purchase the same as someone who took 6 minutes? Practically:

| Funnel type | Typical window |
|---|---|
| Checkout flow | Minutes to 1 hour |
| Onboarding / activation | 1–7 days |
| Free-to-paid conversion | 14–30 days (often tied to a trial length) |

Pick the window based on the natural rhythm of the action, not a default. A checkout funnel with a 30-day window will look artificially good — it's giving up-front carts credit for purchases that happened weeks later for unrelated reasons. A B2B activation funnel with a 1-hour window will look artificially bad — decision-makers often need days to loop in a teammate.

```sql
-- step 1 -> step 2 conversion, within a 7-day window
select
  count(distinct s1.user_id) as reached_step1,
  count(distinct s2.user_id) as reached_step2,
  round(100.0 * count(distinct s2.user_id) / count(distinct s1.user_id), 1) as conversion_pct
from events s1
left join events s2
  on s1.user_id = s2.user_id
  and s2.event_name = 'created_first_project'
  and s2.event_time between s1.event_time and s1.event_time + interval '7 days'
where s1.event_name = 'signed_up';
```

**When you'd actually use this**: any time you report a conversion rate, state the window next to it. "Signup → paid: 8%" is not comparable across teams or time periods unless everyone agrees it means "within 14 days."

## Drop-off diagnosis

Once you see a drop between two steps, the number alone doesn't tell you why. Useful next moves, roughly in order of effort:

1. **Segment the drop** (see below) — is it universal, or concentrated in one channel/device/plan?
2. **Look at time-to-convert among those who did convert** — if it's oddly long, users are probably getting stuck and figuring it out themselves; the step may need a nudge, not a redesign.
3. **Check for a silent technical failure** — a broken button, a slow-loading step, a form validation bug — before assuming it's a UX or motivation problem. A funnel drop that started on a specific date is often a deploy, not a behavior change.
4. **Talk to a handful of users who dropped off**, if you can reach them. Quantitative funnels tell you *where*; they rarely tell you *why* on their own.

A worked example:

| Step | Users | Conversion from previous |
|---|---|---|
| Signed up | 1,000 | — |
| Verified email | 780 | 78% |
| Created first project | 460 | 59% |
| Invited teammate | 90 | 20% |
| Ran first report | 75 | 83% |

The 59% → 20% drop between "created project" and "invited teammate" is the biggest single-step leak by far, worse than the drop into it or out of it. That's where diagnosis effort belongs — not on the email verification step, even though its raw number (78%) looks lower than "invited teammate → ran first report" (83%), because it's the *relative* drop at each step that matters, not the absolute count remaining.

**When you'd actually use this**: rank steps by conversion-rate drop, not by raw user count remaining — the biggest opportunity is usually the step with the steepest percentage decline, not the step with the most users sitting in front of it.

## Segment comparison

Splitting a funnel by segment — acquisition channel, plan, device, geography, signup cohort — often reveals that an "average" 40% drop is actually two very different stories layered on top of each other.

| Segment | Signup → Activated |
|---|---|
| Organic / referral | 62% |
| Paid search | 24% |
| Mobile web | 18% |
| Desktop | 51% |

If paid search is dragging the blended average down, the fix is either better targeting/landing pages for that channel, or accepting a lower blended activation rate as the cost of that acquisition channel — but you'd never know to make that call from the blended number alone. This is the same underlying idea as splitting cohorts by channel in retention analysis: an average across a mixed population usually hides the more useful, more actionable story.

**When you'd actually use this**: whenever a funnel number is used to justify a decision (kill a channel, redesign a step, change pricing), segment it first — the blended number is rarely the number the decision should actually be based on.

## Statistical significance of step differences

Before concluding that Version B's onboarding step converts better than Version A's, check whether the difference could plausibly be noise. A two-proportion comparison is the right tool: each step's conversion rate is a proportion (converted / entered), and you're asking whether two proportions differ by more than sampling variation would explain.

Rule-of-thumb sample sizes needed to detect common effect sizes reliably (roughly, for a two-sided test at conventional confidence):

| Baseline conversion | Effect size you want to detect | Users needed per variant (rough) |
|---|---|---|
| 20% | +5 percentage points (→25%) | ~1,000 |
| 20% | +2 percentage points (→22%) | ~6,000 |
| 5% | +2 percentage points (→7%) | ~1,700 |

The pattern: smaller baseline rates and smaller effect sizes both demand dramatically more users. This is the single most common mistake in early-stage funnel comparisons — declaring a redesign "worked" off of 40 users in each arm, when the observed difference is comfortably inside the range random variation would produce on its own.

**When you'd actually use this**: before running an A/B test on a funnel step, estimate the sample size you'll need for the effect size you actually care about — if your traffic won't get you there in a reasonable time, either pick a higher-leverage step (more users, bigger expected effect) or don't treat the result as conclusive. For a deeper, worked-through walk on why teams reach for A/B tests on funnel steps and where that reasoning goes wrong, see the author's write-up: [snowgot.tistory.com/168](https://snowgot.tistory.com/168) (Korean).

For a runnable version of everything above — conversion windows, cohort bucketing, and segment comparison applied to a raw event log, where skipping them would have got the decision wrong — see [`../recipes/funnel-weekly/`](../recipes/funnel-weekly/). For real funnels analyzed end-to-end with actual data, see `../case-studies/`.

## Further reading

- Wikipedia — [Funnel analysis](https://en.wikipedia.org/wiki/Funnel_analysis)
- Wikipedia — [A/B testing](https://en.wikipedia.org/wiki/A/B_testing)
- BuildnWrite — [왜 프로덕트 팀은 A/B 테스트를 사랑하는가](https://snowgot.tistory.com/168) (Korean deep dive on statistical significance in product decisions)
