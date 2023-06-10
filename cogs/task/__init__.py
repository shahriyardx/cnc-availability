import datetime
import os
from typing import List

from aioscheduler import TimedScheduler
from nextcord import Interaction, Member, SlashOption, slash_command
from nextcord.ext import commands, tasks
from nextcord.utils import get

from cogs.commands.utils import append_into_ir
from essentials.models import Data, IBot
from essentials.time import get_next_date
from essentials.utils import get_team_name
from utils.gspread import DataSheet

from .utils import get_week, lockdown, unlockdown


class Tasker(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.scheduler = TimedScheduler(prefer_utc=True)
        self.start_tasks.start()
        self.roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")

    @slash_command(description="Simulate specific tasks")
    async def simulate(
        self,
        interaction: Interaction,
        task: str = SlashOption(
            description="Select task to simulate",
            choices={
                "Open Availability": "Open Availability",
                "Close Availability and Open Lineups Submit and Edit": (
                    "Close Availability and Open Lineups Submit and Edit"
                ),
                "Close Lineup Submit": "Close Lineup Submit",
                "Close Lineup Edit": "Close Lineup Edit",
            },
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != interaction.guild.owner_id:
            return await interaction.edit_original_message(
                content="You are allowed to simulate tasks"
            )

        t = {
            "Open Availability": self.open_availability_task,
            "Close Availability and Open Lineups Submit and Edit": self.close_availability_task,
            "Close Lineup Submit": self.close_lineup_submit,
            "Close Lineup Edit": self.close_lineup_channel,
        }

        task_func = t[task]

        try:
            await task_func(True)
        except Exception as e:
            return await interaction.edit_original_message(content=f"**Error**: {e}")

        await interaction.edit_original_message(content="Simulation succeded.")

    async def open_availability_task(self, simulate: bool = False):
        # Runs Friday 5 PM UTC
        # Opens availability

        # Delete all previous lineups and availability
        # Close any submission and edition of lineups
        print("[+] START open_availability_task")

        if not simulate:
            await self.bot.prisma.lineups.delete_many()
            await self.bot.prisma.lineup.delete_many()
            await self.bot.prisma.availability.delete_many()

        settings = await self.bot.prisma.settings.find_first()

        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": False,
                "can_submit_lineups": False,
            },
        )

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            PLAYERS_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            SUBMITTED_ROLE = get(guild.roles, name=Data.SUBMITTED_ROLE)
            IR_ROLE = get(guild.roles, name="IR")
            AVIAL_SUBMIT_CHANNEL = get(
                guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL
            )

            if PLAYERS_ROLE and AVIAL_SUBMIT_CHANNEL and SUBMITTED_ROLE:
                message = (
                    f"{PLAYERS_ROLE.mention} please click {self.bot.get_command_mention('submitavailability')} "
                    "to submit your availability. Remember you must provide your owner a "
                    "minimum of four days each week to be considered active."
                )

                await unlockdown(channel=AVIAL_SUBMIT_CHANNEL, roles=PLAYERS_ROLE)
                await AVIAL_SUBMIT_CHANNEL.send(content=message)

                for member in SUBMITTED_ROLE.members:
                    try:
                        await member.remove_roles(
                            SUBMITTED_ROLE, IR_ROLE, reason="Open Availability"
                        )
                    except Exception as e:
                        print(e)

        print("[+] END open_availability_task")
        if not simulate:
            self.start_task(
                self.open_availability_task, get_next_date("Friday", hour=17)
            )

    async def close_availability_task(self, simulate: bool = False):
        # Runs Monday 5 PM UTC
        # Closes availability submission
        # Open Lineups submit

        SUPPORT_GUILD = self.bot.SUPPORT_GUILD
        print("[+] START close_availability_task")

        # Open lineups submit and edit
        settings = await self.bot.prisma.settings.find_first()
        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": True,
                "can_submit_lineups": True,
            },
        )

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            TEAM_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            LINEUPS_CHANNEL = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)

            if not TEAM_ROLE or not LINEUPS_CHANNEL:
                continue

            # Lockdown submit channel - No more availability submission
            submit_availability_channel = get(
                guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL
            )
            await submit_availability_channel.send(
                content="This concludes this weeks availability"
            )
            await lockdown(submit_availability_channel, roles=TEAM_ROLE)

            # Check who did not submit availability
            # Report back in CNC Discord
            playable_members: List[Member] = list()

            for member in TEAM_ROLE.members:
                has_ir = get(member.roles, name="IR")
                if has_ir:
                    continue

                avail = await self.bot.prisma.availability.find_first(
                    where={"member_id": member.id}
                )

                if not avail:
                    await append_into_ir(self.bot, guild, member, self.roster_sheet, 0)
                # Else already got into ir

            TEAM_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            for member in TEAM_ROLE.members:
                has_ir = get(member.roles, name="IR")
                if not has_ir:
                    playable_members.append(member)

            if not SUPPORT_GUILD:
                continue

            cnc_team_channel = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{get_team_name(guild.name)}",
            )

            # Ask Owner and General Manager to submit for lineups
            OWNER_ROLE = get(guild.roles, name="Owner")
            GM_ROLE = get(guild.roles, name="General Manager")

            if len(playable_members) < 13:
                await cnc_team_channel.send(
                    content=(
                        f"The {get_team_name(guild.name)} need {13 - len(playable_members)} ECU "
                        f"players this week {OWNER_ROLE.mention} {GM_ROLE.mention}"
                    )
                )

            if not OWNER_ROLE or not GM_ROLE:
                continue

            await unlockdown(LINEUPS_CHANNEL, roles=[OWNER_ROLE, GM_ROLE])
            await LINEUPS_CHANNEL.send(
                content=(
                    f"{OWNER_ROLE.mention} or {GM_ROLE.mention} please click on "
                    f"{self.bot.get_command_mention('setlineups')} to enter your preliminary lineups"
                )
            )

        print("[+] STOP close_availability_task")
        if not simulate:
            self.start_task(
                self.close_availability_task, get_next_date("Monday", hour=17)
            )

    async def close_lineup_submit(self, simulate: bool = False):
        # Runs Tuesday 4 AM
        # Keeps the lineup edit open

        print("[+] START close_lineup_submit")
        settings = await self.bot.prisma.settings.find_first()
        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": True,
                "can_submit_lineups": False,
            },
        )

        SUPPORT_GUILD = self.bot.SUPPORT_GUILD

        # Check matches scheduled
        week = get_week()
        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            TEAM_ROLE = get(guild.roles, name=Data.PLAYERS_ROLE)
            LINEUPS_CHANNEL = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)

            if LINEUPS_CHANNEL:
                await LINEUPS_CHANNEL.send(
                    ":information_source: Lineup submission has been closed. Only editing old lneups are open now."
                )

            not_played_minimum_3 = []
            for player in TEAM_ROLE.members:
                lined_up = await self.bot.prisma.lineups.find_many(
                    where={"member_id": str(player.id), "week": week}
                )
                has_ir = get(player.roles, name="IR")

                if len(lined_up) < 3 and not has_ir:
                    not_played_minimum_3.append(player.mention)

            if not_played_minimum_3:
                players = ", ".join(not_played_minimum_3)

                TEAM_CHANNEL = get(
                    SUPPORT_GUILD.text_channels,
                    name=f"╟・{get_team_name(guild.name)}",
                )

                if TEAM_CHANNEL:
                    await TEAM_CHANNEL.send(
                        content=(
                            f"Players {players} have not been scheduled at-least 3 matches this week."
                            f"{get(SUPPORT_GUILD.roles, name='Commissioners').mention} "
                            f"{get(SUPPORT_GUILD.roles, name='Admins').mention}"
                        )
                    )

        print("[+] STOP close_lineup_submit")
        if not simulate:
            self.start_task(self.close_lineup_submit, get_next_date("Tuesday", hour=4))

    async def close_lineup_channel(self, simulate: bool = False):
        # Runs Friday 2 AM UTC
        # Closes the lineup channel
        # Checks who did not play 3 matches

        # Close lineup submit and edit both again
        print("[+] START close_lineup_channel")
        settings = await self.bot.prisma.settings.find_first()
        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": False,
                "can_submit_lineups": False,
            },
        )

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            LINEUPS_CHANNEL = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)
            OWNER_ROLE = get(guild.roles, name="Owner")
            GM_ROLE = get(guild.roles, name="General Manager")

            if LINEUPS_CHANNEL and OWNER_ROLE and GM_ROLE:
                await LINEUPS_CHANNEL.send(
                    ":information_source: Lineup editing has been closed for this week."
                )

                await lockdown(LINEUPS_CHANNEL, roles=[OWNER_ROLE, GM_ROLE])

        print("[+] STOP close_lineup_channel")
        if not simulate:
            self.start_task(self.close_lineup_channel, get_next_date("Friday", hour=2))

    def start_task(self, task_func, time):
        now = datetime.datetime.utcnow()
        delta = time - now

        print(f"[T] Task scheduled after {delta} {task_func.__name__}")
        self.scheduler.schedule(task_func(), time)

    @tasks.loop(count=1)
    async def start_tasks(self):
        await self.bot.wait_until_ready()

        mode = os.environ["MODE"]
        print(f"Mode: {mode}")

        if mode in ["dev", "devstart"]:
            # Fake times
            now = datetime.datetime.utcnow()
            f17 = now + datetime.timedelta(seconds=3)
            m17 = f17 + datetime.timedelta(seconds=30)
            t4 = m17 + datetime.timedelta(seconds=30)
            f2 = t4 + datetime.timedelta(seconds=30)

            if mode == "devstart":
                print("[+] Devstart mode")
                self.start_task(self.open_availability_task, f17)
                self.start_task(self.close_availability_task, m17)
                self.start_task(self.close_lineup_submit, t4)
                self.start_task(self.close_lineup_channel, f2)
        else:
            # Real times
            f17 = get_next_date("Friday", hour=17)
            m17 = get_next_date("Monday", hour=17)
            t4 = get_next_date("Tuesday", hour=4)
            f2 = get_next_date("Friday", hour=2)

            self.start_task(self.open_availability_task, f17)
            self.start_task(self.close_availability_task, m17)
            self.start_task(self.close_lineup_submit, t4)
            self.start_task(self.close_lineup_channel, f2)

        self.scheduler.start()


def setup(bot: IBot):
    bot.add_cog(Tasker(bot))
