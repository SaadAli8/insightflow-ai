from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "InsightFlow Lead Service"
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/insightflow_ai"

    jwt_secret: str = "change-me-in-prod-super-secret"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "insightflow-ai"

    perplexity_api_key: str = ""
    perplexity_model: str = "sonar"
    perplexity_api_base: str = "https://api.perplexity.ai"

    rapidapi_key: str = ""
    rapidapi_apollo_host: str = "apollo-leads-from-website.p.rapidapi.com"
    rapidapi_timeout: int = 45
    lead_people_per_company: int = 5
    lead_enrichment_delay_seconds: float = 10.0

    lead_signal_service_url: str = "http://lead-signal-service:8090"
    lead_signal_timeout: int = 30

    main_api_base: str = "http://api:8000"
    submit_website_jobs: bool = True


settings = Settings()
