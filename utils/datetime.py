from datetime import datetime

def parse_datetime(dt_string):
    if isinstance(dt_string, datetime):
        return dt_string
    if not dt_string:
        return datetime.utcnow()
    try:
        # Try parsing with microseconds
        return datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        try:
            # Try without microseconds
            return datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return datetime.utcnow()