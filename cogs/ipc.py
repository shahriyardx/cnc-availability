import os
import json
from winerp import Client
from nextcord.ext.commands import AutoShardedBot
from prisma import Prisma

IPC_HOST = os.getenv("IPC_HOST")
IPC_PORT = os.getenv("IPC_PORT")

server = Client(
    local_name="avail",
    host=IPC_HOST,
    port=int(IPC_PORT),
    reconnect=True,
)


async def init_ipc(bot: AutoShardedBot):
    prisma: Prisma = bot.prisma # noqa

    @server.route("get_stats")
    async def get_stats(_, week: int):
        data = await prisma.game.find_first(where={"week": week})
        if (data):
            return json.dumps(data.data)
        else:
            return json.dumps({})

    await server.start()
