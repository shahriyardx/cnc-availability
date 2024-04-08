from datetime import datetime
from pytz import timezone


def can_submit(day):
    now = datetime.now(tz=timezone("EST"))
    weekday = now.weekday()

    days = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    if weekday == 0:
        return True

    if weekday > 3:
        return None

    if weekday != days[day]:
        return False

    last_time = datetime(
        now.year, now.month, now.day, 20, 30, 0, 0, tzinfo=timezone("EST")
    )
    return now < last_time


print(can_submit("Tuesday"))
print(can_submit("Wednesday"))
print(can_submit("Thursday"))