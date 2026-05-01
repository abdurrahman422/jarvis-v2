from app.services.offline_guard import block_internet


_last_result: str = "Speed test is disabled in offline mode."


def run_speedtest(_: str) -> str:
    return block_internet("speed test")


def last_speedtest(_: str) -> str:
    return _last_result
