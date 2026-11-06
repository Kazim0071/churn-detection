# Project State

- **Updated:** 2026-11-06
- **Project:** TuneLoop churn prediction pilot
- **Repo:** PrimeNest-Inov/churn-detection · **Jira:** Churn Detection (key `CHURN`)
- **Sprint:** 0 (setup). Sprint 1 not started.

Paste this file at the start of a review or planning session. Update it once a week, or when a decision changes.

## Goal
A weekly list of up to 500 high-risk monthly subscribers, shown in a simple web dashboard with contact details and a CSV export. Client walkthrough at the **Sprint 2 Review** (3–4 weeks after Sprint 1 starts). Brief: `PROJECT_BRIEF.md` v1.1.

## Done
- ML notebook: feature engineering + LightGBM pipeline, saved as `churn_model.joblib` (`ChurnPredictor` class)
- 6 unit tests for `ChurnPredictor`; CI on every PR (`ruff check`, `ruff format --check`, `pytest`, Python 3.14)
- `main` protected: PR required, squash merge only, required checks "Python (lint + tests)" and "Tech Lead approval" (`tl-approved` label)
- Jira: 20 backlog tickets (CHURN-1 to CHURN-20), Spike CHURN-21 (ADR 0001), Epics CHURN-22 to CHURN-25; GitHub for Jira connected
- PR #1 (CI setup): merged
- PR #2 (PR template): Tech Lead APPROVED

## In progress
| Item | Status | Next step |
|---|---|---|
| PR #2 — PR template | Approved | Add `tl-approved`, squash merge |
| PR #3 — CHURN-21, ADR 0001 | Changes requested (B1–B5) | Rebase onto `main` to drop the template commit; fix B4 and B5; reply to the Tech Lead |

## Decisions
- Monorepo: `apps/web` (Next.js), `services/api` (FastAPI), `ml/` (training + batch scoring), `docs/adr/` — ADR 0001, pending approval
- Scoring is an **offline weekly batch command**; the top 500 are frozen in a table; the API only reads that table and does not load the model
- Pilot covers **monthly** subscribers only
- Contact details (name, phone, email) shown in the dashboard and CSV; generated synthetically (KKBox has none)
- All data stays internal: Docker Compose locally, no public cloud hosting, no third-party AI services
- The pilot reads the static KKBox CSV files directly; full ingestion pipelines deferred
- `churn_model.joblib` will stop being tracked in Git, without rewriting history (CHURN-6)
- Database, contact data source and login: one ADR 0002 during Sprint 1

## Sprint 1 candidates
CHURN-2 (notebook → `.py` modules), CHURN-5 (input validation), CHURN-6 (model file out of Git + import path), CHURN-7 (monorepo setup), CHURN-1 (14 vs 30 day spike), CHURN-17 (synthetic contacts). Final choice at Sprint 1 Planning after estimates.

## Deferred (Sprint 3+)
CHURN-8, 12, 14, 16, 19, 20

## Open issues
- GitHub Gemini review bot produces no reviews on the free tier (overload, tool-calling failures). Not a required check. Optional local review with Antigravity CLI (`agy`), pasted on the PR as `[AI Review — agy]`.
- CHURN-13: the bot stays silent when a review times out.
- From PR #2 review (S1, noted on CHURN-7): add the frontend test command and an ML-changes note to the PR template.

## Working agreement
- Every change: ticket → branch from `main` (`type/CHURN-<n>-short-name`) → PR → CI green → Tech Lead review → squash merge
- **ML Projects Gem** = daily mentor for building and learning. **Tech Lead Gem** = one review per PR before merge.
- PM and Client Gems only at sprint planning and sprint review. QA Gem only for user-facing features.
- Most of each day goes to code; process stays under 30 minutes a day.
