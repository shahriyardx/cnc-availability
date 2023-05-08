from datetime import datetime, timedelta

from typing_extensions import Literal

Days = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


def get_next_date(day: Days, hour=0, minute=0, second=0):
    # Convert day name to integer representation
    day_dict = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    day_num = day_dict.get(day.lower())

    # Get current date and time
    now = datetime.utcnow()

    # Calculate the datetime for the specified day and time
    target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    target_day = (day_num - now.weekday()) % 7
    target_datetime = target_time + timedelta(days=target_day)

    # Check if the target datetime has already passed
    if target_datetime < now:
        target_datetime += timedelta(weeks=1)

    return target_datetime
