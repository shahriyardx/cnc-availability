from nextcord import SlashOption
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from utils.gspread import DataSheet


def get_number(value):
    print(f'Value: {value}')
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


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

        owner_id = get_number(self.draft_sheet.get_value(team_name, "B27")[0][0])
        gm_id = get_number(self.draft_sheet.get_value(team_name, "B28")[0][0])
        agm_id = get_number(self.draft_sheet.get_value(team_name, "B29")[0][0])

        print(owner_id, gm_id, agm_id, member.id)

        if owner_id == member.id:
            nick = self.draft_sheet.get_value(team_name, "A27")[0][0]
            owner_role = get(member.guild.roles, name="Owner")
            team_role = get(member.guild.roles, name="Team")
            await member.add_roles(owner_role)
            await member.remove_roles(team_role)
            if nick:
                await member.edit(nick=nick)

        elif gm_id == member.id:
            nick = self.draft_sheet.get_value(team_name, "A28")[0][0]
            gm_role = get(member.guild.roles, name="General Manager")
            team_role = get(member.guild.roles, name="Team")
            await member.add_roles(gm_role)
            await member.remove_roles(team_role)

            if nick:
                await member.edit(nick=nick)

        elif agm_id == member.id:
            agm_role = get(member.guild.roles, name="AGM")
            await member.add_roles(agm_role)

        else:
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
            content="Your roles has been synced"
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
