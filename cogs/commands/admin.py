import json
import traceback
import asyncio
import nextcord
from nextcord import SlashOption
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from utils.gspread import DataSheet
from essentials.data import team_names
from .utils import (
    sync_player,
    get_custom_member,
    CustomMember,
    CustomRole,
    valid_member,
    get_duplicate,
)
from ..task.utils import report_games_played, get_week, get_team_name
from .views import StagePlayers
from datetime import datetime
from pytz import timezone
from betterspread import Sheet, Connection, Row
from typing import List

con = Connection("./credentials.json")


roster_sheet = Sheet("OFFICIAL NHL ROSTER SHEET", connection=con)
draft_sheet = Sheet("NHL Live Draft Sheet", connection=con)
nick_sheet = Sheet("Official Nickname Updates", connection=con)


def can_submit(day):
    now = datetime.now(tz=timezone("EST"))
    weekday = now.weekday()

    days = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    if weekday < days[day]:
        return True
    else:
        if weekday > 3:
            return None

        last_time = datetime(
            now.year, now.month, now.day, 20, 30, 0, 0, tzinfo=timezone("EST")
        )

        return now < last_time


class UtilityCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma

    @slash_command(description="Sync your roles and nickname with Roster sheet")
    async def sync(
        self,
        interaction: Interaction,
        player: nextcord.Member = SlashOption(
            description="The member to sync", required=False
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if player and interaction.user.id in [696939596667158579, 810256917497905192]:
            player = player or interaction.user
        else:
            player = interaction.user

        try:
            await sync_player(self.bot, player)
        except Exception as e:
            traceback.print_exc()
            return await interaction.edit_original_message(
                content=f"Error occured during sync: {e}"
            )

        return await interaction.edit_original_message(content="Sync finished")

    @slash_command(description="Enable or disable tasks")
    async def toggle_tasks(
        self,
        interaction: Interaction,
        status: bool = SlashOption(
            name="status", description="True = Enabled, False = Disabled", required=True
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return await interaction.followup.send(
                content="You don't have permission to run this command"
            )

        settings = await self.prisma.settings.find_first()
        await self.prisma.settings.update(
            where={"id": settings.id},
            data={
                "tasks_enabled": status,
            },
        )

        self.bot.tasks_enabled = status
        await interaction.edit_original_message(
            content=f"Tasks has been {'Enabled' if status else 'Disabled'}"
        )

    @slash_command(description="Enable of disable playoffs")
    async def toggle_playoffs(
        self,
        interaction: Interaction,
        status: bool = SlashOption(
            name="status", description="True = Enabled, False = Disabled", required=True
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return await interaction.followup.send(
                content="You don't have permission to run this command"
            )

        settings = await self.prisma.settings.find_first()
        await self.prisma.settings.update(
            where={"id": settings.id},
            data={
                "playofss": status,
            },
        )

        self.bot.playoffs = status
        await interaction.edit_original_message(
            content=f"Playoffs has been {'Enabled' if status else 'Disabled'}"
        )

    @slash_command(description="Reset ir of a player")
    async def resetir(
        self,
        interaction: Interaction,
        player: nextcord.Member = SlashOption(
            description="The player to reset ir", required=True
        ),
    ):
        await interaction.response.defer()

        if interaction.guild_id != 831166408888942623:
            return await interaction.followup.send(f"This server is not allowed")

        guild_map = {}
        for guild in self.bot.guilds:
            guild_map[guild.name] = guild

        member: nextcord.Member = None  # noqa
        team_name: str = None  # noqa
        team_guild: nextcord.Guild = None  # noqa

        for role in player.roles:
            if role.name in team_names:
                team_guild = guild_map.get(f"CNC {role.name}")
                if team_guild:
                    guild_member = team_guild.get_member(player.id)
                    if guild_member:
                        member = guild_member
                        break

        if not member:
            return await interaction.followup.send(
                content="Unable to find the team of this player."
            )

        sub_role = get(team_guild.roles, name="Availability Submitted")
        ir_role = get(team_guild.roles, name="IR")

        if sub_role:
            await member.remove_roles(sub_role)
        if ir_role:
            await member.remove_roles(ir_role)

        ir_tab = await roster_sheet.get_tab("IR")
        ir_entry: List[Row] = await ir_tab.values()
        ir_entry.reverse()

        for entry in ir_entry:
            if entry[1] == player.display_name:
                await entry.delete()

        chat = get(team_guild.text_channels, name="chat")
        if chat:
            await chat.send(
                content=f"{member.mention} Your Availability has been reset "
                "please Submit availability again."
            )

        await interaction.edit_original_message(
            content=f"{player.mention}'s IR has been reset succesfully"
        )

    @slash_command(description="Sync nicknames from sheet")
    async def syncall(
        self,
        interaction: Interaction,
        team: nextcord.Role = SlashOption(description="Team role", required=False),
    ):
        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return

        await interaction.response.defer()
        await interaction.edit_original_message(content="Sync process has been started")
        msg = await interaction.guild.get_channel(interaction.channel_id).send(
            content="Sync all is about to start.."
        )

        guilds = self.bot.guilds
        if team:
            for guild in self.bot.guilds:
                if f"CNC {team.name}" == guild.name:
                    guilds = [guild]
                    break

        for guild in guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            unable_to_sync = []
            await msg.edit(content=f"Syncing {guild.name}...")
            for member in guild.members:
                if member.bot:
                    continue

                try:
                    await sync_player(self.bot, member)
                    await asyncio.sleep(5)
                except:  # noqa
                    exc = traceback.format_exc()
                    unable_to_sync.append([member, exc])
                    continue

            if unable_to_sync:
                member_list = ""
                for us in unable_to_sync:
                    member_list += (
                        f"- {us[0].display_name} {us[0].id} \n```sh\n{us[1]}\n```"
                    )

                await interaction.guild.get_channel(interaction.channel_id).send(
                    content=f"Unable to sync for **{guild.name}**\n {member_list}"
                )

            await msg.edit(
                content=f"Finished syncing {guild.name}. Next server sync in 10 minutes"
            )
            await asyncio.sleep(3 * 60)

        await msg.edit(content="All servers has been synced")

    @slash_command(description="sync nickname in official cnc discord")
    async def syncnick(
        self,
        interaction: Interaction,
        target: nextcord.Member = SlashOption(
            description="member to sync nick", required=False
        ),
    ):
        await interaction.response.defer()

        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return await interaction.followup.send(
                content="You don't have permission to run this command"
            )

        await interaction.edit_original_message(content="Nickname sync started")

        all_members = [member for member in interaction.guild.members if not member.bot]
        synced = 0

        msg = await interaction.guild.get_channel(interaction.channel_id).send(
            content=f"Synced {synced}/{len(all_members)}"
        )

        data_tab = await nick_sheet.get_tab("data")
        nick_data = await data_tab.values()
        nicks = {}

        for row in nick_data[1:]:
            try:
                uid = int(row[0].strip())
            except ValueError:
                continue

            is_member = interaction.guild.get_member(uid)
            if is_member:
                nicks[uid] = row[1].strip()

        if target:
            all_members = [target]

        for m in all_members:
            if m.id in nicks:
                await m.edit(nick=nicks[m.id])
                synced += 1

                if synced % 10 == 0:
                    await msg.edit(content=f"Synced {synced}/{len(all_members)}")

                if len(all_members) > 1:
                    await asyncio.sleep(5)

        await interaction.guild.get_channel(interaction.channel_id).send(
            content="Nick sync has been finished"
        )

    @slash_command(description="Report stats of a specific server")
    async def report_stats(
        self,
        interaction: Interaction,
        team: nextcord.Role = SlashOption(description="The team role", required=True),
    ):
        await interaction.response.defer()

        week = get_week()
        last_week = week - 1

        old_data = dict()
        new_data = dict()

        old_game_data = await self.bot.prisma.game.find_first(where={"week": last_week})
        new_week_data = await self.bot.prisma.game.find_first(where={"week": week})

        if old_game_data:
            old_data = json.loads(old_game_data.data)

        if new_week_data:
            new_data = json.loads(new_week_data.data)

        guild = get(self.bot.guilds, name=f"CNC {team.name}")
        data = await report_games_played(
            self.bot, guild, old_data, new_data, return_first=True
        )

        await interaction.followup.send(content=data)

    @slash_command(description="See a player's stats")
    async def player_stats(
        self,
        interaction: Interaction,
        player: nextcord.Member = SlashOption(description="The player", required=False),
    ):
        await interaction.response.defer()

        if not player:
            player = interaction.user

        old_game_data = await self.bot.prisma.game.find_many(order={"week": "asc"})
        datas = [[json.loads(data.data), data.week] for data in old_game_data]

        games_played = {}

        for data_week in datas:
            data = data_week[0]
            week = data_week[1]

            games_played[week] = 0

            if player.nick in data:
                current_week_data = data[player.nick]
                games_played[week] = current_week_data

        message = f"# Stats for {player.nick}\n"
        for index, key in enumerate(games_played.keys()):
            last_played = games_played.get(key - 1, 0)
            this_played = games_played.get(key, 0)
            total_played = max(this_played - last_played, 0)

            message += f"- Week {index + 1}: **{total_played}** Games\n"

        await interaction.followup.send(content=message)

    async def submitted(self, member_id: int, day: str, time: str):
        data = await self.bot.prisma.availabilitysubmitted.find_first(
            where={"member_id": member_id, "day": day, "time": time}
        )

        if data:
            return True

        return False

    async def is_available(self, member: nextcord.Member, day: str, time: str):
        result = await self.bot.prisma.availabilitysubmitted.find_first(
            where={"member_id": member.id, "day": day, "time": time}
        )

        if result:
            return True

        return False

    async def get_players(self, interaction: Interaction, day: str, time: str):  # noqa
        lw_role = get(interaction.guild.roles, name="Left Wing")
        rw_role = get(interaction.guild.roles, name="Right Wing")
        ld_role = get(interaction.guild.roles, name="Left Defense")
        rd_role = get(interaction.guild.roles, name="Right Defense")
        c_role = get(interaction.guild.roles, name="Center")
        g_role = get(interaction.guild.roles, name="Goalie")
        owner_role = get(interaction.guild.roles, name="Owner")
        gm_role = get(interaction.guild.roles, name="General Manager")

        owner_membners = [
            get_custom_member(member)
            for member in owner_role.members
            if valid_member(member)
        ]
        gm_membners = [
            get_custom_member(member)
            for member in gm_role.members
            if valid_member(member)
        ]

        lw_members = [
            get_custom_member(member)
            for member in lw_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]
        rw_members = [
            get_custom_member(member)
            for member in rw_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]
        g_members = [
            get_custom_member(member)
            for member in g_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]
        ld_members = [
            get_custom_member(member)
            for member in ld_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]
        rd_members = [
            get_custom_member(member)
            for member in rd_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]
        c_members = [
            get_custom_member(member)
            for member in c_role.members
            if valid_member(member) and await self.is_available(member, day, time)
        ]

        lw_rw_c = [
            CustomMember(id=1, nick="ECU", roles=[CustomRole("ECU")]),
            *{*lw_members, *rw_members, *c_members, *owner_membners, *gm_membners},
        ]

        ld_rd = [
            CustomMember(id=1, nick="ECU", roles=[CustomRole("ECU")]),
            *{*ld_members, *rd_members, *owner_membners, *gm_membners},
        ]
        g = [
            CustomMember(id=1, nick="ECU", roles=[CustomRole("ECU")]),
            *{*g_members, *owner_membners, *gm_membners},
        ]

        return [lw_rw_c, ld_rd, g]

    async def send_lineup_message(
        self, lineup, interaction: Interaction, data: dict, day: str, time: str
    ):
        msg = ""
        mentions = ""
        for key, value in data.items():
            if value == 1:
                mention = "Generic ECU"
            else:
                member = interaction.guild.get_member(value)
                if member:
                    mention = member.mention
                    mentions += f"{member.mention} "
                else:
                    mention = f"Unknown Member, ID: `{value}`"

            msg += f"{key}: {mention}\n"

        embed = nextcord.Embed(title=f"{day} - {time}")
        embed.description = msg
        embed.set_thumbnail(interaction.guild.icon.url)

        await interaction.channel.send(content="Lineup ID: ")
        await interaction.channel.send(content=f"{lineup.id}")
        await interaction.channel.send(embed=embed)

    @slash_command(description="Testing new avail", name="set-lineups")
    async def set_lineups(
        self,
        interaction: Interaction,
        day: str = SlashOption(
            description="day",
            required=True,
            choices={
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
            },
        ),
        time: str = SlashOption(
            description="day",
            required=True,
            choices={"8:30pm": "8:30pm", "9:10pm": "9:10pm", "9:50pm": "9:50pm"},
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        can = can_submit(day)

        if can is None:
            return await interaction.followup.send(
                content="You can't submit lineups right now"
            )
        elif not can:
            return await interaction.followup.send(
                content=f"You can't submit lineups for `{day}` right now"
            )

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.followup.send(
                content="Lineups can't be submitted in this channel"
            )

        owner = get(interaction.user.roles, name="Owner")
        gm = get(interaction.user.roles, name="General Manager")

        if interaction.user.id not in [810256917497905192, 696939596667158579]:
            if not owner and not gm:
                return await interaction.followup.send(
                    content="You don't have permission to set or edit lineups"
                )

        team_name = get_team_name(interaction.guild.name)
        prev = await self.bot.prisma.lineup.find_first(
            where={"team": team_name, "day": day, "time": time}
        )

        if prev:
            return await interaction.followup.send(
                content=f"Lineup already exists. ID: {prev.id}"
            )

        lw_rw_c, ld_rd, g = await self.get_players(interaction, day, time)

        data = {}

        first_stage = StagePlayers(lw_rw_c, lw_rw_c, lw_rw_c, ["LW", "RW", "C"])
        await interaction.edit_original_message(
            content="Select players", view=first_stage
        )

        cancelled = await first_stage.wait()
        if first_stage.cancelled or cancelled:
            return await interaction.edit_original_message(
                content="Cancelled", view=None
            )

        data.update(first_stage.data)

        second_stage = StagePlayers(ld_rd, ld_rd, g, ["LD", "RD", "G"])
        await interaction.edit_original_message(
            content="Select players", view=second_stage
        )

        cancelled = await second_stage.wait()
        if second_stage.cancelled or cancelled:
            return await interaction.edit_original_message(
                content="Cancelled", view=None
            )

        data.update(second_stage.data)
        dup = get_duplicate(data)

        if dup:
            return await interaction.edit_original_message(
                content=f"Can't have same player for multiple position, {dup}"
            )

        lineup = await self.bot.prisma.lineup.create(
            {"data": json.dumps(data), "day": day, "time": time, "team": team_name}
        )

        await self.send_lineup_message(lineup, interaction, data, day, time)
        await interaction.edit_original_message(
            content=f"Lineup submitted, ID: `{lineup.id}`", view=None
        )

    @slash_command(description="Testing new avail", name="edit-lineups")
    async def edit_lineup(
        self,
        interaction: Interaction,
        lineup_id: str = SlashOption(description="The id of the lineup to edit"),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.followup.send(
                content="Lineups can't be editted in this channel"
            )

        owner = get(interaction.user.roles, name="Owner")
        gm = get(interaction.user.roles, name="General Manager")

        if interaction.user.id not in [810256917497905192, 696939596667158579]:
            if not owner and not gm:
                return await interaction.followup.send(
                    content="You don't have permission to set or edit lineups"
                )

        old_lineup = await self.bot.prisma.lineup.find_first(
            where={"id": lineup_id, "team": get_team_name(interaction.guild.name)}
        )
        if not old_lineup:
            return await interaction.followup.send(content="Lineup not found")

        data = json.loads(old_lineup.data)
        lw_rw_c, ld_rd, g = await self.get_players(
            interaction, old_lineup.day, old_lineup.time
        )

        first_stage = StagePlayers(
            lw_rw_c, lw_rw_c, lw_rw_c, ["LW", "RW", "C"], defaults=data
        )
        await interaction.edit_original_message(
            content="Select players", view=first_stage
        )

        cancelled = await first_stage.wait()
        if first_stage.cancelled or cancelled:
            return await interaction.edit_original_message(
                content="Cancelled", view=None
            )

        data.update(first_stage.data)

        second_stage = StagePlayers(ld_rd, ld_rd, g, ["LD", "RD", "G"], defaults=data)
        await interaction.edit_original_message(
            content="Select players", view=second_stage
        )

        cancelled = await second_stage.wait()
        if second_stage.cancelled or cancelled:
            return await interaction.edit_original_message(
                content="Cancelled", view=None
            )

        data.update(second_stage.data)
        dup = get_duplicate(data)

        if dup:
            return await interaction.edit_original_message(
                content=f"Can't have same player for multiple position, {dup}"
            )

        await self.bot.prisma.lineup.update(
            where={"id": old_lineup.id}, data={"data": json.dumps(data)}
        )

        await self.send_lineup_message(
            old_lineup, interaction, data, old_lineup.day, old_lineup.time
        )
        await interaction.edit_original_message(
            content=f"Lineup Edited, ID: `{old_lineup.id}`", view=None
        )

    @slash_command(description="get lineup data", name="gameday-lineups")
    async def gameday_lineups(
        self,
        interaction: Interaction,
        day: str = SlashOption(
            description="The day to check games",
            required=True,
            choices={
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
            },
        ),
    ):
        await interaction.response.defer()

        data = await self.bot.prisma.lineup.find_many(
            where={"day": day, "team": get_team_name(interaction.guild.name)}
        )

        if not data:
            return await interaction.followup.send(content="No lineup found")

        lineupsChannel = get(interaction.guild.channels, name="lineups")
        support_guild = self.bot.get_guild(Data.SUPPORT_GUILD)
        team_log_channel = get(
            support_guild.text_channels,
            name=f"╟・{get_team_name(interaction.guild.name)}",
        )

        for lineup in data:
            lineup_data = json.loads(lineup.data)

            msg = ""
            mentions = ""
            for key, value in lineup_data.items():
                if value == 1:
                    mention = "Generic ECU"
                else:
                    member = interaction.guild.get_member(value)
                    if member:
                        mention = member.mention
                        mentions += f"{member.mention} "
                    else:
                        mention = f"Unknown Member, ID: `{value}`"

                msg += f"{key}: {mention}\n"

            embed = nextcord.Embed(title=f"{day} - {lineup.time}")
            embed.description = msg
            embed.set_thumbnail(interaction.guild.icon.url)

            if lineupsChannel:
                await lineupsChannel.send(content=mentions, embed=embed)

            if team_log_channel:
                await team_log_channel.send(content=mentions, embed=embed)

        await interaction.edit_original_message(content="Completed")

    @slash_command(description="get lineup data", name="sync-team")
    async def sync_team(self, i: Interaction):
        await i.response.defer()
        owner_or_gm = get(i.user.roles, name="Owner") or get(
            i.user.roles, name="General Manager"
        )

        if not owner_or_gm and i.user.id not in [
            810256917497905192,
            696939596667158579,
        ]:
            return await i.edit_original_message(
                content="You are not allowed to run this command"
            )

        if i.guild.id in [831166408888942623]:
            return await i.edit_original_message(content="Can't run on this server")

        team_role = get(i.guild.roles, name="Team")
        if not team_role:
            return await i.edit_original_message(content="Team role not found")

        values = await (await roster_sheet.get_tab(i.guild.name[4:])).values()
        players = []

        for row in values:
            try:
                players.append(int(row[5]))
            except:  # noqa
                pass

            try:
                players.append(int(row[1]))
            except:  # noqa
                pass

        for member in i.guild.members:
            if member.bot:
                continue

            if member.id not in players and member.id not in [
                810256917497905192,
                696939596667158579,
            ]:
                try:
                    await member.kick(reason="Not on roster")
                except:  # noqa
                    pass

        await i.edit_original_message(
            content="Removing non-roster members finished, Working on syncing existing members..."
        )

        team_name = i.guild.name.split(" ", maxsplit=1)[1].strip()

        team_tab = await roster_sheet.get_tab(team_name)
        all_roster = await team_tab.values()

        ids = [
            await team_tab.get_cell("B27"),
            await team_tab.get_cell("B28"),
            await team_tab.get_cell("B29"),
        ]

        for pid in players:
            m = i.guild.get_member(pid)
            if not m:
                continue

            try:
                await i.edit_original_message(content=f"Syncing {m.mention}")
                await sync_player(self.bot, m, all_roster, team_tab, ids)
                await asyncio.sleep(3)
            except Exception as e:  # noqa
                traceback.print_exc()
                await i.channel.send(content=f"Syncing {m.mention} failed. Reason: {e}")

        await i.edit_original_message(content="Finished")


def setup(bot: IBot):
    bot.add_cog(UtilityCommands(bot))
