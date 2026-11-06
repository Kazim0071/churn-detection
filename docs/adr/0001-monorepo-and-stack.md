# ADR 0001: Monorepo layout and application stack

- **Date:** 2026-11-06
- **Status:** Proposed
- **Ticket:** CHURN-21
- **Author:** Qasim
- **Reviewer:** Tech Lead

## Context

TuneLoop needs a churn prediction pilot: a weekly list of up to 500 high-risk monthly subscribers, shown in a simple web dashboard with contact details and a CSV export. This ADR decides how the code is organised (one repo or several), the backend framework, the frontend framework, how the browser reaches the backend, and where the model runs. The database, the source of contact data and the login mechanism are decided in separate ADRs.

The constraints that shape this decision:

- **One developer.** Every part of the system must be easy for one person to understand, run, maintain and change. There is no one else to review or hand work over to.
- **Walkthrough in 3–4 weeks.** The client accepted a working prototype at the Sprint 2 Review, so the stack must let the first end-to-end slice ship quickly.
- **Data stays internal.** All customer data is personal and must stay inside TuneLoop's infrastructure. No third-party services, external cloud hosting or third-party AI APIs may receive it.
- **Batch, not real-time.** The output is a list produced once a week. Nobody asks for a prediction on demand, so the model only needs to run once per week, not on every request.
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

The backend does not run the model (see "Where the model runs" below). It reads the latest weekly scores from the database, serves the high-risk list and streams the CSV export.

#### Option A: FastAPI (Python)

Pros:

- Same language as the weekly scoring job and the ML code, so the whole backend side is one language and one package manager (pip).
- Pydantic validates requests and responses automatically.
- Automatic interactive API docs (`/docs`).
- `StreamingResponse` makes the CSV export simple.
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

- Heavy and more than this project needs for a few read-only endpoints and a CSV export.
- Steeper learning curve because of its own conventions.
- Async support is less natural than in FastAPI.

#### Option C: Express / Node.js (MERN-style)

Pros:

- Frontend and backend both in JavaScript/TypeScript, so types can be shared.
- Very large npm ecosystem.
- Good fit for real-time features (e.g. Socket.IO).

Cons:

- The scoring job must be Python anyway (the model is a Python pipeline), so an Express API would add a second backend language. Database access and table definitions could not be shared between the job and the API.
- Validation and error handling are written by hand.

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
- `rewrites` can forward `/api/*` to the backend with one line of config, so the browser only ever talks to one origin (see below).
- Layouts and loading states are built in.
- The developer already uses Next.js daily, so there is little to learn.
- High industry demand.

Cons:

- More concepts: server vs client components, caching, rendering modes.
- Caching behaviour can be confusing.
- Many features (SSR, SEO, image optimisation) are more than a simple internal dashboard needs.
- Sends telemetry to Vercel by default, which must be disabled.

#### How the browser reaches the backend

##### Option (a): Next.js `rewrites`

One rule in `next.config` forwards `/api/:path*` to FastAPI. No proxy code is written.

Pros:

- **Same origin.** The browser only sees the dashboard's address, so there is no CORS configuration at all.
- **Login stays simple.** Whatever login mechanism ADR 0003 picks, a session cookie works same-origin without credentialed CORS or `SameSite` workarounds.
- **FastAPI is not exposed.** Only the Next.js container publishes a port; FastAPI is reachable only inside the Docker Compose network (`http://api:8000`).
- **The CSV export streams through** the rewrite without being buffered in proxy code.
- No code to write, test or maintain.

Cons:

- Every API request takes one extra hop through the Next.js server (negligible for an internal dashboard with a few users).
- The rewrite destination is read when the app is built, so the backend address (`API_URL`) must be passed as a build argument.
- Large or slow responses are subject to the Next.js proxy timeout (not a concern for a 500-row CSV).

##### Option (b): browser calls FastAPI directly, CORS limited to the dashboard's address

Pros:

- No extra hop; the backend address can change without rebuilding the frontend.

Cons:

- FastAPI must be reachable from users' browsers, so a second service is exposed on the network.
- CORS must be configured and kept correct in every environment.
- Cookie-based login across two origins needs credentialed CORS and careful cookie settings, which is extra work and easy to get wrong.

## Decision

1. **Monorepo.** With one developer and a 3–4 week deadline, one repo means one clone, one README, one CI pipeline, and API changes that land in a single PR. The main cost (mixed tooling) is handled with path filters in CI and clearly separated folders.
2. **FastAPI for the backend.** The scoring job and ML code are Python, so a Python API keeps the backend side in one language and lets the job and the API share database code. Pydantic validates input and output, `/docs` documents the API, and the CSV export is a simple streaming response. The API serves a few endpoints, not a large web application, so Django would be more than needed.
3. **Next.js for the frontend, reaching FastAPI through `rewrites`.** The developer already works with Next.js, which matters most for the deadline. A single rewrite rule (`/api/:path*` → `API_URL`) puts the dashboard and API on one origin: no CORS, simple same-origin login cookies, and FastAPI never exposed outside the Compose network. No route handlers or proxy code are written. Next.js is only the UI; all business logic stays in FastAPI.
4. **The model runs in a weekly batch job, not in the API.** The output is a weekly list, so loading the model in the API would keep a large model and heavy libraries in a long-running service for nothing. A scoring job runs once a week, loads `churn_model.joblib`, scores all monthly subscribers and writes the scores to the database. The API only reads them.
5. **`ChurnPredictor` lives at `churn_ml.predictor.ChurnPredictor`.** `ml/` becomes an installable package named `churn_ml`. Training and the scoring job both import the class from this one path, and the model is re-saved after the move so the path stored inside `churn_model.joblib` matches (CHURN-6).

### Layout

```
apps/web/                     Next.js dashboard (UI only, rewrites /api/* to FastAPI)
services/api/                 FastAPI: reads weekly scores from the database, serves the list and CSV
ml/                           installable package `churn_ml`
  pyproject.toml              base deps (scoring) + [train] extra
  src/churn_ml/predictor.py   ChurnPredictor
  src/churn_ml/score.py       weekly scoring job (python -m churn_ml.score)
  notebooks/                  experiments, evaluation, model card
docs/adr/                     architecture decision records
```

### Where the model runs

```
weekly:     scoring job → loads churn_model.joblib → scores subscribers → writes scores to DB
on demand:  browser → Next.js (/api/* rewrite) → FastAPI → reads latest scores from DB
```

The scoring job runs as a one-off Docker Compose service (`docker compose run --rm scoring`), started once a week by a cron entry on the host. No scheduler service is added.

### Training vs serving dependencies

Three environments, each with only what it needs:

| Environment                          | Libraries                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------- |
| Training (`pip install ./ml[train]`) | pandas, numpy, scikit-learn, lightgbm, joblib + matplotlib, jupyter, tqdm |
| Scoring job (`pip install ./ml`)     | pandas, numpy, scikit-learn, lightgbm, joblib, database driver (ADR 0002) |
| API (`services/api/`)                | fastapi, uvicorn, pydantic, database driver (ADR 0002)                    |

Notebook and plotting libraries exist only in the `[train]` extra. The API has no ML libraries at all, so its Docker image stays small and it never loads the model. scikit-learn and LightGBM are pinned once, in the base dependencies of `ml/pyproject.toml`, so training and scoring always use the same versions.

### Deployment

Because data must stay internal, the whole stack (Next.js, FastAPI, scoring job, database) runs with Docker Compose on internal infrastructure; for the simulation, that is the developer's machine. Only the Next.js port is published. No public cloud hosting (Vercel, Render, AWS) is used. Only open-source libraries that run locally are used, and no data is sent to third-party AI services.

### Complexity deliberately avoided

Microservices, Kubernetes, message queues, caching layers (e.g. Redis) and workflow schedulers (e.g. Airflow) are not used, because the pilot does not need them. Only one database will be used (chosen in ADR 0002). Model training stays in `ml/`; the scoring job writes scores; the API only reads them.

## Consequences

- **CI needs path filters** so Python and JavaScript jobs run only when their part of the repo changes.
- **Two package ecosystems** (pip and npm) are maintained in one repo.
- **Versions must match exactly.** scikit-learn and LightGBM are pinned in the base dependencies of `ml/pyproject.toml` (currently scikit-learn==1.9.1; LightGBM pinned to the version the model was trained with), so training and scoring cannot drift apart.
- **Preprocessing ships with the model.** Scaling and encoding stay inside the saved scikit-learn pipeline, so scoring applies exactly the same transformations as training.
- **The model must be re-saved under the new import path.** joblib stores the class path inside `churn_model.joblib`; after the move it must be `churn_ml.predictor.ChurnPredictor`, and the model is re-saved from that path (CHURN-6).
- **Scores are only as fresh as the last weekly run.** The dashboard shows when the scores were produced, and a failed run must be visible (job exit code and a run timestamp in the database).
- **`API_URL` is a build argument for the web image**, because Next.js reads the rewrite destination at build time.
- **FastAPI has no CORS configuration** and is not reachable from outside the Compose network.
- **Next.js telemetry must be disabled** (`NEXT_TELEMETRY_DISABLED=1`) in every environment, to respect the data constraint (CHURN-7).
- **No hosted preview URLs.** Because nothing is deployed to public cloud, QA tests run on a clean checkout of the PR branch instead of a preview link.
- **Model files are not committed.** `churn_model.joblib` stops being tracked in Git (CHURN-6) so the repo stays light.

## Review date

After the Sprint 2 Review (client walkthrough): check whether the monorepo, FastAPI, Next.js rewrites and the weekly batch job slowed delivery anywhere or caused integration problems.
