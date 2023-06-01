import os

from dotenv import load_dotenv
from nextcord import Intents
from nextcord.ext import commands
from nextcord.utils import get

from essentials.models import Data
from prisma import Prisma

load_dotenv(".env")

intents = Intents.default()
intents.members = True # noqa


class Availability(commands.AutoShardedBot):
    def __init__(self, command_prefix: str, **kwargs):
        super().__init__(command_prefix, **kwargs)
        self.prisma = Prisma()
        self.SUPPORT_GUILD = None

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

        for guild in self.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            IR = get(guild.roles, name="IR")
            if not IR:
                try:
                    await guild.create_role(name="IR")
                except Exception as e:
                    print(e)
                    print(f"Failed to create role on {guild.name}")

        print(f"{self.user} is ready..")

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
