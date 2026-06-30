# Lead Intake Service

This is a Go microservice for compliant lead intake inside InsightFlow AI.

It does **not** scrape LinkedIn. Instead, it accepts manually provided lead
records, validates LinkedIn/company URL formats, and exposes a small API that
can later be connected to:

- official partner APIs,
- user-uploaded CSV files,
- company website enrichment,
- CRM export flows,
- Kafka events.

## Why Go

Go is a strong fit for this microservice because it is simple, fast,
container-friendly, and easy to run in Docker or Kubernetes as a small API.

Recommended language split for InsightFlow AI:

- Go: lead intake, URL validation, audit, metrics, notification microservices.
- Python: AI analysis, document parsing, OCR, data science workflows.
- Node.js: browser UI and frontend tooling.
- Rust: high-performance security or parsing components when development speed is less important.

## Run Locally

```powershell
cd D:\insightflow-ai\microservices\lead-intake-service
go run .\cmd\server
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8090/health
```

Create a lead:

```powershell
Invoke-RestMethod http://localhost:8090/leads `
  -Method Post `
  -ContentType "application/json" `
  -Body '{
    "full_name": "Example Founder",
    "role": "CEO",
    "company": "ExampleCo",
    "linkedin_url": "https://www.linkedin.com/in/example-founder",
    "website_url": "https://example.com",
    "notes": "Manually added educational test lead"
  }'
```

List leads:

```powershell
Invoke-RestMethod http://localhost:8090/leads
```

## Docker

```powershell
docker build -t local/lead-intake-service:latest .
docker run --rm -p 8090:8090 local/lead-intake-service:latest
```

## Next Professional Steps

- Persist leads in PostgreSQL.
- Publish `LEAD_CREATED` events to Kafka.
- Add API auth between FastAPI and this service.
- Add CSV import for user-owned lead lists.
- Add website enrichment through company websites or licensed APIs.
- Add CRM export to HubSpot/Salesforce.
