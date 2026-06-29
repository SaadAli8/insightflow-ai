# InsightFlow AI (local, Docker)

An enterprise-style AI analysis platform that runs **entirely on your machine**
with Docker. Users submit website URLs or upload files; background workers do the
heavy lifting (fetching, OCR, AI analysis) and results show up via the API.

**Core rule:** the API never does heavy work. It creates a job and returns
immediately. Workers process jobs in the background, gated by **external rate
limits, not your CPU** (OpenAI requests/minute + per-domain politeness).

Website analysis uses **OpenAI's web search tool** (the "search API of ChatGPT")
so the model researches the live site — no custom crawler needed.

---

## Architecture

```
                   ┌───────────┐
  User / curl ───► │   Kong    │  JWT validation + rate limiting (edge)
                   └─────┬─────┘
                         ▼
                   ┌───────────┐
                   │  FastAPI  │  auth, validate, CREATE JOB, return 202
                   └─────┬─────┘
        enqueue task     │   publish event
        (Redis broker)   │   (Kafka)
            ┌────────────┼─────────────┐
            ▼            ▼             ▼
   ┌──────────────┐ ┌──────────┐ ┌──────────────────┐
   │ worker-website│ │worker-file│ │    Kafka         │
   │ (gevent, I/O) │ │(prefork,  │ │  insightflow.events │
   └──────┬────────┘ │ CPU/OCR) │ └────────┬─────────┘
          │          └────┬─────┘          ▼
          └──────┬────────┘         ┌──────────────┐
                 ▼                  │   consumer   │ → notifications
         ┌──────────────┐          └──────────────┘
         │  worker-ai   │  ◄── Redis token bucket (LLM backpressure)
         │ (gevent)     │ ───► OpenAI (web search + analysis)
         └──────┬───────┘
                ▼
        PostgreSQL (results)   ./backend/storage_data (uploads + extracted text)
```

| Layer        | Tech              | Job                                            |
|--------------|-------------------|------------------------------------------------|
| Gateway      | Kong (DB-less)    | JWT validation, rate limiting, routing         |
| API          | FastAPI           | Auth, validation, **create job & return**      |
| Broker/Cache | Redis             | Celery broker + rate-limit token buckets       |
| Workers      | Celery (3 queues) | website (I/O) · file (CPU/OCR) · ai (rate-gated)|
| Events       | Kafka (KRaft)     | `insightflow.events` → notifications/audit        |
| Database     | PostgreSQL        | System of record                               |
| Storage      | Local filesystem  | Uploaded files + extracted text in `backend/storage_data/` |
| AI           | OpenAI web search | Website research + file analysis               |
| Monitoring   | Prometheus+Grafana+Flower | Metrics & queue visibility            |

---

## Quick start

### 1. Prereqs
- Docker + Docker Compose
- An OpenAI API key

### 2. Configure
```bash
Copy-Item backend/.env.example backend/.env
# edit backend/.env and set OPENAI_API_KEY=sk-...
```

### 3. Run everything
```bash
docker compose --env-file backend/.env up -d --build
```
First build takes a few minutes (installs Tesseract/Poppler). Then:

| Service            | URL                                   |
|--------------------|---------------------------------------|
| **React console**  | http://localhost:5173                 |
| **Gateway (use)**  | http://localhost:8081/api/v1          |
| Konga (Kong UI)    | http://localhost:1337                 |
| FastAPI docs       | http://localhost:8000/docs            |
| Flower (Celery)    | http://localhost:5555                 |
| Prometheus         | http://localhost:9090                 |
| Grafana            | http://localhost:3001 (admin/admin)   |

### 4. Seed demo data (100 users + sample jobs)
```bash
docker compose --env-file backend/.env exec api python -m scripts.seed
# more load:
docker compose --env-file backend/.env exec api python -m scripts.seed --users 100 --enqueue 10 --files 5
# professional load demo (100 users + 100 website jobs enqueued):
docker compose --env-file backend/.env exec api python -m scripts.seed_load_demo --reset
```

The seeded admin dashboard login is `user000@example.com` / `password123`.
That account can see all seeded jobs in the React console.

### Demo walkthrough for managers

1. Open the React console: `http://localhost:5173`.
2. Login with `user000@example.com` / `password123`.
3. Show the top summary cards:
   - Users: seeded demo accounts.
   - Jobs: website/file analysis jobs created by the API.
   - Processing: work currently running in Celery.
   - Complete/Failed: final worker outcomes.
4. Show the Users panel on the right to prove the 100 seeded users exist.
5. Show the Jobs table to prove 100 website jobs were queued and processed in
   background workers.
6. Use the Notifications panel as latest activity only. It shows the newest
   events and includes a clear button so old seed-run notifications do not
   clutter the demo.
7. Open Flower (`http://localhost:5555`) to show Celery workers and queues.
8. Open Konga/Kong Admin API to show gateway routing and rate limiting.
9. Open the local `backend/storage_data/` folder to show uploaded files and extracted
   text stored in the project directory.
10. Open Prometheus/Grafana for monitoring.

---

## Try it end-to-end (through Kong)

### Browser UI

Open http://localhost:5173 and use the console to register/login, submit a
website, upload a file, watch job status, and view completion notifications.
The React app calls `/api/v1/...`; Vite proxies those requests to Kong.

### API calls

```bash
# 1. Register
curl -X POST http://localhost:8081/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"secret123"}'

# 2. Login -> get JWT
TOKEN=$(curl -s -X POST http://localhost:8081/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"secret123"}' | jq -r .access_token)

# 3. Submit a website (returns 202 + job_id instantly)
curl -X POST http://localhost:8081/api/v1/websites \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"url":"https://fastapi.tiangolo.com"}'

# 4. Upload a file
curl -X POST http://localhost:8081/api/v1/files/upload \
  -H "Authorization: Bearer $TOKEN" -F "upload=@/path/to/report.pdf"

# 5. Poll job status, then fetch the result
curl http://localhost:8081/api/v1/jobs -H "Authorization: Bearer $TOKEN"
curl http://localhost:8081/api/v1/jobs/<job_id>/result -H "Authorization: Bearer $TOKEN"

# 6. Notifications (created by the Kafka consumer)
curl http://localhost:8081/api/v1/notifications -H "Authorization: Bearer $TOKEN"
```

> PowerShell users: use `Invoke-RestMethod` or just use the Swagger UI at
> http://localhost:8000/docs (click "Authorize" and paste the token).

---

## How backpressure works (the important part)

Heavy work is bounded by **external** limits, enforced with a Redis token bucket
([backend/workers/ratelimit.py](backend/workers/ratelimit.py)):

- **OpenAI:** all `worker-ai` containers share one global bucket of
  `LLM_MAX_RPM` requests/minute. If the budget is spent, the task re-queues
  itself with the exact wait time — it never exceeds the provider limit. Excess
  jobs just wait in the queue.
- **Scraping:** each domain has its own bucket (`SCRAPE_PER_DOMAIN_RPS`), so a
  flood of jobs for one site stays polite.

Concurrency is separately capped by each worker's `-c` flag. Tune both in
`backend/.env` and `docker-compose.yml`.

### Scaling locally
```bash
docker compose --env-file backend/.env up -d --scale worker-ai=3 --scale worker-website=4 --scale worker-file=2
```
The shared Redis bucket keeps total OpenAI rate constant no matter how many
`worker-ai` replicas you run.

---

## Push the image to Docker Hub

The whole stack uses **one image**. Build and push it:

```bash
# log in once
docker login

# build + push (replace yourname)
docker build -t yourname/insightflow-ai:latest backend
docker push yourname/insightflow-ai:latest
```

Or via Make:
```bash
make push DOCKERHUB_USER=yourname
```

To run from the pushed image instead of building locally, set `DOCKERHUB_USER`
so compose uses `yourname/insightflow-ai:latest`:
```bash
DOCKERHUB_USER=yourname docker compose --env-file backend/.env up -d
```

---

## Windows / PowerShell notes
- `make` may not be installed — run the `docker compose ...` commands directly.
- Copy env file: `Copy-Item backend/.env.example backend/.env`
- Easiest way to test the API: the Swagger UI at http://localhost:8000/docs.

---

## Project layout

```
frontend/               React console
backend/                backend runtime files
  app/                  FastAPI application
  workers/              Celery workers
  consumers/            Kafka notification consumer
  scripts/              demo seed scripts
  kong/                 Kong gateway config
  monitoring/           Prometheus and Grafana config
  storage_data/         uploads and extracted text
  Dockerfile            backend image for api/workers/consumer
  requirements.txt      Python dependencies
  .env                  local backend environment
docker-compose.yml      full local stack
Makefile                convenience commands
```

---

## Useful commands
```bash
docker compose --env-file backend/.env logs -f worker-ai
docker compose --env-file backend/.env logs -f consumer
docker compose --env-file backend/.env ps
docker compose --env-file backend/.env down -v
```

## Kubernetes HPA / PDB

Kubernetes starter manifests live in `k8s/`. They add Deployments, Services,
HorizontalPodAutoscalers, and PodDisruptionBudgets for the API, frontend, and
workers.

```powershell
docker build -t local/insightflow-ai:latest backend
docker build -t local/insightflow-ai-ui:latest frontend
kubectl config get-contexts
kubectl config use-context docker-desktop
kubectl apply -f k8s/
kubectl -n insightflow-ai get pods,svc,hpa,pdb
kubectl -n insightflow-ai port-forward svc/frontend 5173:5173
```

If `kubectl config get-contexts` is empty, enable Kubernetes in Docker Desktop
or run `minikube start --driver=docker` and use the `minikube` context.

See `k8s/README.md` for Minikube notes and cleanup commands.

## Local operations tools

- **Flower** (`http://localhost:5555`) shows Celery queues, running tasks,
  completed tasks, failed tasks, retries, and worker health. Use it to prove
  website/file analysis is happening in background workers instead of inside
  the API request.
- **Konga** (`http://localhost:1337`) is a local community UI for Kong's Admin
  API. Add a Kong connection in Konga with Admin URL `http://kong:8001` from
  inside Docker, or `http://localhost:8001` if Konga asks from your browser.
  Konga is useful for a visual demo, but this project still keeps Kong's real
  configuration in `backend/kong/kong.yml`.
- **Prometheus** (`http://localhost:9090`) collects time-series metrics from
  the running services. In this stack it scrapes FastAPI/Kong metrics so you can
  inspect request count, latency, error rate, and service health.
- **Grafana** (`http://localhost:3001`) is the dashboard layer for system
  metrics. It reads from Prometheus and is where production-style charts would
  live: request rate, latency, worker health, queue depth, and error trends.
- **Local storage** (`backend/storage_data/`) stores uploaded files and extracted text
  directly in the project directory. Docker mounts this folder into the API and
  worker containers so each service can read the same files.

## Notes / production gaps (intentionally out of scope for local)
- DB tables are auto-created on startup; production should use Alembic migrations.
- Single-node Kafka/Redis/Postgres; production uses clusters + managed services.
- Add an SSRF guard on submitted URLs before exposing this publicly.
- Replace `gevent + psycopg2` blocking DB calls with `psycogreen` if you push
  very high website-worker concurrency.
