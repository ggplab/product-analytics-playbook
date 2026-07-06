# 🗂 Data Sources

## The best dataset is your own app

If you've shipped anything, you already have the most valuable data source there is. Before hunting for datasets, instrument your app — it takes an afternoon:

- **No-SDK approach**: a localStorage UUID + append-only event log + a tiny stats endpoint. See [Analytics without Google Analytics](case-studies/board-game-webapp/instrumentation.md) for a real implementation
- **Hosted**: Google Analytics 4, PostHog, Plausible — fine choices, but know what events you need first (see [Product Metrics](theory/01-product-metrics.md))

## Practice datasets

For working through the recipes before pointing them at your own data.

| Source | What's there | Good for |
|--------|--------------|----------|
| [Kaggle Datasets](https://www.kaggle.com/datasets) | Community datasets — search "ecommerce", "telecom churn", "cohort" | Churn, retention, funnel practice |
| [Hugging Face Datasets](https://huggingface.co/datasets) | ML-oriented dataset hub | Text/behavioral data at scale |
| [UCI ML Repository](https://archive.ics.uci.edu) | Classic clean benchmark datasets | Algorithm practice |
| [Google Dataset Search](https://datasetsearch.research.google.com) | Search engine for datasets | "Does data like this exist?" |

Or generate your own: this repo's [cohort recipe](recipes/cohort-retention/) ships a seeded synthetic-data generator you can reshape.

## Public APIs

| Source | What's there |
|--------|--------------|
| [public-apis](https://github.com/public-apis/public-apis) | Huge curated list of free APIs (⭐440k+) |
| [RapidAPI](https://rapidapi.com) | Paid API marketplace, for when free doesn't cut it |
| [Korea open data portal](https://www.data.go.kr) | Korean public data — weather, transit, real estate (Korean) |

**Tip**: paste a list like this into an AI assistant and ask *"find me an API that fits what I'm building — is it free, what are the rate limits, what fields does it return?"* You get a comparison table without reading any docs.
