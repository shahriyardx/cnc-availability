from datetime import datetime, timedelta
from typing import Tuple, Union

from typing_extensions import Literal

TIME = Union[datetime, Tuple[datetime, str, Tuple[int, int, int]]]

Days = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


def get_next_date(
    day: Days,
):
    now = datetime.utcnow()
    seconds = 10

    if day == "Sunday":
        seconds = 120
    if day == "Monday":
        seconds = 10
    next_date = now + timedelta(seconds=seconds)

    return next_date
