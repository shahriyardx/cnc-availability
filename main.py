import os

from dotenv import load_dotenv
from nextcord import Intents, Message
from nextcord.ext import commands

from prisma import Prisma

load_dotenv(".env")

intents = Intents.default()
intents.message_content = True
intents.members = True


class Availability(commands.AutoShardedBot):
    def __init__(self, command_prefix: str, **kwargs):
        super().__init__(command_prefix, **kwargs)
        self.prisma = Prisma()

    async def on_ready(self):
        # try:
        #     await self.prisma.connect()
        # except:
        #     pass

        print(f"{self.user} is ready..")

    async def on_message(self, message: Message):
        if message.author.bot:
            return

        await self.process_commands(message)

    def get_command_mention(self, guild_id: int, command_name) -> str:
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
