# Machine Learning for Product Analytics

"We should build a churn model" is one of the most common asks in a product analytics roadmap, and one of the most commonly premature. Before reaching for `scikit-learn`, it's worth knowing what a groupby already answers, and what the three ML use cases that actually come up in product work — churn prediction, LTV estimation, user segmentation — look like in practice.

## You probably don't need ML yet

A model is worth building when you need a *prediction per user* that a segment-level summary can't give you — "will this specific user churn in the next 30 days" is a different question from "which segment churns most." Most product questions are the second kind, and a `groupby` answers them directly:

```python
df.groupby("plan_tier")["churned"].mean()
df.groupby(["signup_channel", "signup_month"])["day_30_retained"].mean()
```

This gets you 80% of what teams reach for ML to answer: which segments churn more, which channels retain worse, whether a cohort's behavior is degrading over time. It's also faster to build, easier to explain to a teammate, and doesn't carry the maintenance cost of a model that needs retraining as user behavior drifts. See [Cohort Retention Analysis](../recipes/cohort-retention/) for exactly this kind of segment-level breakdown done end to end with pandas and SQL, no model involved.

**When you'd actually use this**: reach for a model only once you've hit a real ceiling on groupby — e.g., you need a per-user risk score to prioritize outreach, not just "know that free-tier users churn more."

## Churn prediction (classification)

Churn prediction is a binary classification problem — predict whether a specific user will churn (1) or not (0) in some future window, using their past behavior as features.

The first thing that breaks naive churn models is **class imbalance**: if 5% of users churn in a given month, a model that predicts "never churns" for everyone is 95% accurate and completely useless. Accuracy is the wrong metric here — it rewards ignoring the minority class you actually care about. Two things to do about it:

- Rebalance the training data (oversample the churn class, e.g. SMOTE, or undersample the majority class) so the model doesn't learn to ignore churners.
- Evaluate with **precision, recall, and AUC** instead of accuracy:
  - **Precision** — of the users flagged as likely to churn, how many actually did. Matters when acting on a false positive is expensive (e.g., an expensive retention discount sent to someone who was never leaving).
  - **Recall** — of the users who actually churned, how many the model caught. Matters when missing a real churner is expensive (they're gone, and you never got the chance to intervene).
  - **AUC-ROC** — how well the model ranks churners above non-churners across every possible decision threshold, useful when you haven't committed to a threshold yet and want to compare models on overall separability.

The precision/recall tradeoff is a real business decision, not just a modeling detail: if your retention intervention is cheap (an in-app nudge), bias toward recall and accept some false positives; if it's expensive (a human outreach call, a discount), bias toward precision.

**When you'd actually use this**: you have enough churned users (a few hundred, minimum) to train on, a meaningful and not-too-expensive intervention to act on the prediction, and groupby-level segment analysis has already told you churn isn't explained by one or two obvious segments.

## LTV estimation (regression)

Lifetime value (LTV) estimation predicts a continuous number — expected revenue per user over some horizon — usually from early behavioral signals (first-week activity, initial plan tier, acquisition channel).

Two things matter more here than model choice:

- **Check the regression assumptions before trusting the coefficients** — linearity between features and LTV, no severe multicollinearity between features (two features that are near-duplicates of each other make coefficients unstable and hard to interpret), and reasonably consistent error variance across the prediction range. Skipping this doesn't break the model's ability to produce *a* number, but it does break your ability to trust *what the number depends on*.
- **Regularize when you have many correlated behavioral features** — early product usage signals (sessions in week 1, features touched, days active) tend to correlate heavily with each other. **Ridge** (L2) shrinks all coefficients together and stabilizes estimates under multicollinearity; **Lasso** (L1) can zero out coefficients entirely, which doubles as automatic feature selection when you're not sure which early signals actually matter.

Revenue and LTV data is also usually right-skewed (see [05-statistics-for-pa.md](05-statistics-for-pa.md) on why means mislead on skewed data) — a log transform on the target before fitting, and transforming predictions back afterward, is a common fix worth trying before assuming the model itself is broken.

**When you'd actually use this**: you need a per-user LTV number to feed something else (bid caps for paid acquisition, prioritizing high-value accounts for support) — for a single "what's our average LTV" number, a groupby and a median/percentile split get you there without a model.

## User segmentation (clustering)

Segmentation groups users by behavioral similarity without a predefined label — useful when you suspect there are meaningfully different types of users but don't already know what defines them.

- **K-means** is the default starting point: it partitions users into *k* groups by distance to each group's center. The open question is always what *k* should be, answered with two diagnostics run together:
  - **Elbow method** — plot within-cluster variance against k; look for the point where adding another cluster stops meaningfully tightening the groups.
  - **Silhouette score** — measures how well-separated clusters are (high = tight clusters that are also far apart from each other); use it to sanity-check the elbow's choice, since the elbow point is sometimes ambiguous on its own.
- K-means relies on Euclidean distance, which assumes continuous, similarly-scaled features (session count, days active, revenue) — scale them first. When most of what describes your users is **categorical** (plan tier, signup channel, device type, referral source) rather than continuous, Euclidean distance stops making sense and K-means gives you unstable, hard-to-interpret clusters. Use **K-modes** instead (or **K-prototypes** for a mix of numeric and categorical features) — it clusters on category-match frequency rather than distance.

**When you'd actually use this**: you want to hand a product or marketing team a small number of user archetypes to design around ("power users," "trial-and-bounce," "occasional but high-value") rather than a single per-user score. Segmentation output feeds decisions like differentiated onboarding or messaging — it's descriptive, not predictive, and pairs well with the groupby-level analysis from the first section once you have cluster labels to group by.

## Which one do you actually have

A quick way to tell which of the three (if any) fits the question in front of you:

| Question shape | Use case | Model type | Watch out for |
|---|---|---|---|
| "Which segment churns most?" | Segment analysis | None — groupby | N/A |
| "Will *this* user churn in the next 30 days?" | Churn prediction | Classification | Class imbalance breaks accuracy as a metric |
| "What will *this* user spend over their lifetime?" | LTV estimation | Regression | Multicollinear features, right-skewed target |
| "What natural user types exist in our base?" | Segmentation | Clustering | Categorical features need K-modes, not K-means |

## Scope note

This doc compresses supervised and unsupervised learning into the three shapes that show up most often in product analytics work. Deliberately left out:

- Model internals and math derivations (gradient descent, entropy calculations, the linear algebra behind PCA)
- Hyperparameter tuning strategy (grid search, random search, Bayesian optimization)
- Deep learning, time series forecasting, and recommender systems — each a separate specialty with its own tradeoffs
- Full preprocessing detail (scaling, encoding, train/test splitting) — these are prerequisites to all three use cases above but aren't specific to product analytics

**Related docs**: [05-statistics-for-pa.md](05-statistics-for-pa.md) covers the statistical foundations (distributions, hypothesis testing) these models build on. [Cohort Retention Analysis](../recipes/cohort-retention/) is the no-model version of the churn/segmentation questions above — worth running first.
