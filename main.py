import os
from typing import Optional

import nextcord
from dotenv import load_dotenv
from nextcord import Intents
from nextcord.ext import commands
from nextcord.utils import get

from essentials.models import Data
from prisma import Prisma
from utils.gspread import DataSheet
from cogs.commands.utils import sync_player

load_dotenv(".env")

intents = Intents.default()
intents.members = True  # noqa
intents.guilds = True  # noqa


def get_number(value):
    print(f"Value: {value}")
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class Availability(commands.AutoShardedBot):
    def __init__(self, command_prefix: str, **kwargs):
        super().__init__(command_prefix, **kwargs)
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
        self.SUPPORT_GUILD = self.get_guild(Data.SUPPORT_GUILD)

        settings = await self.prisma.settings.find_first()
        self.tasks_enabled = settings.tasks_enabled
        self.playoffs = settings.playofss

        if not settings:
            await self.prisma.settings.create(
                data={
                    "can_edit_lineups": False,
                    "can_submit_lineups": False,
                }
            )

        print(f"{self.user} is ready..")

        # all_roaster = self.roster_sheet.get_values("Data import")
        # nick_dict = {member.display_name: member.id for member in self.SUPPORT_GUILD.members}
        #
        # for index, row in enumerate(all_roaster):
        #     await asyncio.sleep(2)
        #     print(row[0], index)
        #     if row[0] in nick_dict:
        #         self.roster_sheet.update("Data import", f"D{index + 1}", str(nick_dict[row[0]]))

        for guild in self.guilds:
            ecu_role = get(guild.roles, name="ECU")
            decu_role = get(guild.roles, name="Daily ECU")

            if not ecu_role:
                await guild.create_role(name="ECU")

            if not decu_role:
                await guild.create_role(name="Daily ECU")

    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id in Data.IGNORED_GUILDS:
            return

        await sync_player(self, member)  # noqa

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


bot = Availability(command_prefix="a.", intents=intents)

bot.load_extension("cogs.commands")
bot.load_extension("cogs.commands.admin")
bot.load_extension("cogs.commands.ecu")
bot.load_extension("cogs.task")
bot.load_extension("cogs.utility")

TOKEN = os.environ["TOKEN"]
bot.run(TOKEN)
