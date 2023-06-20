import os

import nextcord
from dotenv import load_dotenv
from nextcord import Intents
from nextcord.ext import commands
from nextcord.utils import get

from essentials.models import Data
from utils.gspread import DataSheet
from prisma import Prisma

load_dotenv(".env")

intents = Intents.default()
intents.members = True # noqa
intents.guilds = True # noqa


class Availability(commands.AutoShardedBot):
    def __init__(self, command_prefix: str, **kwargs):
        super().__init__(command_prefix, **kwargs)
        self.prisma = Prisma()
        self.SUPPORT_GUILD = None
        self.roster_sheet = DataSheet("NHL Live Draft Sheet")

    async def on_ready(self):
        await self.prisma.connect()
        self.SUPPORT_GUILD = self.get_guild(Data.SUPPORT_GUILD)

        settings = await self.prisma.settings.find_first()

        if not settings:
            await self.prisma.settings.create(
                data={
                    "can_edit_lineups": False,
                    "can_submit_lineups": False,
                }
            )

        print(f"{self.user} is ready..")

        all_roaster = self.roster_sheet.get_values("Data import")
        nick_dict = {member.display_name for member in self.SUPPORT_GUILD.members}

        for index, row in enumerate(all_roaster[:5]):
            if row[0] in nick_dict:
                self.roster_sheet.update("Data import", f"D{index + 1}", str(nick_dict[row[0]]))

    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id in Data.IGNORED_GUILDS:
            return
        team_role = get(member.guild.roles, name="Team")
        if not team_role:
            return

        all_roster = self.roster_sheet.get_values("Data import")
        for row in all_roster[1:]:
            try:
                member_id = int(row[3])
            except (ValueError, TypeError):
                continue

            if member_id == member.id:
                await member.add_roles(team_role)
                await member.edit(nick=row[0])

                primary_position = get(member.guild.roles, name=row[1])
                secondary_position = get(member.guild.roles, name=row[2])

                if primary_position:
                    await member.add_roles(primary_position)

                if secondary_position:
                    await member.add_roles(secondary_position)

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
bot.load_extension("cogs.task")
bot.load_extension("cogs.utility")

TOKEN = os.environ["TOKEN"]
bot.run(TOKEN)
