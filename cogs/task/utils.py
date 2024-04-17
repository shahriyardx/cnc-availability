import asyncio
import datetime
from typing import List, Union, Optional

import betterspread
import discord
import gspread.exceptions
import nextcord
from nextcord import PermissionOverwrite, Role, TextChannel
from nextcord.utils import get
from essentials.models import IBot, Data


def get_permissions(state: bool):
    permission_overwrites = PermissionOverwrite()
    permission_overwrites.send_messages = state  # noqa
    permission_overwrites.view_channel = state  # noqa
    permission_overwrites.add_reactions = state  # noqa

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
    old_game_data: Optional[dict],
    new_game_data: Optional[dict],
    member: nextcord.Member,
):
    if not old_game_data:
        old_game_data = dict()

    if not new_game_data:
        new_game_data = dict()

    # in both
    if str(member.id) in old_game_data and str(member.id) in new_game_data:
        return new_game_data[str(member.id)] - old_game_data[str(member.id)]

    # not in both
    if str(member.id) not in old_game_data and str(member.id) not in new_game_data:
        return 0

    # in any of them
    if str(member.id) in new_game_data:
        return new_game_data[str(member.id)]

    else:
        return 0


async def strike_player(member: discord.Member, strike_count: int, team_name: str):
    if not member:
        return

    sheet = betterspread.Sheet(
        "OFFICIAL NHL ROSTER SHEET",
        connection=betterspread.Connection("./credentials.json"),
    )
    strikes_tab = await sheet.get_tab("Strikes")
    strikes = await strikes_tab.values()

    for row in strikes:
        if row[2] == str(member.id):
            current = int(row[4])
            cell = row[4]
            await cell.update(str(current + strike_count))
            break
    else:
        now = datetime.datetime.utcnow()
        await strikes_tab.append(
            [
                member.display_name,
                team_name,
                str(member.id),
                f"{now.month}/{now.day}/{now.year}",
                str(strike_count),
            ]
        )


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
    team_name = get_team_name(guild.name)

    for member in checking_members:
        games_played = get_played_games(old_data, new_data, member)

        if games_played < 3:
            strike_count = 3 - games_played

            while True:
                try:
                    await strike_player(
                        member, strike_count, guild.name.split("CNC ")[1]
                    )
                    break
                except gspread.exceptions.APIError as error:
                    if error.code == 429:
                        await asyncio.sleep(65)
                    else:
                        break

            not_minimum.append([member, games_played, ecu in member.roles])

    if not_minimum:
        cnc_team_channel = get(
            bot.SUPPORT_GUILD.text_channels,
            name=f"╟・{team_name}",
        )

        mentions = "### Players who did not play minimum 3 games this week\n"
        for player_data in not_minimum:
            strike_count = 3 - int(player_data[1])
            mentions += (
                f"- {player_data[0].mention} ({player_data[0].id}){' (ECU)' if player_data[2] else ''} "
                f"played **{player_data[1]}** games. Got {strike_count} strikes\n"
            )

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
