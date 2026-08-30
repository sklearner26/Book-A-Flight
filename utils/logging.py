from datetime import datetime


def create_log_entry(level: str, message: str):
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }