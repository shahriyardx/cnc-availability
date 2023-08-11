import datetime
from typing import List, Union, Optional

import nextcord
from nextcord import PermissionOverwrite, Role, TextChannel
from nextcord.utils import get
from essentials.models import IBot, Data


def get_permissions(state: bool):
    permission_overwrites = PermissionOverwrite()
    permission_overwrites.send_messages = state  # noqa
    permission_overwrites.view_channel = state  # noqa

    return permission_overwrites


def get_team_name(name: str):
    return name[4:].replace(" ", "-").replace(".", "").lower()


def get_roles_array(roles: Union[Role, List[Role]]):
    if isinstance(roles, Role):
        return [roles]

    return roles


async def unlockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(target=role, overwrite=get_permissions(state=True))


async def lockdown(channel: TextChannel, roles: Union[Role, List[Role]]):
    for role in get_roles_array(roles):
        await channel.set_permissions(target=role, overwrite=get_permissions(state=False))


def get_week():
    return datetime.datetime.now().isocalendar()[1]


def get_played_games(
    old_game_data: Optional[dict],
    new_game_data: Optional[dict],
    member: nextcord.Member,
):
    if not old_game_data:
        old_game_data = dict()

    if not new_game_data:
        new_game_data = dict()

    # in both
    if member.display_name in old_game_data and member.display_name in new_game_data:
        return new_game_data[member.display_name] - old_game_data[member.display_name]

    # not in both
    if member.display_name not in old_game_data and member.display_name not in new_game_data:
        return -1

    # in any of them
    if member.display_name in new_game_data:
        return new_game_data[member.display_name]

    else:
        return 0


async def report_games_played(
    bot: IBot,
    guild: nextcord.Guild,
    old_data: dict,
    new_data: dict,
    return_first: bool = False,
):
    if guild.id in Data.IGNORED_GUILDS:
        return

    not_minimum = []
    team = get(guild.roles, name="Team")
    ecu = get(guild.roles, name="ECU")

    checking_members: List[nextcord.Member] = [*team.members, *ecu.members]

    for member in checking_members:
        games_played = get_played_games(old_data, new_data, member)

        if games_played == -1:
            continue

        if games_played < 3:
            not_minimum.append([member, games_played, ecu in member.roles])

    if not_minimum:
        team_name = get_team_name(guild.name)
        cnc_team_channel = get(
            bot.SUPPORT_GUILD.text_channels,
            name=f"╟・{team_name}",
        )

        mentions = "### Players who did not play minimum 3 games this week\n"
        for player_data in not_minimum:
            mentions += f"- {player_data[0].mention} ({player_data[0].id}){' (ECU)' if player_data[2] else ''} played **{player_data[1]}** games\n"

        if return_first:
            return mentions

        if cnc_team_channel:
            await cnc_team_channel.send(content=mentions)
            f"{get(bot.SUPPORT_GUILD.roles, name='Owners')}, "
            f"{get(bot.SUPPORT_GUILD.roles, name='Commissioners')}"


async def send_message(channel: nextcord.TextChannel, content: str):
    if not channel:
        return

    try:
        await channel.send(content=content)
    except Exception as e:
        print(e)
