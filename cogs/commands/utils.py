import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Union

import pytz
import nextcord
from nextcord import Guild, Member, Object
from nextcord.ext.commands import AutoShardedBot
from nextcord.utils import get
from essentials.models import IBot

from utils.data import inactive_channel, inactive_roles, ir_channel, support_server_id
from utils.gspread import DataSheet


roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
draft_sheet = DataSheet("NHL Live Draft Sheet")
nick_sheet = DataSheet("Official Nickname Updates")


def get_number(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


position_roles = {
    "LW": "Left Wing",
    "RW": "Right Wing",
    "LD": "Left Defense",
    "RD": "Right Defense",
    "G": "Goalie",
    "C": "Center",
}


async def add_roles(member: nextcord.Member, roles: list):
    roles = [role for role in roles if role]
    await member.add_roles(*roles)


async def sync_player(bot: IBot, member: nextcord.Member):
    team_name = member.guild.name.split(" ", maxsplit=1)[1].strip()
    cnc_member = bot.SUPPORT_GUILD.get_member(member.id)
    if not bot.SUPPORT_GUILD.get_member(member.id):
        return

    right_team = get(cnc_member.roles, name=team_name)
    if not right_team:
        return

    # Checking if team member
    all_roster = draft_sheet.get_values("Data import")
    for row in all_roster[1:]:
        if get_number(row[3]) == member.id:
            roles_to_add = [
                get(member.guild.roles, name="Team"),
                get(member.guild.roles, name=position_roles.get(row[1])),
                get(member.guild.roles, name=position_roles.get(row[2])),
            ]
            for role in roles_to_add:
                if role not in member.roles:
                    await add_roles(member, roles_to_add)
                    break

    # checking owner gm and agm
    owner_id = get_number(roster_sheet.get_value(team_name, "B27")[0][0])
    gm_id = get_number(roster_sheet.get_value(team_name, "B28")[0][0])
    agm_id = get_number(roster_sheet.get_value(team_name, "B29")[0][0])

    if owner_id == member.id:
        await member.add_roles(get(member.guild.roles, name="Owner"))
        await member.remove_roles(get(member.guild.roles, name="Team"))

    elif gm_id == member.id:
        await member.add_roles(get(member.guild.roles, name="General Manager"))
        await member.remove_roles(get(member.guild.roles, name="Team"))

    elif agm_id == member.id:
        await member.add_roles(get(member.guild.roles, name="AGM"))

    # importing nick
    nick_data = nick_sheet.get_values("data")
    for row in nick_data[1:]:
        if get_number(row[0]) == member.id:
            try:
                print(cnc_member)
                await cnc_member.edit(nick=row[1])
            except Exception as e:
                traceback.print_exc()
                print(f"Failed in CNC Discord")

            try:
                print(member)
                await member.edit(nick=row[1])
            except Exception as e:
                print(f"Failed in team discord")
                traceback.print_exc()
                print(e)


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
    items = list(filter(lambda x: x.discord_id == str(user.id), all_values))
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
            await channel.send(f"{user.mention} of the **{team_name}** has been deemed inactive")

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
                    await member.remove_roles(*[Object(role_id) for role_id in inactive_roles])
                except Exception as e:
                    print(e)


@dataclass
class CustomRole:
    name: str


@dataclass
class CustomMember:
    id: int
    nick: str
    roles: List[Union[nextcord.Role, CustomRole]]
    position: str = ""

    def __post_init__(self):
        position_roles = [
            role.name
            for role in self.roles
            if role.name in ["Left Wing", "Right Wing", "Left Defense", "Right Defense", "Center", "Goalie", "ECU"]
        ]

        positions = []
        for role in position_roles:
            if role == "ECU":
                positions.append("ECU")
            else:
                parts = role.split(" ")
                name = ""
                for part in parts:
                    name += part[0]

                positions.append(name)

        position = ", ".join(positions)
        self.position = f"({position})"

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((self.id,))


def get_custom_member(member: nextcord.Member) -> CustomMember:
    return CustomMember(member.id, nick=member.nick, roles=member.roles)


def combine_list(lists: list):
    all_items = []

    for lst in lists:
        all_items.extend(lst)

    return all_items


def valid_member(member: nextcord.Member):
    ir = get(member.roles, name="IR")

    if ir or not member.nick:
        return None

    team = get(member.roles, name="Team")
    ecu = get(member.roles, name="ECU")
    owner = get(member.roles, name="Owner")
    gm = get(member.roles, name="General Manager")

    if team or ecu or owner or gm:
        return True
