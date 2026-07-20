"""Central configuration.

Every setting is read from environment variables so the same image can run as
the API, background workers, or Kafka consumer.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "InsightFlow AI"
    environment: str = "development"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/insightflow_ai"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/3"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    ratelimit_redis_url: str = "redis://redis:6379/2"

    # JWT secret must match infra/kong/kong.yml
    jwt_secret: str = "change-me-in-prod-super-secret"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "insightflow-ai"
    access_token_expire_minutes: int = 60

    # Local file storage shared by API and workers
    local_storage_path: str = "storage_data"

    # Kafka
    kafka_enabled: bool = True
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "insightflow.events"

    # OpenAI web search
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_search_tool: str = "web_search"
    openai_request_timeout: int = 120
    openai_mock: bool = False

    # LLM backpressure
    llm_max_rpm: int = 60
    llm_max_concurrency: int = 20

    # Scraping politeness
    scrape_per_domain_rps: float = 1.0
    scrape_timeout: int = 20
    scrape_user_agent: str = "InsightFlowAIBot/1.0 (+http://localhost)"


settings = Settings()

__all__ = ["Settings", "settings"]
