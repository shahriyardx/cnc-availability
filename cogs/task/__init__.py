import asyncio
import datetime
import json
import os
import traceback

from aioscheduler import TimedScheduler
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext import commands, tasks
from nextcord.utils import get

from essentials.models import Data, IBot
from essentials.time import get_next_date
from essentials.utils import get_team_name
from utils.gspread import DataSheet

from .stats import get_all_team_data
from .utils import get_week, lockdown, unlockdown, report_games_played, send_message
from betterspread import Sheet, Connection

connection = Connection(credentials_path="./credentials.json")


class Tasker(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.scheduler = TimedScheduler(prefer_utc=True)
        self.start_tasks.start()
        self.roster = Sheet("OFFICIAL NHL ROSTER SHEET", connection=connection)
        self.roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")

    @slash_command(description="Simulate specific tasks")
    async def simulate(
        self,
        interaction: Interaction,
        task: str = SlashOption(
            description="Select task to simulate",
            choices={
                "Open Availability": "Open Availability",
                "Notify Lineups": "Notify Lineups",
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
            "Notify Lineups": self.close_availability_task,
            "Calculate Games Played": self.calculate_gp,
        }

        task_func = t[task]

        try:
            await task_func(True)
        except Exception as e:
            traceback.print_exc()
            return await interaction.edit_original_message(content=f"**Error**: {e}")

        await interaction.edit_original_message(content="Simulation succeeded.")

    @slash_command(description="Simulate specific tasks")
    async def repost_avail(self, interaction: Interaction):
        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return

        await interaction.response.defer(ephemeral=True)

        play_days = ["Tuesday", "Wednesday", "Thursday"]
        play_times = ["8:30pm", "9:10pm", "9:50pm"]

        new_avail_submit_channel = get(
            interaction.guild.channels, name="submit-availability"
        )
        players_role = get(interaction.guild.roles, name="Team")

        for day in play_days:
            date = get_next_date(day)
            await new_avail_submit_channel.send(
                content=f"╔══ **{day.upper()}** ({date.month}/{date.day}/{date.year}) ══╗"
            )
            for time in play_times:
                msg = await new_avail_submit_channel.send(
                    content=f"__**{day.upper()}**__ {time}"
                )
                await msg.add_reaction("✅")
                await asyncio.sleep(2)

            await new_avail_submit_channel.send(content="╚════════════════════╝")

        await new_avail_submit_channel.send(
            content=(
                f"{players_role.mention} choose which games you can play. "
                "You must select a minimum of 4 games or more"
            )
        )

        await interaction.followup.send(content="Done ✅")

    @slash_command(description="get avail of specific day", name="get-avail")
    async def get_avail(
        self,
        interaction: Interaction,
        day: str = SlashOption(
            description="Select task to simulate",
            choices={
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
            },
        ),
    ):
        await interaction.response.defer()

        guild = interaction.guild
        team_role = get(guild.roles, name=Data.PLAYERS_ROLE)

        member_ids = [member.id for member in team_role.members]

        avails = await self.bot.prisma.availabilitysubmitted.find_many(
            where={"day": day, "member_id": {"in": member_ids}}
        )
        data = {
            "8:30pm": [],
            "9:10pm": [],
            "9:50pm": [],
        }

        for avail in avails:
            member = guild.get_member(avail.member_id)
            if member:
                data[avail.time].append(member.mention)

        msg = f"Avail submissions for : {day}\n"
        for key, val in data.items():
            msg += f"**{key}** - {','.join(val)}\n" if val else f"**{key}:** None\n"

        await interaction.followup.send(content=msg)

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

            print(f"=== Opening {guild.name}===")

            try:
                players_role = get(guild.roles, name=Data.PLAYERS_ROLE)
                submitted_role = get(guild.roles, name=Data.SUBMITTED_ROLE)
                ir_role = get(guild.roles, name="IR")
                ecu_role = get(guild.roles, name="ECU")

                avail_submit_channel = get(
                    guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL
                )
                chat_channel = get(guild.text_channels, name="chat")
                lineups_channel = get(
                    guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL
                )

                gm_role = get(guild.roles, name="General Manager")
                owner_role = get(guild.roles, name="Owner")

                await unlockdown(
                    lineups_channel, roles=[r for r in [owner_role, gm_role] if r]
                )
                if not players_role or not avail_submit_channel or not submitted_role:
                    continue

                new_avail_submit_channel = await avail_submit_channel.clone()
                await avail_submit_channel.delete()

                await unlockdown(channel=new_avail_submit_channel, roles=players_role)

                # Send messages
                for day in play_days:
                    date = get_next_date(day)
                    await new_avail_submit_channel.send(
                        content=f"╔══ **{day.upper()}** ({date.month}/{date.day}/{date.year}) ══╗"
                    )
                    for time in play_times:
                        msg = await new_avail_submit_channel.send(
                            content=f"__**{day.upper()}**__ {time}"
                        )
                        await msg.add_reaction("✅")
                        await asyncio.sleep(2)

                    await new_avail_submit_channel.send(
                        content="╚════════════════════╝"
                    )

                await new_avail_submit_channel.send(
                    content=(
                        f"{players_role.mention} choose which games you can play. "
                        "You must select a minimum of 4 games or more"
                    )
                )

                await chat_channel.send(
                    content=(
                        f"{players_role.mention}, this is a friendly reminder to  {new_avail_submit_channel.mention}. "
                        f"Please make sure you give your team your availability for "
                        f"the week and get your 3 game minimums in."
                    )
                )

                for member in submitted_role.members:
                    try:
                        await member.remove_roles(
                            submitted_role, ir_role, reason="Open Availability"
                        )
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
            except Exception as e:
                traceback.print_exc()
                print(e)

        print("[+] END open_availability_task")
        if not simulate:
            self.start_task(
                self.open_availability_task, get_next_date("Friday", hour=17)
            )

    async def close_availability_task(self, simulate: bool = False):
        # Runs Monday 5 PM UTC

        support_guild = self.bot.SUPPORT_GUILD
        print("[+] START close_availability_task")
        if not self.bot.tasks_enabled or self.bot.playoffs:  # noqa
            if not simulate:
                return self.start_task(
                    self.close_availability_task, get_next_date("Monday", hour=16)
                )

            return

        # Member count check
        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            team_role = get(guild.roles, name="Team")
            lineups_channel = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)
            playable_members = []

            for member in team_role.members:
                has_ir = get(member.roles, name="IR")
                if not has_ir:
                    playable_members.append(member)

            cnc_team_channel = get(
                support_guild.text_channels,
                name=get_team_name(guild.name, prefix="╟・"),
            )

            # Ask Owner and General Manager to submit for lineups
            owner_role = get(guild.roles, name="Owner")
            gm_role = get(guild.roles, name="General Manager")

            if len(playable_members) < 11 and not self.bot.playoffs:  # noqa
                await cnc_team_channel.send(
                    content=(
                        f"The **{get_team_name(guild.name)}** need {11 - len(playable_members)} ECU "
                        f"players this week"
                    )
                )

            if not owner_role or not gm_role:
                continue

            await lineups_channel.send(
                content=(
                    f"{owner_role.mention} & {gm_role.mention}, this is a friendly reminder to make sure "
                    f"you submit your lineups for games before 8:30 EST on each day. "
                    f"You can run the command {self.bot.get_command_mention('get-avail')} to check availability "
                    f"given and Use the command {self.bot.get_command_mention('set-lineups')} to enter lineups"
                )
            )

        print("[+] STOP close_availability_task")
        if not simulate:
            self.start_task(
                self.close_availability_task, get_next_date("Monday", hour=16)
            )

    async def calculate_gp(self, simulate: bool = False):
        if not self.bot.tasks_enabled:  # noqa
            if not simulate:
                return self.start_task(
                    self.calculate_gp, get_next_date("Friday", hour=16)
                )

            return

        if self.bot.playoffs:  # noqa
            return self.start_task(self.calculate_gp, get_next_date("Friday", hour=16))

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
            await self.bot.prisma.game.create(
                {"week": week, "data": json.dumps(new_data)}
            )

        for guild in self.bot.guilds:
            await report_games_played(self.bot, guild, old_data, new_data)

        if not simulate:
            self.start_task(self.calculate_gp, get_next_date("Friday", hour=16))

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
            # t4 = get_next_date("Tuesday", hour=4)
            # f2 = get_next_date("Friday", hour=2)

            self.start_task(self.calculate_gp, f16)
            self.start_task(self.open_availability_task, f17)
            self.start_task(self.close_availability_task, m16)

            # self.start_task(self.close_lineup_submit, t4)
            # self.start_task(self.close_lineup_channel, f2)

        self.scheduler.start()


def setup(bot: IBot):
    bot.add_cog(Tasker(bot))
