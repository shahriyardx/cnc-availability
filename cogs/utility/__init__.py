from nextcord import Member, Role, SlashOption
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import IBot
from essentials.views import Positions


class UilityCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma

    @slash_command(
        description="Get your positions",
    )
    async def positions(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        position_view = Positions()

        await interaction.edit_original_message(view=position_view)
        await position_view.wait()

        position_roles = {
            "LW": get(interaction.guild.roles, name="Left Wing"),
            "RW": get(interaction.guild.roles, name="Right Wing"),
            "LD": get(interaction.guild.roles, name="Left Defense"),
            "RD": get(interaction.guild.roles, name="Right Defense"),
            "C": get(interaction.guild.roles, name="Center"),
            "G": get(interaction.guild.roles, name="Goalie"),
        }

        selected_positions = []
        for position in position_view._selects:  # noqa
            selected_positions.append(position_roles[position])

        await interaction.user.add_roles(*selected_positions)
        await interaction.edit_original_message(
            content=f"You have assigned to positions {', '.join(position_view._selects)}",  # noqa
            view=None,
        )

    @slash_command(description="Assign new role to players")
    async def assignrole(
        self,
        interaction: Interaction,
        role: Role = SlashOption(
            name="role",
            description="Select the role you want to give",
        ),
        player: Member = SlashOption(
            name="player",
            description="Select the player you want to give role",
        ),
    ):
        await interaction.response.defer()

        if interaction.user.id == interaction.guild.owner_id:
            print("As Guid owner")
            await player.add_roles(role)
            return await interaction.followup.send(content=f"{role} has been added to {player}")

        highest_role = None

        if get(interaction.user.roles, name="Owner"):
            print("As Owner")
            highest_role = get(interaction.guild.roles, name="Owner")

        if get(interaction.user.roles, name="General Manager"):
            print("As GM")
            highest_role = get(interaction.guild.roles, name="General Manager")

        if not highest_role:
            return await interaction.followup.send(content="You can't remove roles")

        if role > highest_role:
            return await interaction.followup.send("Can't remove this role")

        if highest_role:
            print(f"Adding role {role} to {player}")
            await player.add_roles(role)
            return await interaction.followup.send(content=f"{role} has been added to {player}")

        await interaction.edit_original_message(content="You can't add roles")

    @slash_command(description="Remove roles from player")
    async def removerole(
        self,
        interaction: Interaction,
        role: Role = SlashOption(
            name="role",
            description="Select the role you want to remove",
        ),
        player: Member = SlashOption(
            name="player",
            description="Select the player you want to remove role from",
        ),
    ):
        await interaction.response.defer()

        if interaction.user.id == interaction.guild.owner_id:
            print("As Guid owner")
            await player.remove_roles(role)
            return await interaction.followup.send(content=f"{role} has been removed from {player}")

        highest_role = None

        if get(interaction.user.roles, name="Owner"):
            print("As Owner")
            highest_role = get(interaction.guild.roles, name="Owner")

        if get(interaction.user.roles, name="General Manager"):
            print("As GM")
            highest_role = get(interaction.guild.roles, name="General Manager")

        if not highest_role:
            return await interaction.followup.send(content="You can't remove roles")

        if role > highest_role:
            return await interaction.followup.send("Can't remove this role")

        if highest_role:
            print(f"Removing {role} from {player}")
            await player.remove_roles(role)
            return await interaction.followup.send(content=f"{role} has been removed from {player}")

    @slash_command(description="Change psn")
    async def psn(
        self,
        interaction: Interaction,
        new_psn: str = SlashOption(name="new_psn", description="Your new psn"),
    ):
        await interaction.response.defer()

        await interaction.user.edit(nick=new_psn)
        await interaction.edit_original_message(content="PSN has been updated.")

    @slash_command(description="Change color of a role")
    @commands.has_any_role("Owner", "General Manager")
    async def changecolor(
        self,
        interaction: Interaction,
        role: Role = SlashOption(name="role", description="The role to change color", required=True),
        color: str = SlashOption(name="color", description="The new color code. e.g. #ffffff"),
    ):
        await interaction.response.defer()

        try:
            code = color.replace("#", "")
            code = int(code, 16)
        except ValueError:
            return await interaction.edit_original_message(content=f"Invalid color code {color}")

        try:
            await role.edit(color=code)
        except:  # noqa
            return await interaction.edit_original_message(content="Unable to change color.")

        await interaction.edit_original_message(content="Role color changed")


def setup(bot: IBot):
    bot.add_cog(UilityCommands(bot))
