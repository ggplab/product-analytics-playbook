# Metric Definitions

A number is not a measurement until you can say how it was computed. "Activation is 14%" is not a fact about your product — it's a fact about your product *and* a dozen choices you made on the way to the number: which users you counted, which you excluded, what counted as activation, how long you gave people to get there, and where you drew the start and end of the period.

This is the least glamorous document in the folder and the one that costs the most when it's skipped. Every other guide here assumes you can put two numbers side by side. This one is about when you actually can.

## The choices behind any rate

Every rate you report makes six decisions. Most reports state one of them.

| Choice | The question it answers | A cheap way to get it wrong |
|---|---|---|
| Numerator | What counts as success? | "Activated" meaning three different things in three docs |
| Denominator | Who had the chance to succeed? | Counting users who were never eligible for the step |
| Unit of count | Events, sessions, or people? | Mixing "sessions that converted" with "users who converted" |
| Time window | How long does someone have? | No window at all, so the rate silently rises forever |
| Exclusions | Who isn't a real user? | The team's own accounts, bots, load tests, your own staging traffic |
| Attribution | Which period/segment does a conversion belong to? | Crediting a conversion to the week it happened rather than the week the user arrived |

The unit of count is the one people are most confident about and most often wrong on, because all three answers are defensible and they produce different numbers from the same log:

```
sessions that reached checkout / sessions      →  "checkout rate 12%"
users who ever reached checkout / users        →  "checkout rate 31%"
checkout events / product-page views           →  "checkout rate 4%"
```

None of these is the true one. They answer different questions — "how often does a visit end in checkout," "how many people ever get there," "how much does a product page pull its weight." A report that doesn't say which is a report that can't be checked.

**When you'd actually use this**: write the six choices down once per metric, in the same place the metric lives. It takes ten minutes and it's the only thing that makes the number survivable six months later, when the person who computed it is you-from-before and can't be asked.

## Reproducing a baseline before comparing to it

Here is the situation this document exists for. Three weeks after a launch, you want to know whether traffic quality improved. You have a note from launch week recording the baseline: **128 visits, 30% started, 14% completed.** The note doesn't say over what window, or whether the founder's own visits were in it.

The tempting move is to compute today's numbers with whatever definition seems reasonable and subtract. That produces a delta, and some unknown fraction of that delta is your own definition choices rather than anything that happened to the product.

What to do instead: treat the baseline's numbers as a **fingerprint** and search for the definition that reproduces them. From a real audit of a deployed side project, sweeping candidate windows against candidate segments:

| Window | Segment | visits | starts | completes | start % | complete % |
|---|---|---|---|---|---|---|
| 08-01 – 08-02 | owner excluded | 46 | 20 | 9 | 43% | 20% |
| 08-01 – 08-03 | owner excluded | 102 | 34 | 14 | 33% | 14% |
| **08-01 – 08-03 12:27** | **owner excluded** | **127** | **38** | **18** | **30%** | **14%** |
| 08-01 – 08-04 | owner excluded | 146 | 42 | 20 | 29% | 14% |
| 08-01 – 08-03 12:27 | everyone | 130 | 41 | 18 | 32% | 14% |

One row reproduces the baseline: 30% and 14% both land, and visits come in at 127 against the recorded 128. The window turned out to end at the moment the note was written, not at a day boundary — the author had simply run the query and written down what it said. The segment excluded three owner IDs. The unit was distinct anonymous IDs, not sessions.

Only after that was fixed did the audit compute a single delta, using that same definition throughout.

Two things worth taking from this. First, three of the four figures reproduce exactly and visits lands one off, and that one is explained rather than waved away: the note was written mid-day, so a visitor arriving in the same minute could fall on either side of the cutoff. An unexplained discrepancy would mean the definition is still wrong. Second, the window nobody would have guessed — "up to the minute the note was written" — is the normal case, not a freak one. Ad-hoc numbers get recorded when someone runs a query, and the query's implicit `now()` goes unrecorded.

**When you'd actually use this**: any time you report a change against a historical number you did not personally compute. If you cannot reproduce the old number, say so and report both numbers under your definition instead of reporting a delta.

## Denominators of different difficulty

Two rates can be built identically and still not be comparable, because the thing being divided by isn't equally hard in both cases.

An example with real numbers. In a game AI project, 6,155 human decision points were replayed and scored by whether the AI's top-ranked move matched the human's. Reported by decision type:

| Decision phase | n | Avg. options available | Top-1 match |
|---|---|---|---|
| build | 2,460 | 221.4 | 14.4% |
| moveGoods | 1,392 | 55.9 | 39.9% |
| auction | 901 | 18.0 | 34.9% |
| issueShares | 688 | 9.1 | 55.8% |

Read the last column alone and the conclusion is obvious: the AI is worst at building, so fix building. But `build` offers an average of 221 legal moves and `issueShares` offers 9. Matching the human's pick 14.4% of the time out of 221 candidates and 55.8% of the time out of 9 are not the same feat, and the raw column can't tell you which is harder.

The original analysis normalized by **mean rank** instead: where in the ranked option list did the human's actual choice fall? On build it sat at rank 36.9 of 221.4 on average — roughly the top 17% of the pool. Ranked that way, build is not the weak phase at all, and the conclusion the raw column pointed at was backwards.

Mean rank is one normalization, not the normalization. Another common one is lift over a chance floor: if a random pick scores 1/221.4 on build and 1/9.1 on issueShares, both rates are far above chance, build by the larger multiple. That framing is tempting because the multiple is dramatic — and it's the weaker choice here, for two reasons worth internalizing. A chance floor assumes uniform random selection, but build's 221 options are mostly near-duplicate placements, so nothing sensible picks uniformly among them. And ratios of small probabilities inflate: dividing by 0.45% manufactures a large number out of a modest absolute gain.

The lesson is not "use mean rank." It's that every normalization encodes an assumption about what the denominator's difficulty *is*, and you have to be able to say what yours assumes before the normalized comparison means anything.

There is no product-analytics version of this that involves game AI, but there are many that involve the same mistake:

- **Click-through rate across surfaces with different list lengths.** A 2% CTR on a 50-item search page and a 2% CTR on a 3-item recommendation strip are not the same performance.
- **Conversion across funnels with different step counts.** A 5-step onboarding will show a lower end-to-end rate than a 2-step one even if every step is better.
- **"% of users who used feature X"** where X is only reachable by a subset. The denominator is all users; the eligible population is much smaller.
- **Support-resolution rate by ticket category**, where categories differ wildly in how solvable they are.

The shape of the fix is the same in all of them: divide by what was actually achievable, or put both numbers on a common scale — rank percentile, rate among the eligible, or a floor you can defend — before you rank them. Which scale is a judgement call, and it belongs in the metric spec next to the number.

**When you'd actually use this**: before ranking anything — channels, features, cohorts, surfaces — ask whether each item's denominator represents the same degree of difficulty. If it doesn't, the ranking is measuring difficulty, not performance.

## A metric spec worth pasting

Six lines next to the metric, in the dashboard description or the query header:

```yaml
metric: activation_rate
numerator:   users who ran their first report
denominator: users who signed up
unit:        distinct user (not session, not event)
window:      21 days from first visit
exclusions:  anonIds listed in actors.json (3 internal)
attribution: cohorted by the user's first-seen ISO week
owner:       @you, last reviewed 2025-05-12
```

This is an illustrative spec for the product the [Weekly Funnel recipe](../recipes/funnel-weekly/) models, not one of the rates that recipe reports — the window, exclusion list and attribution are its real settings, the numerator and denominator are there to show the shape. That block is the difference between a number someone can check and a number someone has to trust. It also makes the failure mode above impossible: a future reader doesn't have to reverse-engineer your window, because you wrote it down.

**When you'd actually use this**: the first time a metric appears in a document that outlives the conversation it came from.

## When two numbers stop being comparable

Even with definitions locked, comparability can break underneath you. The usual causes, in rough order of how often they bite:

| Cause | What happens | Where it's worked through |
|---|---|---|
| Mix shift | Every segment improves and the blended number falls, or vice versa | [Weekly Funnel recipe](../recipes/funnel-weekly/) |
| Definition drift | Someone "fixes" the numerator; the series has a silent seam | Nowhere yet — the spec block above is the prevention |
| Instrumentation change | A new event fires earlier, so the funnel's top step inflates | [instrumentation.md](../case-studies/board-game-webapp/instrumentation.md) |
| Exclusion-list change | An ID is added to the internal list and history isn't recomputed | [Weekly Funnel recipe](../recipes/funnel-weekly/) |
| Rolling vs. calendar window | Two dashboards disagree from the same events | [01-product-metrics.md](01-product-metrics.md) |
| Right censoring | The newest cohort hasn't had time to convert and looks worse | [02-cohort-retention.md](02-cohort-retention.md) |

The habit that covers most of these: when a metric moves, check whether the *population* or the *definition* moved before concluding the *product* did. It's a five-minute check and it's wrong to skip it exactly when the number is exciting.

## Related docs

- [01-product-metrics.md](01-product-metrics.md) — picking which metrics to define in the first place, and the rolling vs. calendar window case
- [03-funnel-analysis.md](03-funnel-analysis.md) — conversion windows and segment comparison, the two definition choices funnels get wrong most
- [Weekly Funnel recipe](../recipes/funnel-weekly/) — a runnable event log where four definition choices each change the answer, one of them by 11 percentage points

## Further reading

- Wikipedia — [Simpson's paradox](https://en.wikipedia.org/wiki/Simpson%27s_paradox) — the formal name for a blended number moving opposite to all of its parts
- Wikipedia — [Reproducibility](https://en.wikipedia.org/wiki/Reproducibility) — the general form of "can someone else get your number again"
- Wikipedia — [Base rate](https://en.wikipedia.org/wiki/Base_rate) — why a rate means nothing without the floor it's measured against
