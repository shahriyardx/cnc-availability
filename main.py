import datetime
import os
from typing import Dict, List, Optional

import nextcord
from dotenv import load_dotenv
from nextcord import Intents
from nextcord.ext import commands
from nextcord.types.interactions import ApplicationCommand as ApplicationCommandPayload
from nextcord.utils import get

from essentials.models import Data
from prisma import Prisma
from utils.gspread import DataSheet
from cogs.commands.utils import sync_player
from cogs.ipc import init_ipc


load_dotenv(".env")

intents = Intents.default()
intents.members = True  # noqa
intents.guilds = True  # noqa


def get_number(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class Availability(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prisma = Prisma()
        self.SUPPORT_GUILD: Optional[nextcord.Guild] = None
        self.roster_sheet = DataSheet("NHL Live Draft Sheet")
        self.draft_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.ecu_sheet = DataSheet("ECU Sheet")
        self.tasks_enabled = True
        self.playoffs = False
        self.rollout_application_commands = False

    async def on_ready(self):
        await self.prisma.connect()
        try:
            await init_ipc(self)
        except:  # noqa
            print("failed to connect ipc server")
            pass

        self.SUPPORT_GUILD = self.get_guild(Data.SUPPORT_GUILD)

        settings = await self.prisma.settings.find_first()

        if not settings:
            settings = await self.prisma.settings.create(
                data={
                    "can_edit_lineups": False,
                    "can_submit_lineups": False,
                }
            )

        self.tasks_enabled = settings.tasks_enabled
        self.playoffs = settings.playofss

        print(f"{self.user} is ready..")

    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id in Data.IGNORED_GUILDS:
            return

        await sync_player(self, member)  # noqa

    async def handle_avail_react(self, reaction: nextcord.RawReactionActionEvent):
        guild = self.get_guild(reaction.guild_id)
        channel = guild.get_channel(reaction.channel_id)
        member_id = reaction.user_id

        if member_id == self.user.id:
            return

        if channel.name != "submit-availability":
            return

        message = await channel.fetch_message(reaction.message_id)
        message_parts = message.content.split(" ")

        if len(message_parts) < 2:
            return

        days_avail = ["Tuesday", "Wednesday", "Thursday"]
        times_avail = ["8:30pm", "9:10pm", "9:50pm"]

        day = message_parts[0].strip("__").strip("**").title()
        time = message_parts[1]

        if day not in days_avail or time not in times_avail:
            return

        week = datetime.datetime.now().isocalendar()[1]

        if reaction.emoji.name == "✅" and reaction.event_type == "REACTION_ADD":
            await reaction.member.add_roles(get(guild.roles, name="Availability Submitted"))
            submits = await self.prisma.availabilitysubmitted.find_many(
                where={
                    "member_id": member_id,
                    "day": day,
                    "time": time,
                }
            )

            if not submits:
                await self.prisma.availabilitysubmitted.create(
                    {
                        "member_id": member_id,
                        "day": day,
                        "time": time,
                        "week": week,
                    }
                )

        if reaction.emoji.name == "✅" and reaction.event_type == "REACTION_REMOVE":
            await self.prisma.availabilitysubmitted.delete_many(
                where={
                    "member_id": member_id,
                    "week": week,
                    "day": day,
                    "time": time,
                }
            )

    async def on_raw_reaction_add(self, reaction: nextcord.RawReactionActionEvent):
        await self.handle_avail_react(reaction)

    async def on_raw_reaction_remove(self, reaction: nextcord.RawReactionActionEvent):
        await self.handle_avail_react(reaction)

    def get_command_mention(self, command_name) -> str:
        cmd = None
        all_commands = self.get_application_commands()

        for command in all_commands:
            if command.qualified_name == command_name:
                cmd = command

        if cmd:
            return f"</{command_name}:{cmd.command_ids[None]}>"
        else:
            return f"/{command_name}"


bot = Availability(intents=intents)
print("Loading cogs")
bot.load_extension("cogs.commands")
bot.load_extension("cogs.commands.admin")
bot.load_extension("cogs.commands.ecu")
bot.load_extension("cogs.task")
bot.load_extension("cogs.utility")

print("Starting")
TOKEN = os.environ["TOKEN"]
bot.run(TOKEN)
