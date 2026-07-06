# CLAUDE.md

Product analytics playbook — runnable recipes, theory guides, and real-service case studies. Conventions for AI-assisted contributions:

## Recipe conventions
- Folder shape: `README.md + analysis.py + requirements.txt (pinned) + data/ (<1MB) + assets/ (output PNGs)`
- README flow: overview → data (with reproduction path) → stack → how to run → analysis steps → results (embedded images) → interpretation → limitations → references
- English only. Python env via `uv`: `uv venv .venv && uv pip install -r requirements.txt`
- **The merge bar is one question: does it run right after cloning?** Any change to a recipe requires actually rerunning it and regenerating assets/ before commit

## Case-study rules
- Real deployed services only. Publish aggregates, or event-level tables ONLY when fully anonymized (P-code identities via one-way hash; no links, free text, emails, or raw IDs) — never anything joinable back to a person
- Anonymize people as P01… codes; never commit a mapping back to identities
- State limitations honestly (sample size, time window, significance)

## Data rules
- Measured data only — no fabrication, estimation, or placeholders
- Synthetic data must be seed-pinned for reproducibility
- Committed data <1MB per recipe; larger via fetch script + source link

## Link rules
- Verify external links (curl 200) before adding
- New recipe/case study → add a row to the root README table
