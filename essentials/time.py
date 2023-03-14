from datetime import datetime, timedelta
from typing import Optional, Tuple, Union

from typing_extensions import Literal

TIME = Union[datetime, Tuple[datetime, str, Tuple[int, int, int]]]

Days = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

day_map = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def get_next_date(
    day: Days,
    hour: int = 17,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    default_now: Optional[datetime] = None,
):
    now = default_now or datetime.utcnow()

    days_left = day_map[day] - now.weekday()
    if days_left <= 0:  # Target day already happened this week
        days_left += 7

    next_date = now.replace(
        hour=hour, minute=minute, second=second, microsecond=microsecond
    ) + timedelta(days=days_left)

    return next_date
