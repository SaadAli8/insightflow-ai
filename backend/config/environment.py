from config.settings import settings


def is_development() -> bool:
    return settings.environment.lower() == "development"


def is_production() -> bool:
    return settings.environment.lower() == "production"
