# 📈 Product Analytics Playbook

**You shipped it. Now learn what your users actually do.**

Runnable recipes, plain-language theory, and case studies from real apps — product analytics for indie builders and vibe coders who suddenly have users and no analytics background.

> Building an app got easy. Understanding your users is the new bottleneck.
> Everything here follows one rule: **it must work on your data within an hour of cloning.**

Written by [BuildnWrite](https://buildnwrite.com/?utm_source=github&utm_medium=readme&utm_campaign=launch-2026q4) — notes on running this playbook on real funnels are on the blog.

## 🧭 Start Here — Theory

Short, practical guides. Each concept comes with "when you'd actually use this."

| # | Guide | What you'll learn |
|---|-------|-------------------|
| 1 | [Product Metrics](theory/01-product-metrics.md) | North Star, AARRR, engagement — and why vanity metrics lie |
| 2 | [Cohort & Retention](theory/02-cohort-retention.md) | Why snapshots mislead and cohorts don't; reading retention curves |
| 3 | [Funnel Analysis](theory/03-funnel-analysis.md) | Finding where users drop off, and what to do about it |
| 4 | [A/B Testing & Causality](theory/04-ab-testing.md) | Running experiments that don't fool you |
| 5 | [Statistics for PA](theory/05-statistics-for-pa.md) | Just enough stats: skewed data, significance, chi-square |
| 6 | [ML for PA](theory/06-ml-for-pa.md) | Churn prediction, LTV, segmentation — and why you probably don't need ML yet |
| 7 | [Metric Definitions](theory/07-metric-definitions.md) | Why the same log yields two different numbers, and how to reproduce a baseline before comparing to it |

## 🍳 Recipes — Runnable Code

Clone, run, swap in your data.

| Recipe | Stack | What it does |
|--------|-------|--------------|
| [Cohort Retention](recipes/cohort-retention/) | pandas · SQL | Build a retention matrix + heatmap two ways, with a hidden-pattern exercise |
| [Threads Engagement](recipes/threads-engagement/) | pandas · matplotlib | Read a content account like a product — why engagement rate misranks your best post. Runs on synthetic data, or [connect your own Threads/Meta account](recipes/threads-engagement/connect-meta.md) |
| [Weekly Funnel](recipes/funnel-weekly/) | raw JSONL · matplotlib | Did the thing you shipped work? Rebuild a funnel from a raw event log four times — the blended weekly number says no, both device segments say yes |
| [A/B Test Evaluation](recipes/ab-test-eval/) | scipy · matplotlib | The four checks before believing a result — sample size, validity, effect size with a CI, and what daily peeking costs (measured: 4.3% → 20.9%) |

**Coming soon**: Instrumentation starter kit

## 🔬 Case Studies — Real Apps, Real Numbers

Not toy datasets. These are analyses of actually-deployed services, with the mistakes left in.

| Case | Service | Headline finding |
|------|---------|------------------|
| [Board Game Web App](case-studies/board-game-webapp/) | A complex board game ported to the web | Two distinct churn types hid inside one "drop-off" number — and easy mode was bankrupting beginners |
| [Challenge Community](case-studies/challenge-community/) | A 12-week creator challenge (19 participants) | Naive weekly counting overstates churn (week 1 read 52.6% active, corrected: 84.2%); top 5 participants produced 54.6% of all submissions |

Bonus: [Analytics without Google Analytics](case-studies/board-game-webapp/instrumentation.md) — full funnel analysis with a UUID, a JSONL file, and zero external SDKs.

## 🗂 Data

- [Data Sources](data-sources.md) — practice datasets and public APIs, plus why your own app is the best dataset you'll ever get

## 🗺 Roadmap

- [x] Theory guides 01–07
- [x] Cohort retention recipe (pandas + SQL, cross-validated)
- [x] Threads engagement recipe (social API connector + the engagement-rate trap)
- [x] Weekly cohort funnel recipe (internal-actor exclusion, conversion windows, a mix-shift reversal)
- [x] Two real-service case studies
- [x] A/B test evaluation recipe (sample-size calculator, SRM + covariate balance, measured peeking cost)
- [ ] Instrumentation starter kit (drop-in, no-SDK event logging)
- [ ] Claude Code plugin packaging — each recipe as an installable skill

## 🤝 Contributing

One merge bar: **it must run right after cloning.**

```
your-recipe/
├── README.md          # overview → data → how to run → steps → results → interpretation
├── analysis.py        # running it saves charts to assets/
├── requirements.txt   # pinned versions
├── data/              # <1MB sample (larger data via fetch script)
└── assets/            # output charts
```

Case-study PRs are welcome too — real numbers from your own app, aggregates only, anonymized.

## ✍️ Author

**BuildnWrite** — a data analyst who mentors builders. Sharing perspective, not doctrine.

- Threads: [@buildnwrite](https://www.threads.com/@buildnwrite)
- LinkedIn: [jayjunglim](https://www.linkedin.com/in/jayjunglim/)
- Blog (Korean): [snowgot.tistory.com](https://snowgot.tistory.com/)

## License

[MIT](LICENSE) — use anything, a one-line credit is plenty.

---

*Looking for the earlier Korean-language general data-analysis content (Seoul apartment case study, sensor anomaly detection, analysis gallery)? It lives on the [`legacy-korean`](https://github.com/ggplab/product-analytics-playbook/tree/legacy-korean) branch.*
