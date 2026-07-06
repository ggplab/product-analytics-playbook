# A/B Testing and Causality for Product Decisions

You shipped a new onboarding flow. Signups went up 12% the week after. Did the flow cause that, or did a Product Hunt feature, a slow news week for competitors, or plain randomness cause it? You can't tell from the "before vs. after" numbers alone — and shipping the wrong lesson from a correlation is how teams end up optimizing for noise. This doc covers why raw comparisons mislead, how randomization fixes that, and how to run an A/B test (and read its results) without fooling yourself.

## Why correlation lies

Look at your own product data and you'll find plenty of naturally occurring correlations: users who turn on notifications retain better, users with a filled-out profile convert more, users who hit a "power feature" early stick around longer. It's tempting to read each of these as "turn on notifications → users retain," and then go build a growth hack that nags people to enable them.

The problem is **confounding**. A confounder is a hidden variable that drives both sides of the correlation you're looking at. Take "users who enable notifications retain better": the more plausible story is that *engaged* users are the ones who bother to dig into settings and turn notifications on — engagement is the hidden cause behind both the setting and the retention. Force notifications on for everyone, and you don't get engaged users; you get annoyed ones. The correlation was real. The causal story you told yourself about it wasn't.

This is a general shape, not a one-off gotcha: whenever variable A and variable B are both downstream of some variable C you didn't measure, A and B move together with zero causal link between them. Data you collect by just watching what users already do — **observational data** — is full of these. You didn't assign anyone to a group; you're looking at choices users already made, and those choices are rarely random.

**When you'd actually use this**: any time a dashboard segment shows "users who did X retain/convert Y% better," pause before treating X as a lever. Ask what kind of user tends to do X unprompted — that's your confounder candidate.

## Randomization is the fix

**Experimental data** breaks the confounding problem by assigning users to groups *yourself*, at random, before you observe any outcome. If assignment is random, a confounder like "underlying engagement" gets spread roughly evenly across both groups by construction — it can't selectively load onto one arm of the test. Whatever difference remains between groups is attributable to the thing you changed, not to who self-selected into it.

This is the same logic behind clinical drug trials (randomized controlled trials, RCTs), just running on your product instead of on patients — practitioners sometimes call the online version an **online controlled experiment (OCE)**, which is the formal name for what everyone just calls an A/B test. A hashing function assigns each user (or session) to variant A or B, consistently, and you compare the metric between groups after enough traffic has passed through.

**When you'd actually use this**: whenever you're about to make a real product change based on a belief like "feature X drives retention," and you have enough traffic to split it — randomize instead of rolling it out to everyone and eyeballing the trend line.

## Pick the metric before you pick the winner

Decide what you're measuring before you look at any data, and pick something the change could plausibly move. Two failure modes show up constantly:

- **Metric too far downstream.** Testing a button color change against 90-day revenue will drown any real signal in unrelated noise — use click-through or immediate conversion instead, and treat revenue as something you sanity-check later, not the test's verdict.
- **Metric too easy to game.** "Time on page" goes up when your UI gets more confusing, not necessarily more valuable. Prefer metrics where more is unambiguously better for the user.

Also pick one primary metric. If you track ten metrics and declare victory on whichever one turns green, you've quietly reintroduced the peeking problem (below) through a side door — testing ten things is ten chances for a fluke to look real.

**When you'd actually use this**: write the metric name down in the test plan before launch, not in the readout doc after.

## Sample size before you start

The single most common indie-builder A/B testing mistake is starting a test with no sense of how much traffic it needs, then checking it daily until something looks green. Sample size should be a pre-launch calculation, not a post-hoc question.

Here's a worked version. Say your current free-trial-to-paid conversion is 5%, and you believe a new upgrade prompt could lift it to 7% — a 40% relative improvement, which is a big deal if it's real. Using the standard sample-size formula for comparing two proportions:

```
n ≈ (Z_α/2 + Z_β)² · [p1(1-p1) + p2(1-p2)] / (p1 - p2)²
```

with `Z_α/2 = 1.96` (95% confidence) and `Z_β = 0.84` (80% power), plugging in `p1 = 0.05` and `p2 = 0.07` gives roughly **2,200 users per arm** (about 4,400 total) before you can trust the result either way. If your product gets 200 signups a week, that's several months of test — worth knowing on day one, not week six when you're staring at a still-inconclusive dashboard.

You don't need to hand-derive this every time — tools like Evan Miller's sample size calculator do the arithmetic for you. The point isn't the formula; it's the habit of computing a required N (and therefore a rough test duration) *before* you launch the test. See [05-statistics-for-pa.md](05-statistics-for-pa.md) for the standard error and confidence interval mechanics this formula rests on.

**When you'd actually use this**: before launching any test, write down your baseline rate, the minimum lift worth caring about, and the resulting sample size / duration. If the duration is longer than you're willing to wait, you either need more traffic, a bigger expected effect, or a different validation method (see the last section).

## The p-value interpretation traps

Say your test finishes: variant A converted 45 of 900 users (5.0%), variant B converted 63 of 900 (7.0%) — an 18-conversion, 40%-relative difference that would be real money if it holds. Run the numbers and you get p ≈ 0.074. At the conventional α = 0.05 threshold, that's "not statistically significant." A lot of builders' instinct here is to round up anyway, because the difference *looks* real and feels like it should count. Resist that instinct — this exact setup (a plausible-looking lift that fails the significance bar) is the standard case where teams talk themselves into a false win.

A few traps worth memorizing, because each one gets used to justify a decision it doesn't actually support:

- **p is not "the probability B is better."** It's the probability of seeing a difference this large (or larger) *if there were truly no difference at all*. It says nothing about how likely your hypothesis is to be true.
- **p > 0.05 is not proof of "no effect."** It means you don't have enough evidence yet — often because the sample size above wasn't reached. Absence of evidence, not evidence of absence.
- **Big samples make tiny differences "significant."** With a few hundred thousand users, a 0.1 percentage point difference in conversion can hit p < 0.05 while being completely irrelevant to the business. Always look at effect size alongside p, not p alone.
- **A significant result on a bad metric is still a bad result.** Statistical significance answers "was this due to chance," not "does this matter." Keep the metric-choice discipline from the section above.

**When you'd actually use this**: whenever a test result lands near the 0.05 line, resist the urge to round it in the direction you were hoping for. A close call usually means "run it longer" or "the effect is smaller than you hoped," not "ship it anyway."

## The peeking problem

Checking your A/B test dashboard every morning and stopping the moment it flips green feels responsible. It's actually one of the most reliable ways to manufacture a false positive. Each time you peek and run a significance test, you get another chance for random noise to cross the 0.05 threshold — check daily for two weeks and your real false-positive rate is well above the 5% you think you signed up for, even though every individual check used α = 0.05 correctly.

The fix is deciding your sample size and/or duration in advance (previous section) and only evaluating significance once you hit it. If you genuinely need to monitor a live test, use a method built for it — sequential testing frameworks or "always-valid" p-values adjust the threshold as you go, instead of letting repeated looks quietly inflate your error rate. That's a deliberate design choice, not something you back into by checking a dashboard whenever you feel like it.

**When you'd actually use this**: before a test starts, decide when you'll look at it (a date or a sample size), write it down, and don't evaluate significance before then — checking the raw numbers out of curiosity is fine, acting on them isn't.

## When you can't A/B test

Early-stage products often don't have the traffic for the sample sizes above — a few hundred users a month can't reach 2,200 per arm in any reasonable time. A few honest fallbacks, roughly in order of rigor:

- **Cohort comparison over time.** Compare a metric for users who signed up before a change to users who signed up after. This is observational, not experimental — every confounder problem from the first section applies, since "signed up after the change" is also correlated with anything else that changed around the same time (season, marketing channel, pricing). Treat it as a hint, not a verdict — see the caveats in [Cohort Retention Analysis](../recipes/cohort-retention/) on reading cohort curves without over-attributing differences to a single cause.
- **Bigger, more obvious changes.** If you can't detect a 2-point conversion lift reliably, don't test 2-point changes — test the kind of change you'd expect to move the needle 20+ points. Bigger effects need smaller samples to detect.
- **Statistical adjustment on observational data.** When randomization truly isn't possible, causal-inference techniques (propensity score matching, difference-in-differences) attempt to construct comparable groups after the fact by controlling for known confounders. This is a deeper topic than this doc covers — worth knowing the term exists so you can look it up when you hit the wall where A/B testing isn't an option.

**When you'd actually use this**: pre-product-market-fit, most of the time. Don't force an underpowered A/B test just because it feels more rigorous than a cohort comparison — an underpowered experiment that never reaches significance is worse than an honest, caveated observational read.

## Pre-launch checklist

Before you flip a test live, you should be able to check off all four of these — each one maps to a section above:

| Question | Section |
|---|---|
| What's the one metric that decides this test? | Pick the metric before you pick the winner |
| What's the minimum effect size worth caring about, and what sample size does it require? | Sample size before you start |
| When (date or N) will you look at significance — and will you resist looking before then? | The peeking problem |
| If you can't hit that sample size, what's your fallback (cohort comparison, bigger change, causal adjustment)? | When you can't A/B test |

If you can't answer one of these, that's the thing to fix before launch — not something to figure out from the readout after the fact.

## Further reading (Korean)

This doc is grounded in a Korean-language blog series on causal inference for product analytics by the same author. The originals go deeper into the math and include Python/R walkthroughs:

- [Why product teams reach for A/B tests](https://snowgot.tistory.com/168) — observational studies vs. RCTs, the confounding problem
- [Randomized experiments, standard error, and confidence intervals](https://snowgot.tistory.com/158) — the statistical machinery behind an online controlled experiment
- [Significance testing walkthrough](https://snowgot.tistory.com/129) — a worked click-rate example, including the "looks real but isn't significant" trap
- [Sample size calculation for A/B tests](https://snowgot.tistory.com/130) — deriving the two-proportion sample size formula with a worked example
- [Graphical causal models (DAGs)](https://snowgot.tistory.com/159) — chain/fork/collider structures for reasoning about confounders visually
- [Propensity score matching](https://snowgot.tistory.com/162) — what to do when randomization genuinely isn't an option
