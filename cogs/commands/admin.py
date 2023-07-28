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
from .utils import sync_player
import datetime

class UtilityCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma
        self.roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.draft_sheet = DataSheet("NHL Live Draft Sheet")
        self.nick_sheet = DataSheet("Official Nickname Updates")

    @slash_command(description="Sync your roles and nickname with Roster sheet")
    async def sync(
            self,
            interaction: Interaction,
            player: nextcord.Member = SlashOption(description="The member to sync", required=False),
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
            return interaction.edit_original_message(content=f"Error occured during sync: {e}")

        return await interaction.edit_original_message(
            content="Sync finished"
        )

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

        ir_entry: list = self.roster_sheet.get_values("IR")
        ir_entry.reverse()
        for index, entry in enumerate(ir_entry):
            if entry[1] == player.display_name:
                self.roster_sheet.delete_row("IR", len(ir_entry) - index)

        chat = get(team_guild.text_channels, name="chat")
        if chat:
            await chat.send(
                content=(
                    f"{member.mention} Your Availability has been reset "
                    "please Submit availability again."
                )
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
        msg = await interaction.guild.get_channel(interaction.channel_id).send(content="Sync all is about to start..")

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
                    print(f"Syncing {member.display_name}")
                    await sync_player(self.bot, member)
                    await asyncio.sleep(10)
                except: # noqa
                    exc = traceback.format_exc()
                    print(exc)
                    unable_to_sync.append([member, exc])
                    continue

            if unable_to_sync:
                member_list = ""
                for us in unable_to_sync:
                    member_list += f"- {us[0].display_name} {us[0].id} \n```sh\n{us[1]}\n```"

                await interaction.guild.get_channel(interaction.channel_id).send(
                    content=f"Unable to sync for **{guild.name}**\n {member_list}"
                )

            await msg.edit(content=f"Finished syncing {guild.name}. Next server sync in 10 minutes")
            await asyncio.sleep(3 * 60)

        await msg.edit(content="All servers has been synced")

    @slash_command(description="sync nickname in official cnc discord")
    async def syncnick(
        self,
        interaction: Interaction,
        member: nextcord.Member = SlashOption(description="member to sync nick", required=False)
    ):
        await interaction.response.defer()

        if interaction.user.id not in [696939596667158579, 810256917497905192]:
            return await interaction.followup.send(
                content="You don't have permission to run this command"
            )

        await interaction.edit_original_message(content="Nickname sync started")

        nick_data = self.nick_sheet.get_values("data")
        nicks = {}

        for row in nick_data[1:]:
            try:
                uid = int(row[0].strip())
            except ValueError:
                continue

            member = interaction.guild.get_member(uid)
            if member:
                nicks[uid] = row[1].strip()
        print(nicks)

        all_members = [member for member in interaction.guild.members if not member.bot]
        if member:
            all_members = [member]

        print(all_members)

        for m in all_members:
            print(m.id in nicks)

            if m.id in nicks:
                await m.edit(nick=nicks[m.id])
                if len(all_members) > 1:
                    await asyncio.sleep(5)

        await interaction.guild.get_channel(interaction.channel_id).send(content="Nick sync has been finished")


def setup(bot: IBot):
    bot.add_cog(UtilityCommands(bot))
