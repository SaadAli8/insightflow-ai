# Lead Signal Service

Go microservice for lightweight website intelligence in InsightFlow AI.

The FastAPI lead service owns campaign orchestration, database writes,
Perplexity company discovery, and RapidAPI/Apollo people enrichment. This Go
service has one focused job: inspect discovered company websites quickly and
return structured signals that help validate the lead source.

It does not scrape LinkedIn. It only fetches public company websites submitted
by the FastAPI lead service.

## API

- `GET /health`
- `POST /signals/website`

Example:

```powershell
Invoke-RestMethod http://localhost:8090/signals/website `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"website_url":"https://example.com","company_name":"Example"}'
```

## Why Go

Go is used here for a small network-heavy service: URL validation, HTTP
fetching, response limiting, metadata extraction, and fast container startup.
Python/FastAPI stays responsible for orchestration and AI/provider APIs.

## Run

```powershell
cd D:\insightflow-ai\microservices\lead-signal-service
go run .\cmd\server
```
