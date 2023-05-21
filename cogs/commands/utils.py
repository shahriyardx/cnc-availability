from dataclasses import dataclass
from datetime import datetime

import pytz
from nextcord import Guild, Member, Object
from nextcord.ext.commands import AutoShardedBot

from utils.data import inactive_roles, support_server_id
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

    sheet.append(
        "IR",
        [
            guild.name.replace("CNC", "").strip(),
            user.display_name,
            f"{current_time.day}-{current_time.month}-{current_time.year}",
            "Full Week",
            "null",
            f"Availability Bot (Total games = {total_games})",
            status,
        ],
    )

    if status == "Approved":
        if len(items) == 0:
            next_status = "This is your first time on IR, you still have one week left of IR to use."
        elif len(items) == 1:
            next_status = (
                "This is your second time on IR. The next time you will be removed from your team and "
                "inactivated in the league which could lead to a 1 year league ban"
            )
        else:
            next_status = ""

        try:
            await user.send(
                content=(
                    f"i{user.mention} You have been placed on IR because you didn't "
                    "submit availability this week or did not submit enough games of availability this week. "
                    f"{next_status}"
                )
            )
        except Exception as e:
            print(e)
    else:
        team_name = guild.name.split(" ", maxsplit=1)[1]

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
                    f"You have been removed from the team {team_name} "
                    "for being third time on IR"
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
