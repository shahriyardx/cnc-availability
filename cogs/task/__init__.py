import asyncio
import datetime
import json
import os
import traceback

from aioscheduler import TimedScheduler
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext import commands, tasks
from nextcord.utils import get

from cogs.commands.utils import append_into_ir
from essentials.models import Data, IBot
from essentials.time import get_next_date
from essentials.utils import get_team_name
from utils.gspread import DataSheet

from .stats import get_all_team_data
from .utils import get_week, lockdown, unlockdown, report_games_played, send_message


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
            return await interaction.edit_original_message(content="You are allowed to simulate tasks")

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
            traceback.print_exc()
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
                return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

            return

        if not simulate:
            await self.bot.prisma.playerlineup.delete_many()
            await self.bot.prisma.lineup.delete_many()
            await self.bot.prisma.availabilitysubmitted.delete_many()

        settings = await self.bot.prisma.settings.find_first()

        await self.bot.prisma.settings.update(
            where={"id": settings.id},
            data={
                "can_edit_lineups": False,
                "can_submit_lineups": False,
            },
        )

        play_days = ["Tuesday", "Wednesday", "Thursday"]
        play_times = ["8:30pm", "9:10pm", "9:50pm"]

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            players_role = get(guild.roles, name=Data.PLAYERS_ROLE)
            submitted_role = get(guild.roles, name=Data.SUBMITTED_ROLE)
            ir_role = get(guild.roles, name="IR")
            ecu_role = get(guild.roles, name="ECU")

            avail_submit_channel = get(guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL)

            if not players_role or not avail_submit_channel or not submitted_role:
                continue

            new_avail_submit_channel = await avail_submit_channel.clone()
            await avail_submit_channel.delete()

            await unlockdown(channel=new_avail_submit_channel, roles=players_role)

            # Send messages
            for day in play_days:
                date = get_next_date(day)
                await new_avail_submit_channel.send(
                    content=f"🚨🚨 **{day.upper()}** ({date.month}/{date.day}/{date.year}) 🚨🚨"
                )
                for time in play_times:
                    msg = await new_avail_submit_channel.send(content=f"__**{day.upper()}**__ {time}")
                    await msg.add_reaction("✅")
                    await msg.add_reaction("❌")
                    await asyncio.sleep(2)

            for member in submitted_role.members:
                try:
                    await member.remove_roles(submitted_role, ir_role, reason="Open Availability")
                except Exception as e:
                    print(e)

            for member in ir_role.members:
                try:
                    await member.remove_roles(ir_role, reason="Open Availability")
                except Exception as e:
                    print(e)

            for member in ecu_role.members:
                try:
                    await member.kick()
                except:  # noqa
                    try:
                        await member.remove_roles(ecu_role)
                    except:  # noqa
                        pass

        print("[+] END open_availability_task")
        if not simulate:
            self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

    async def close_availability_task(self, simulate: bool = False):
        # Runs Monday 5 PM UTC
        # Closes availability submission
        # Open Lineups submit

        support_guild = self.bot.SUPPORT_GUILD
        print("[+] START close_availability_task")
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

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

        # IR Process
        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            team_role = get(guild.roles, name=Data.PLAYERS_ROLE)

            if not team_role:
                continue

            # Lockdown submit channel - No more availability submission
            submit_availability_channel = get(guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL)
            availability_log_channel = get(guild.text_channels, name=Data.AVIAL_LOG_CHANNEL)
            team_avail_log_channel = get(support_guild.text_channels, name=get_team_name(guild.name, prefix='╟・'))

            await submit_availability_channel.send(content="This concludes this weeks availability")
            await lockdown(submit_availability_channel, roles=team_role)

            if self.bot.playoffs:
                continue

            for member in team_role.members:
                submitted = get(member.roles, name="Availability Submitted")

                if not submitted:
                    await append_into_ir(self.bot, guild, member, self.roster_sheet, 0)
                    continue

                avails = await self.bot.prisma.availabilitysubmitted.find_many(where={"member_id": member.id})
                times = {
                    "Tuesday": [],
                    "Wednesday": [],
                    "Thursday": [],
                }
                for avail in avails:
                    times[avail.day].append(avail.time)

                message = f"{member.mention} is available\n"
                for key, value in times.items():
                    if not value:
                        message += f"{key}: None\n"

                    message += f"{key}: {'/'.join(value)}\n"

                await send_message(availability_log_channel, message)
                await send_message(team_avail_log_channel, message)

                if len(avails) < 3:
                    await append_into_ir(self.bot, guild, member, self.roster_sheet, 0)

        # Member count check
        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            team_role = get(guild.roles, name="Team")
            lineups_channel = get(guild.text_channels, name="submit-lineups")
            playable_members = []

            for member in team_role.members:
                has_ir = get(member.roles, name="IR")
                if not has_ir:
                    playable_members.append(member)

            cnc_team_channel = get(
                support_guild.text_channels,
                name=get_team_name(guild.name, prefix='╟・'),
            )

            # Ask Owner and General Manager to submit for lineups
            owner_role = get(guild.roles, name="Owner")
            gm_role = get(guild.roles, name="General Manager")

            owners_role = get(support_guild.roles, name="Owners")
            commissioners_role = get(support_guild.roles, name="Commissioners")

            if len(playable_members) < 11 and not self.bot.playoffs:  # noqa
                await cnc_team_channel.send(
                    content=(
                        f"The {get_team_name(guild.name)} need {11 - len(playable_members)} ECU "
                        f"players this week {owners_role.mention} {commissioners_role.mention}"
                    )
                )

            if not owner_role or not gm_role:
                continue

            await unlockdown(lineups_channel, roles=[owner_role, gm_role])
            await lineups_channel.send(
                content=(
                    f"{owner_role.mention} or {gm_role.mention} please click on "
                    f"{self.bot.get_command_mention('setlineups')} to enter your preliminary lineups"
                )
            )

        print("[+] STOP close_availability_task")
        if not simulate:
            self.start_task(self.close_availability_task, get_next_date("Monday", hour=17))

    async def close_lineup_submit(self, simulate: bool = False):
        # Runs Tuesday 4 AM
        # Keeps the lineup edit open

        print("[+] START close_lineup_submit")
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

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
                return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

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

            lineups_channel = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)
            owner_role = get(guild.roles, name="Owner")
            gm_role = get(guild.roles, name="General Manager")

            if lineups_channel and owner_role and gm_role:
                await lineups_channel.send(":information_source: Lineup editing has been closed for this week.")

                await lockdown(lineups_channel, roles=[owner_role, gm_role])

        print("[+] STOP close_lineup_channel")

        if not simulate:
            self.start_task(self.close_lineup_channel, get_next_date("Friday", hour=2))

    async def calculate_gp(self, simulate: bool = False):
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

            return

        if self.bot.playoffs:  # noqa
            return self.start_task(self.open_availability_task, get_next_date("Friday", hour=17))

        week = get_week()
        last_week = week - 1

        old_data = dict()

        old_game_data = await self.bot.prisma.game.find_first(where={"week": last_week})
        new_week_data = await self.bot.prisma.game.find_first(where={"week": week})

        if old_game_data:
            old_data = json.loads(old_game_data.data)

        if new_week_data:
            new_data = json.loads(new_week_data.data)
        else:
            new_data = get_all_team_data()
            await self.bot.prisma.game.create({"week": week, "data": json.dumps(new_data)})

        for guild in self.bot.guilds:
            await report_games_played(self.bot, guild, old_data, new_data)

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
            # now = datetime.datetime.utcnow()
            # f16 = now + datetime.timedelta(seconds=3)
            # f17 = now + datetime.timedelta(seconds=10)
            # s16 = f17 + datetime.timedelta(seconds=30)
            # t4 = s16 + datetime.timedelta(seconds=30)
            # f2 = t4 + datetime.timedelta(seconds=30)
            pass

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
            m16 = get_next_date("Monday", hour=16)
            t4 = get_next_date("Tuesday", hour=4)
            f2 = get_next_date("Friday", hour=2)

            self.start_task(self.calculate_gp, f16)
            self.start_task(self.open_availability_task, f17)
            self.start_task(self.close_availability_task, m16)
            self.start_task(self.close_lineup_submit, t4)
            self.start_task(self.close_lineup_channel, f2)

        self.scheduler.start()


def setup(bot: IBot):
    bot.add_cog(Tasker(bot))
