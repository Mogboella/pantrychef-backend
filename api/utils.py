import re

def parse_time_to_minutes(time_str: str) -> int:
    """Parse time strings like '15 mins', '1 hr 30 mins' to total minutes."""
    if not time_str:
        return 0
    time_str = time_str.lower().strip()

    # Extract hours and minutes
    hours = 0
    minutes = 0

    # Look for hours: e.g. '1 hr' or '2 hrs'
    hr_match = re.search(r"(\d+)\s*hr", time_str)
    if hr_match:
        hours = int(hr_match.group(1))

    # Look for minutes: e.g. '15 mins' or '5 min'
    min_match = re.search(r"(\d+)\s*min", time_str)
    if min_match:
        minutes = int(min_match.group(1))

    return hours * 60 + minutes
