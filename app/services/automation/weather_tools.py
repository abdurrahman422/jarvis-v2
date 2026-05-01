from app.services.offline_guard import block_internet


def current_weather(text: str, default_city: str = "") -> str:
    return block_internet("weather")
