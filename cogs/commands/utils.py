from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz
from nextcord import Guild, Member, Object
from nextcord.ext.commands import AutoShardedBot
from nextcord.utils import get

from utils.data import (inactive_channel, inactive_roles, ir_channel,
                        support_server_id)
from utils.gspread import DataSheet


@dataclass
class IR:
    team: str
    player: str
    week: str
    week_2: str
    ticket: str
    reason: str
    status: str
    discord_id: Optional[str]

    @staticmethod
    def create(data):
        return IR(*data)


async def append_into_ir(
    bot: AutoShardedBot,
    guild: Guild,
    user: Member,
    sheet: DataSheet,
    total_games: int = 0,
):
    current_time = datetime.now(pytz.timezone("US/Eastern"))
    all_values = [IR.create(data) for data in sheet.get_values("IR")]
    items = list(filter(lambda x: x.player == user.display_name, all_values))
    status = "Approved" if len(items) < 2 else "Denied"
    team_name = guild.name.replace("CNC", "").strip()

    sheet.append(
        "IR",
        [
            team_name,
            user.display_name,
            f"{current_time.month}/{current_time.day}/{current_time.year}",
            "Full Week",
            "null",
            f"Availability Bot (Total games = {total_games})",
            status,
            str(user.id),
        ],
    )

    IR_role = get(guild.roles, name="IR")
    await user.add_roles(IR_role)

    channel = bot.get_channel(ir_channel)
    if channel:
        await channel.send(f"{user.mention} of the **{team_name}** is on IR this week")

    if status == "Approved":
        if len(items) == 0:
            next_status = "This is your first time on IR, you still have one week left of IR to use."
        elif len(items) == 1:
            next_status = (
                "This is your second time on IR. The next time you will be removed from your team and "
                "inactivated in the league which will lead to a permanent ban."
            )
        else:
            next_status = ""

        try:
            await user.send(
                content=(
                    f"{user.mention} You have been placed on IR because you didn't "
                    "submit availability this week or did not submit enough games of availability this week. "
                    f"{next_status}"
                )
            )
        except Exception as e:
            print(e)
    else:
        team_name = guild.name.split(" ", maxsplit=1)[1]
        print(user.display_name)

        sheet.append(
            "Inactive",
            [
                user.display_name,
                str(user.id),
                team_name,
                "Unavailable",
                "Third time being on IR",
            ],
        )

        channel = bot.get_channel(inactive_channel)
        if channel:
            await channel.send(
                f"{user.mention} of the **{team_name}** has been deemed inactive"
            )

        all_values = sheet.get_values(team_name)
        for index, value in enumerate(all_values, start=1):
            if value[0] == user.display_name:
                sheet.update(team_name, position=f"A{index}", data="Open")
                sheet.update(team_name, position=f"B{index}", data="")
                sheet.update(team_name, position=f"C{index}", data="")
                break

        try:
            await user.send(
                content=(
                    f"You have been removed from the {team_name} for not providing "
                    "enough availability for the third time this season"
                )
            )
        except Exception as e:
            print(e)

        try:
            await user.kick(reason="Kicked because of third time being on IR")
        except Exception as e:
            print(e)

        support_server = bot.get_guild(support_server_id)
        if support_server:
            member = support_server.get_member(user.id)
            if member:
                try:
                    await member.remove_roles(
                        *[Object(role_id) for role_id in inactive_roles]
                    )
                except Exception as e:
                    print(e)
