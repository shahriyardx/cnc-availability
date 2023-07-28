import datetime
import json
import os
from typing import List, Optional

import nextcord
from aioscheduler import TimedScheduler
from nextcord import Interaction, Member, SlashOption, slash_command
from nextcord.ext import commands, tasks
from nextcord.utils import get

from cogs.commands.utils import append_into_ir
from essentials.models import Data, IBot
from essentials.time import get_next_date
from essentials.utils import get_team_name
from utils.gspread import DataSheet

from .stats import get_all_team_data
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
                "Calculate Games Played": "Calculate Games Played",
            },
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in [interaction.guild.owner_id, 696939596667158579]:
            return await interaction.edit_original_message(
                content="You are allowed to simulate tasks"
            )

        t = {
            "Open Availability": self.open_availability_task,
            "Close Availability and Open Lineups Submit and Edit": self.close_availability_task,
            "Close Lineup Submit": self.close_lineup_submit,
            "Close Lineup Edit": self.close_lineup_channel,
            "Calculate Games Played": self.calculate_gp,
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
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.open_availability_task, get_next_date("Friday", hour=17)
                )

            return

        if not simulate:
            await self.bot.prisma.playerlineup.delete_many()
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
            ECU_ROLE = get(guild.roles, name="ECU")

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

                for member in IR_ROLE.members:
                    try:
                        await member.remove_roles(IR_ROLE, reason="Open Availability")
                    except Exception as e:
                        print(e)

                for member in ECU_ROLE.members:
                    try:
                        await member.kick()
                    except:
                        try:
                            await member.remove_roles(ECU_ROLE)
                        except:
                            pass

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
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.open_availability_task, get_next_date("Friday", hour=17)
                )

            return

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

            ECU_ROLE = get(guild.roles, name="ECU")
            for member in ECU_ROLE.members:
                try:
                    await member.kick()
                except: # noqa
                    try:
                        await member.remove_roles(ECU_ROLE)
                    except: # noqa
                        pass

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

                if not avail and not self.bot.playoffs:  # noqa
                    await append_into_ir(self.bot, guild, member, self.roster_sheet, 0)
                # Else already got into ir

            TEAM_ROLE = get(guild.roles, name="Team")
            for member in TEAM_ROLE.members:
                has_ir = get(member.roles, name="IR")
                if not has_ir:
                    playable_members.append(member)

            cnc_team_channel = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{get_team_name(guild.name)}",
            )

            # Ask Owner and General Manager to submit for lineups
            OWNER_ROLE = get(guild.roles, name="Owner")
            GM_ROLE = get(guild.roles, name="General Manager")

            OWNERS = get(SUPPORT_GUILD.roles, name="Owners")
            COMISSIONERS = get(SUPPORT_GUILD.roles, name="Commissioners")

            if len(playable_members) < 13 and not self.bot.playoffs:  # noqa
                await cnc_team_channel.send(
                    content=(
                        f"The {get_team_name(guild.name)} need {11 - len(playable_members)} ECU "
                        f"players this week {OWNERS.mention} {COMISSIONERS.mention}"
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
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.open_availability_task, get_next_date("Friday", hour=17)
                )

            return

        settings = await self.bot.prisma.settings.find_first()
        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": True,
                "can_submit_lineups": False,
            },
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
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.open_availability_task, get_next_date("Friday", hour=17)
                )

            return

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

    @staticmethod
    def get_played_games(
        old_game_data: Optional[dict], new_game_data: Optional[dict], member: nextcord.Member
    ):
        if old_game_data and new_game_data:
            if (
                member.display_name in old_game_data
                and member.display_name in new_game_data
            ):
                return (
                    new_game_data[member.display_name]
                    - old_game_data[member.display_name]
                )

            elif member.display_name in new_game_data:
                return new_game_data[member.display_name]

            else:
                return 0

        if new_game_data and member.display_name in new_game_data:
            return new_game_data[member.display_name]

        return 0

    async def calculate_gp(self, simulate: bool = False):
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.open_availability_task, get_next_date("Friday", hour=17)
                )

            return

        if self.bot.playoffs:  # noqa
            return self.start_task(
                self.open_availability_task, get_next_date("Friday", hour=17)
            )

        week = get_week()
        last_week = week - 1

        old_game_data = await self.bot.prisma.game.find_first(where={"week": last_week})
        new_week_data = await self.bot.prisma.game.find_first(where={"week": week})

        if old_game_data:
            old_data = json.loads(old_game_data.data)
        else:
            old_data = None

        if new_week_data:
            new_data = json.loads(new_week_data.data)
        else:
            new_data = get_all_team_data()
            await self.bot.prisma.game.create(
                {"week": week, "data": json.dumps(new_data)}
            )

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            not_minimum = []
            team = get(guild.roles, name="Team")

            for member in team.members:
                games_played = self.get_played_games(
                    old_data, new_data, member
                )

                if games_played < 3:
                    not_minimum.append(member)
            if not_minimum:
                team_name = get_team_name(guild.name)
                cnc_team_channel = get(
                    self.bot.SUPPORT_GUILD.text_channels,
                    name=f"╟・{team_name}",
                )

                mentions = ", ".join([player.display_name for player in not_minimum])
                if cnc_team_channel:
                    await cnc_team_channel.send(
                        content=(
                            f"{mentions} did not play at-least 3 games last week. And has been added to the IR list\n"
                            "**[IMPORTANT]:** This is a test message."
                            # f"{get(self.bot.SUPPORT_GUILD.roles, name='Owners')}, "
                            # f"{get(self.bot.SUPPORT_GUILD.roles, name='Commissioners')}"
                        )
                    )

        if not simulate:
            self.start_task(self.close_lineup_channel, get_next_date("Friday", hour=16))

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
            f16 = now + datetime.timedelta(seconds=3)
            f17 = now + datetime.timedelta(seconds=10)
            s16 = f17 + datetime.timedelta(seconds=30)
            t4 = s16 + datetime.timedelta(seconds=30)
            f2 = t4 + datetime.timedelta(seconds=30)

            if mode == "devstart":
                print("[+] Devstart mode")
                # self.start_task(self.calculate_gp, f16)
                # self.start_task(self.open_availability_task, f17)
                # self.start_task(self.close_availability_task, m16)
                # self.start_task(self.close_lineup_submit, t4)
                # self.start_task(self.close_lineup_channel, f2)
        else:
            # Real times
            f16 = get_next_date("Friday", hour=16)
            f17 = get_next_date("Friday", hour=17)
            s16 = get_next_date("Sunday", hour=16)
            t4 = get_next_date("Tuesday", hour=4)
            f2 = get_next_date("Friday", hour=2)

            self.start_task(self.calculate_gp, f16)
            self.start_task(self.open_availability_task, f17)
            self.start_task(self.close_availability_task, s16)
            self.start_task(self.close_lineup_submit, t4)
            self.start_task(self.close_lineup_channel, f2)

        self.scheduler.start()


def setup(bot: IBot):
    bot.add_cog(Tasker(bot))
