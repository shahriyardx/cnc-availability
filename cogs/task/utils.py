import datetime
from typing import List, Union, Optional

import nextcord
from nextcord import PermissionOverwrite, Role, TextChannel
from nextcord.utils import get
from essentials.models import IBot, Data
import json
from .stats import get_all_team_data


def get_permissions(state: bool):
    permission_overwrites = PermissionOverwrite()
    permission_overwrites.send_messages = state  # noqa
    permission_overwrites.view_channel = True  # noqa

    return permission_overwrites


def get_team_name(name: str):
    return name[4:].replace(" ", "-").replace(".", "").lower()


def get_roles_array(roles: Union[Role, List[Role]]):
    if isinstance(roles, Role):
        return [roles]

    return roles


async def unlockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(
            target=role, overwrite=get_permissions(state=True)
        )


async def lockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(
            target=role, overwrite=get_permissions(state=False)
        )


def get_week():
    return datetime.datetime.now().isocalendar()[1]


def get_played_games(
    old_game_data: Optional[dict], new_game_data: Optional[dict], member: nextcord.Member
):
    if old_game_data and new_game_data:
        if (
            member.display_name in old_game_data
            and member.display_name in new_game_data
        ):
            return (
                new_game_data[member.display_name]
                - old_game_data[member.display_name]
            )

        elif member.display_name in new_game_data:
            return new_game_data[member.display_name]

        else:
            return 0

    if new_game_data and member.display_name in new_game_data:
        return new_game_data[member.display_name]

    return 0


async def report_games_played(bot: IBot, guild: nextcord.Guild):
    week = get_week()
    last_week = week - 1

    old_game_data = await bot.prisma.game.find_first(where={"week": last_week})
    new_week_data = await bot.prisma.game.find_first(where={"week": week})

    if old_game_data:
        old_data = json.loads(old_game_data.data)
    else:
        old_data = None

    if new_week_data:
        new_data = json.loads(new_week_data.data)
    else:
        new_data = get_all_team_data()
        await bot.prisma.game.create(
            {"week": week, "data": json.dumps(new_data)}
        )

    if guild.id in Data.IGNORED_GUILDS:
        return

    not_minimum = []
    team = get(guild.roles, name="Team")

    for member in team.members:
        games_played = get_played_games(
            old_data, new_data, member
        )

        if games_played < 3:
            not_minimum.append([member, games_played])

    if not_minimum:
        team_name = get_team_name(guild.name)
        cnc_team_channel = get(
            bot.SUPPORT_GUILD.text_channels,
            name=f"╟・{team_name}",
        )

        mentions = ", ".join([f"{player[0].display_name} - {player[1]}" for player in not_minimum])
        if cnc_team_channel:
            await cnc_team_channel.send(
                content=(
                    f"{mentions} did not play at-least 3 games last week. And has been added to the IR list\n"
                    # f"{get(self.bot.SUPPORT_GUILD.roles, name='Owners')}, "
                    # f"{get(self.bot.SUPPORT_GUILD.roles, name='Commissioners')}"
                )
            )