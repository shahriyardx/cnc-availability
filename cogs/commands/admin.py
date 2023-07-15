from datetime import datetime

from nextcord import (CategoryChannel, Embed, Member, PermissionOverwrite,
                      SlashOption)
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from utils.gspread import DataSheet


class UtilityCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma
        self.roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.draft_sheet = DataSheet("NHL Live Draft Sheet")

    @slash_command(description="Sync your roles and nickname with Roster sheet")
    async def sync(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if member.guild.id in Data.IGNORED_GUILDS:
            return
        cnc_member = self.bot.SUPPORT_GUILD.get_member(member.id)

        if not cnc_member:
            return

        team_name = member.guild.name.split(" ", maxsplit=1)[1].strip()
        right_team = get(cnc_member.roles, name=team_name)

        if not right_team:
            return await interaction.edit_original_message(
                content="Unable to sync, You do not belong to this team"
            )

        role_names = {
            "LW": "Left Wing",
            "RW": "Right Wing",
            "LD": "Left Defense",
            "RD": "Right Defense",
            "G": "Goalie",
            "C": "Center",
        }

        all_roster = self.draft_sheet.get_values("Data import")

        for row in all_roster[1:]:
            try:
                member_id = int(row[3])
            except (ValueError, TypeError):
                continue

            if member_id == member.id:
                team_role = get(member.guild.roles, name="Team")
                await member.add_roles(team_role)
                await member.edit(nick=row[0])

                primary_position = get(member.guild.roles, name=role_names.get(row[1]))
                secondary_position = get(
                    member.guild.roles, name=role_names.get(row[2])
                )

                if primary_position:
                    await member.add_roles(primary_position)

                if secondary_position:
                    await member.add_roles(secondary_position)

                return await interaction.edit_original_message(
                    content="Role and nickname has been synced"
                )
        return await interaction.edit_original_message(
            content="Your data is not available on the roster sheet"
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


def setup(bot: IBot):
    bot.add_cog(UtilityCommands(bot))
