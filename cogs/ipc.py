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
    prisma: Prisma = bot.prisma  # noqa

    @server.route("get_stats")
    async def get_stats(_):
        data = await prisma.game.find_many(order={"week": "desc"})
        if len(data) > 1:
            return json.dumps({"current": data[0].data, "prev": data[1].data})
        elif len(data) == 1:
            return json.dumps(
                {
                    "current": data[0].data,
                    "prev": {},
                }
            )
        else:
            return json.dumps({"current": {}, "prev": {}})

    await server.start()
