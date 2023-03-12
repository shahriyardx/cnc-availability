import datetime
from typing import List, Union

from aioscheduler import TimedScheduler
from nextcord import (
    Member,
    PermissionOverwrite,
    Role,
    TextChannel,
    slash_command,
    Interaction,
    SlashOption,
)
from nextcord.ext import commands, tasks
from nextcord.utils import get

from essentials.time import Days, get_next_date
from essentials.models import Data, IBot
from prisma import Prisma


class Tasker(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.scheduler = TimedScheduler(prefer_utc=True)
        self.start_tasks.start()
        self.task_functions = {
            "Open": self.open_availability_task,
            "Close": self.close_availability_task,
            "Lineups": self.lineups_task,
        }
        self.once = False

    @slash_command(description="Simulate specific day")
    @commands.is_owner()
    async def simulate(
        self,
        interaction: Interaction,
        day: str = SlashOption(
            name="day",
            description="The day to simulate",
            required=True,
            choices={
                "Open Availability Submission": "Open",
                "Close Availability Submission": "Close",
                "Open Lineups": "Lineups",
            },
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != interaction.guild.owner.id:
            return await interaction.edit_original_message(
                content="You are not allowed to run this command."
            )

        await self.task_functions[day](simulation=True)
        await interaction.edit_original_message(content="The simulation completed")

    def get_friday_message(self, role: Role):
        return (
            f"{role.mention} please click {self.bot.get_command_mention(role.guild.id, 'submitavailability')} "
            "to submit your availability. Remember you must provide your owner a "
            "minimum of four days each week to be considered active."
        )

    def get_permissions(self, state: bool):
        permission_overwrites = PermissionOverwrite()
        permission_overwrites.send_messages = state
        permission_overwrites.view_channel = state

        return permission_overwrites

    def get_roles_array(self, roles: Union[Role, List[Role]]):
        if isinstance(roles, Role):
            return [roles]

        return roles

    async def unlockdown(self, channel: TextChannel, roles: Union[Role, List[Role]]):
        for role in self.get_roles_array(roles):
            await channel.set_permissions(
                target=role, overwrite=self.get_permissions(state=True)
            )

    async def lockdown(self, channel: TextChannel, roles: Union[Role, List[Role]]):
        for role in self.get_roles_array(roles):
            await channel.set_permissions(
                target=role, overwrite=self.get_permissions(state=False)
            )

    async def open_availability_task(self, simulation: bool = False):
        print("[=] Doing open_availability_task")
        if not simulation:
            await self.bot.prisma.lineup.delete_many()

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            PLAYERS_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            SUBMITTED_ROLE = get(guild.roles, name=Data.SUBMITTED_ROLE)
            CHANNEL = get(guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL)

            if PLAYERS_ROLE and CHANNEL and SUBMITTED_ROLE:
                await self.unlockdown(channel=CHANNEL, roles=PLAYERS_ROLE)
                await CHANNEL.send(content=self.get_friday_message(PLAYERS_ROLE))

                for member in SUBMITTED_ROLE.members:
                    await member.remove_roles(SUBMITTED_ROLE)

        if not simulation or not self.once:
            self._day_task("Open", "Friday")

    async def close_availability_task(self, simulation: bool = False):
        print("[=] close_availability_task")
        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            TEAM_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)  # `@Team`
            SUBMITTED_ROLE = get(
                guild.roles, name=Data.SUBMITTED_ROLE
            )  # `@Availability Submitted`
            SUBMIT_CHANNEL = get(
                guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL
            )  # `#submmit-availability`
            SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)  # The support server

            if TEAM_ROLE and SUBMIT_CHANNEL:
                await self.lockdown(SUBMIT_CHANNEL, roles=TEAM_ROLE)
                await SUBMIT_CHANNEL.send(
                    content="This concludes this weeks availability"
                )

                not_submitted_players: List[Member] = list()
                for member in TEAM_ROLE.members:
                    if SUBMITTED_ROLE.id not in [role.id for role in member.roles]:
                        not_submitted_players.append(member)

                if SUPPORT_GUILD:
                    TEAM_LOG_CHANNEL = get(
                        SUPPORT_GUILD.text_channels,
                        name=f"╟・{guild.name[4:].replace(' ', '-').lower()}",
                    )

                    COMMISSIONERS_ROLE = get(SUPPORT_GUILD.roles, name="Commissioners")
                    ADMINS_ROLE = get(SUPPORT_GUILD.roles, name="Admins")

                    LINEUPS_CHANNEL = get(
                        guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL
                    )
                    OWNER_ROLE = get(guild.roles, name="Owner")
                    GM_ROLE = get(guild.roles, name="General Manager")

                    await self.unlockdown(SUBMIT_CHANNEL, roles=[OWNER_ROLE, GM_ROLE])

                    submit_message = (
                        f"{' '.join([player.mention for player in not_submitted_players])} "
                        "did not submitted availability for this week. "
                        f"{COMMISSIONERS_ROLE.mention} {ADMINS_ROLE.mention}"
                    )

                    lineups_message = (
                        f"{OWNER_ROLE.mention} or {GM_ROLE.mention} please click on "
                        f"{self.bot.get_command_mention(guild.id, 'setlineups')} to enter your preliminary lineups"
                    )

                    if not_submitted_players:
                        await TEAM_LOG_CHANNEL.send(content=submit_message)

                    await LINEUPS_CHANNEL.send(content=lineups_message)

        if not simulation or not self.once:
            self._day_task("Close", "Monday", hour=17)

    async def lineups_task(self, simulation: bool = False):
        print("[=] Doing lineups_task")
        prisma = self.bot.prisma
        try:
            week = datetime.datetime.now().isocalendar().week
        except:
            week = datetime.datetime.now().isocalendar()[1]

        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)  # The support server

        COMMISSIONERS_ROLE = get(SUPPORT_GUILD.roles, name="Commissioners")
        ADMINS_ROLE = get(SUPPORT_GUILD.roles, name="Admins")

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            LINEUPS_CHANNEL = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)

            if not LINEUPS_CHANNEL:
                continue

            TEAM_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            OWNER_ROLE = get(guild.roles, name="Owner")
            GM_ROLE = get(guild.roles, name="General Manager")

            TEAM_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{guild.name[4:].replace(' ', '-').lower()}",
            )

            await self.lockdown(LINEUPS_CHANNEL, roles=[OWNER_ROLE, GM_ROLE])

            not_played_all = []
            for player in TEAM_ROLE.members:
                lined_up = await prisma.lineups.find_many(
                    where={"memberId": str(player.id), "week": week}
                )

                if len(lined_up) < 3:
                    not_played_all.append(player.mention)

            if not_played_all:
                players = ", ".join(not_played_all)

                await TEAM_CHANNEL.send(
                    f"Players {players} have not been scheduled at-least 3 matches this week."
                    f"{COMMISSIONERS_ROLE.mention} {ADMINS_ROLE.mention}"
                )

        if not simulation or not self.once:
            self._day_task("Lineups", "Monday", hour=17, minute=10)

    def _day_task(self, task: str, day: Days, hour: int = 17, minute: int = 0):
        print("[+] Crating task for", day)
        now = datetime.datetime.utcnow()
        date = get_next_date(day=day, hour=hour, minute=minute)

        if isinstance(date, datetime.datetime):
            print("[?]", day, "Task will run in ", date - now)
            self.scheduler.schedule(self.task_functions[task](), date)

    @tasks.loop(count=1)
    async def start_tasks(self):
        print("Waiting for the bot to ready")
        await self.bot.wait_until_ready()

        self._day_task("Open", "Friday")
        self._day_task("Close", "Monday")
        self._day_task("Lineups", "Monday", minute=10)

        self.scheduler.start()


def setup(bot: IBot):
    bot.add_cog(Tasker(bot))
