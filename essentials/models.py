from dataclasses import dataclass
from typing import Callable, List

from nextcord.ext.commands import AutoShardedBot

from prisma import Prisma


@dataclass
class IBot(AutoShardedBot):
    get_command_mention: Callable[[int, str], str]
    prisma: Prisma


@dataclass
class Itask:
    IGNORED_GUILDS: List[int]
    PLAYERS_ROLE: str
    AVIAL_LOG_CHANNEL: str
    AVIAL_SUBMIT_CHANNEL: str
    SUBMITTED_ROLE: str
    SUPPORT_GUILD: int
    LINEUP_SUBMIT_CHANNEL: str
    LINEUP_LOG_CHANNEL: str


Data = Itask(
    IGNORED_GUILDS=[1055597639028183080, 831166408888942623, 1054908977512714280],
    PLAYERS_ROLE="Team",
    AVIAL_LOG_CHANNEL="availability",
    AVIAL_SUBMIT_CHANNEL="submit-availability",
    SUBMITTED_ROLE="Availability Submitted",
    SUPPORT_GUILD=831166408888942623,
    LINEUP_LOG_CHANNEL="lineups",
    LINEUP_SUBMIT_CHANNEL="submit-lineups",
)
