from datetime import datetime


def normalize_date(date_string):

    try:
        return datetime.strptime(date_string, "%d.%m.%Y").strftime("%Y-%m-%d")

    except Exception:
        return date_string
