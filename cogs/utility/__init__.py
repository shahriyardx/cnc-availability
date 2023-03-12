from nextcord import Embed, Member, Role, SlashOption
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
        for position in position_view._selects:
            selected_positions.append(position_roles[position])

        await interaction.user.add_roles(*selected_positions)
        await interaction.edit_original_message(
            content=f"You have assigned to positions {', '.join(position_view._selects)}",
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
        if interaction.user.id != interaction.guild.owner_id:
            is_owner = get(interaction.user.roles, name="Owner")
            is_gm = get(interaction.user.roles, name="General Manager")
            
            if not is_owner or not is_gm:
                return await interaction.edit_original_message(
                    content="You can't assign roles"
                )

            if is_owner:
                highest_role = get(interaction.guild.roles, name="Owner")

            if not is_owner and is_gm:
                highest_role = get(interaction.guild.roles, name="General Manager")
                

            if role > highest_role:
                return await interaction.followup.send("Can't assign this role")

        await player.add_roles(role)
        await interaction.followup.send(content=f"{role} has been added to {player}")

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
        role: Role = SlashOption(
            name="role", description="The role to change color", required=True
        ),
        color: str = SlashOption(
            name="color", description="The new color code. e.g. #ffffff"
        ),
    ):
        await interaction.response.defer()

        try:
            code = color.replace("#", "")
            code = int(code, 16)
        except ValueError:
            return await interaction.edit_original_message(
                content=f"Invalid color code {color}"
            )

        try:
            await role.edit(color=code)
        except:
            return await interaction.edit_original_message(
                content="Unable to change color."
            )

        await interaction.edit_original_message(content="Role color changed")
    
    @slash_command(name="get-mention", description="Get mention of a command")
    async def get_mention(self, interaction: Interaction, command_name: str = SlashOption(description="The command name")):
        await interaction.response.defer()
        mention = self.bot.get_command_mention(interaction.guild.id, command_name)
        await interaction.edit_original_message(content=f"{mention} `{mention}`")


def setup(bot: IBot):
    bot.add_cog(UilityCommands(bot))
