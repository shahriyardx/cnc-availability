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
from betterspread import Sheet, Connection

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

con = Connection("./credentials.json")


roster_sheet = Sheet("OFFICIAL NHL ROSTER SHEET", connection=con)
draft_sheet = Sheet("NHL Live Draft Sheet", connection=con)
nick_sheet = Sheet("Official Nickname Updates", connection=con)


async def sync_player(bot: IBot, member: nextcord.Member, all_roster=None, team_tab=None, ids=None):
    team_name = member.guild.name.split(" ", maxsplit=1)[1].strip()

    if not all_roster and not team_tab:
        data_import_tab = await draft_sheet.get_tab("Data import")
        all_roster = await data_import_tab.values()
        team_tab = await roster_sheet.get_tab(team_name)

    cnc_member = bot.SUPPORT_GUILD.get_member(member.id)
    if not bot.SUPPORT_GUILD.get_member(member.id):
        return

    right_team = get(cnc_member.roles, name=team_name)
    if not right_team:
        return

    await member.add_roles(get(member.guild.roles, name="Team"))

    # Checking if team member
    for row in all_roster[1:]:
        if get_number(row[3]) == member.id:
            roles_to_add = [
                get(member.guild.roles, name=position_roles.get(row[1])),
                get(member.guild.roles, name=position_roles.get(row[2])),
            ]
            for role in roles_to_add:
                if role not in member.roles:
                    await add_roles(member, roles_to_add)
                    break

    if not ids:
        owner_id = get_number(await team_tab.get_cell("B27"))
        gm_id = get_number(await team_tab.get_cell("B28"))
        agm_id = get_number(await team_tab.get_cell("B29"))
    else:
        owner_id, gm_id, agm_id = list(map(lambda x: get_number(x), ids))

    print(owner_id, gm_id, agm_id)

    if owner_id == member.id:
        await member.add_roles(get(member.guild.roles, name="Owner"))
        await member.remove_roles(get(member.guild.roles, name="Team"))

    if gm_id == member.id:
        await member.add_roles(get(member.guild.roles, name="General Manager"))
        await member.remove_roles(get(member.guild.roles, name="Team"))

    if agm_id == member.id:
        await member.add_roles(get(member.guild.roles, name="AGM"))

    # importing nick
    cnc_nick = cnc_member.nick
    try:
        await member.edit(nick=cnc_nick)
    except:  # noqa
        pass


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
    sheet,
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

    try:
        IR_role = get(guild.roles, name="IR")
        await user.add_roles(IR_role)
    except:
        pass

    try:
        channel = bot.get_channel(ir_channel)
        if channel:
            await channel.send(
                f"{user.mention} of the **{team_name}** is on IR this week"
            )
    except:  # noqa
        pass

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
        except:  # noqa
            pass
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
        except:  # noqa
            pass

        try:
            await user.kick(reason="Kicked because of third time being on IR")
        except:  # noqa
            pass

        support_server = bot.get_guild(support_server_id)
        if support_server:
            member = support_server.get_member(user.id)
            if member:
                try:
                    await member.remove_roles(
                        *[Object(role_id) for role_id in inactive_roles]
                    )
                except:  # noqa
                    pass


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
        pos_roles = [
            role.name
            for role in self.roles
            if role.name
            in [
                "Left Wing",
                "Right Wing",
                "Left Defense",
                "Right Defense",
                "Center",
                "Goalie",
                "ECU",
            ]
        ]

        positions = []
        for role in pos_roles:
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


@dataclass
class Player:
    position: str
    player_id: int

    def __eq__(self, other):
        return self.player_id == other.player_id

    def __hash__(self):
        return hash(self.player_id)


def get_duplicate(data: dict):
    values = []
    duplicate_values = []

    all_items = [Player(pos, pid) for pos, pid in data.items()]

    for item in all_items:
        if item.player_id == 1:
            continue

        if item in values:
            duplicate_values.append(item)
            duplicate_item = values[values.index(item)]
            duplicate_values.append(duplicate_item)

        values.append(item)

    if not duplicate_values:
        return None

    return ", ".join(set([val.position for val in duplicate_values]))
