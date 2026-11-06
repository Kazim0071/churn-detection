# ADR 0001: Monorepo layout and application stack

- **Date:** 2026-11-06
- **Status:** Proposed
- **Ticket:** CHURN-21
- **Author:** Qasim
- **Reviewer:** Tech Lead

## Context

TuneLoop needs a churn prediction pilot: a weekly list of up to 500 high-risk monthly subscribers, shown in a simple web dashboard with contact details and a CSV export. This ADR decides three things: how the code is organised (one repo or several), the backend framework and the frontend framework. The database, the source of contact data and the login mechanism are decided in separate ADRs.

The constraints that shape this decision:

- **One developer.** Every part of the system must be easy for one person to understand, run, maintain and change. There is no one else to review or hand work over to.
- **Walkthrough in 3–4 weeks.** The client accepted a working prototype at the Sprint 2 Review, so the stack must let the first end-to-end slice ship quickly.
- **Data stays internal.** All customer data is personal and must stay inside TuneLoop's infrastructure. No third-party services, external cloud hosting or third-party AI APIs may receive it.
- **The model already exists.** A LightGBM pipeline wrapped in the `ChurnPredictor` class is trained and saved as `churn_model.joblib` with Python, scikit-learn and joblib.
- **Training and serving dependencies must be separate** (Tech Lead requirement): heavy notebook and training libraries must not end up in the serving environment.
- **Existing repo:** Python ML code, unit tests and CI (ruff + pytest) are already in `PrimeNest-Inov/churn-detection`.

## Options considered

### Decision 1: repository layout

#### Option A: monorepo (one repo for ML, backend and frontend)

Pros:

- Anyone opening the repo sees the whole system in one place.
- With one developer, one repo is easier to maintain than several.
- No version mismatch between parts: when the API response shape changes, the backend and frontend change in one commit and one PR.
- Simple setup: one `git clone`, then the whole stack starts locally with one command.

Cons:

- Python and JavaScript tooling and dependencies must be managed side by side in one repo.
- CI needs path filters so that a frontend change does not run the Python jobs and the other way round.
- The repo can become heavy if model files or datasets are committed.

#### Option B: separate repos (ML, backend, frontend)

Pros:

- Each part has its own clean history.
- Suits separate teams with different permissions.
- The ML repo stays Python-only with clean tooling.
- Each part can be versioned and deployed independently.

Cons:

- Coordination cost: one API change needs two PRs in two repos, kept in sync by hand.
- Scattered for a reader: three links are needed to see the complete picture.
- Duplicated configuration: three CI pipelines, three READMEs and three environment setups to maintain.

### Decision 2: backend framework

#### Option A: FastAPI (Python)

Pros:

- Loads the saved model directly in the same process; no extra service or network hop between the API and the model.
- Fast, with native async support.
- Pydantic validates requests and responses automatically.
- Automatic interactive API docs (`/docs`).
- Widely used for ML serving, so it matches the roles the project targets.

Cons:

- No built-in authentication, admin panel or ORM; these are added and configured by the developer.
- The application structure has to be designed by the developer.

#### Option B: Django (Python)

Pros:

- Authentication, ORM and admin panel are built in.
- The admin panel is quick to set up.
- Mature and stable for large, complex applications.
- Django REST Framework is a strong toolkit for APIs.

Cons:

- Heavy and more than this project needs for model serving and a few API endpoints.
- Steeper learning curve because of its own conventions.
- Async support is less natural than in FastAPI.
- Built mainly around relational databases.

#### Option C: Express / Node.js (MERN-style)

Pros:

- Frontend and backend both in JavaScript/TypeScript, so types can be shared.
- Very large npm ecosystem.
- Good fit for real-time features (e.g. Socket.IO).

Cons:

- The model is in Python, so a Node backend would still need a separate Python service to run it: two languages and two backend services.
- Validation and error handling are written by hand.

**Rejected hybrid (Express + FastAPI):** two backends plus a frontend would mean three services for one developer, which is too much to run and maintain.

### Decision 3: frontend framework

#### Option A: React + Vite (client-side app)

Pros:

- Large ecosystem and community.
- Lightweight and flexible.
- Fast development server with Vite.
- A pure client-side app is a simple mental model.

Cons:

- Routing, data fetching and folder structure must all be chosen by the developer.
- Weak SEO by default (not relevant for an internal dashboard).
- Structure can drift as the project grows.

#### Option B: Next.js

Pros:

- File-based routing.
- Route handlers can act as a small server-side proxy to the backend, which avoids CORS issues and keeps the backend URL off the browser.
- Layouts and loading states are built in.
- The developer already uses Next.js daily, so there is little to learn.
- High industry demand.

Cons:

- More concepts: server vs client components, caching, rendering modes.
- Caching behaviour can be confusing.
- Many features (SSR, SEO, image optimisation) are more than a simple internal dashboard needs.
- Sends telemetry to Vercel by default, which must be disabled.

## Decision

1. **Monorepo.** With one developer and a 3–4 week deadline, one repo means one clone, one README, one CI pipeline, and API changes that land in a single PR. The main cost (mixed tooling) is handled with path filters in CI and clearly separated folders.
2. **FastAPI for the backend.** The model is already a Python LightGBM pipeline saved with joblib, so FastAPI can load it directly in the same process with no extra service. Pydantic gives input validation for free, which protects the model from bad input. The project is a model-serving API with a few endpoints, not a large web application, so Django would be more than needed.
3. **Next.js for the frontend.** The developer already works with Next.js, which matters most for the deadline. Route handlers proxy requests to FastAPI, which avoids CORS and keeps the backend address internal. File-based routing keeps the dashboard pages organised. All business logic stays in FastAPI; Next.js is only the UI, so logic does not spread across two places.

### Layout

```
apps/web/          Next.js dashboard (UI only)
services/api/      FastAPI backend: loads the model and serves the API
ml/                notebooks, training code, evaluation, model card
docs/adr/          architecture decision records
```

### Training vs serving dependencies

Training and serving run in separate environments with separate requirements files:

| Environment               | Libraries                                                                 |
| ------------------------- | ------------------------------------------------------------------------- |
| Training (`ml/`)          | pandas, numpy, scikit-learn, lightgbm, joblib, matplotlib, jupyter, tqdm  |
| Serving (`services/api/`) | fastapi, uvicorn, pydantic, scikit-learn, lightgbm, joblib, pandas, numpy |

Notebook and plotting libraries (jupyter, matplotlib, tqdm) stay out of serving, so the serving environment and its Docker image stay small. LightGBM and scikit-learn must be in **both** environments, because loading `churn_model.joblib` needs the same libraries the model was trained with.

### Deployment

Because data must stay internal, the whole stack (Next.js, FastAPI, database) runs with Docker Compose on internal infrastructure; for the simulation, that is the developer's machine. No public cloud hosting (Vercel, Render, AWS) is used. Only open-source libraries that run locally are used, and no data is sent to third-party AI services.

### Complexity deliberately avoided

Microservices, Kubernetes, message queues and caching layers (e.g. Redis) are not used, because the pilot does not need them. Only one database will be used (chosen in ADR 0002). Model training stays in `ml/`; the API only loads the saved model and returns predictions.

## Consequences

- **CI needs path filters** so Python and JavaScript jobs run only when their part of the repo changes.
- **Two package ecosystems** (pip and npm) are maintained in one repo.
- **Versions must match exactly.** scikit-learn and LightGBM versions are pinned and identical in the training and serving environments (currently scikit-learn==1.9.1), or the model may fail to load or give different results.
- **Preprocessing ships with the model.** Scaling and encoding stay inside the saved scikit-learn pipeline, so serving applies exactly the same transformations as training.
- **Moving `ChurnPredictor` into the monorepo changes its module path**, and joblib stores that path inside `churn_model.joblib`. The model must be re-saved or loaded with a compatible path (CHURN-6).
- **Next.js telemetry must be disabled** (`NEXT_TELEMETRY_DISABLED=1`) in every environment, to respect the data constraint (CHURN-7).
- **No hosted preview URLs.** Because nothing is deployed to public cloud, QA tests run on a clean checkout of the PR branch instead of a preview link.
- **Model files are not committed.** `churn_model.joblib` stops being tracked in Git (CHURN-6) so the repo stays light.

## Review date

After the Sprint 2 Review (client walkthrough): check whether the monorepo, FastAPI and Next.js slowed delivery anywhere or caused integration problems.
