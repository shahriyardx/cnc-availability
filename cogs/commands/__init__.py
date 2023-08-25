from nextcord import CategoryChannel, PermissionOverwrite, SlashOption
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from utils.gspread import DataSheet

from .utils import append_into_ir


def get_over(state):
    overwrites = PermissionOverwrite()
    overwrites.manage_channels = state  # noqa
    overwrites.manage_permissions = state  # noqa
    overwrites.send_messages = state  # noqa
    overwrites.view_channel = state  # noqa
    overwrites.create_public_threads = state  # noqa
    overwrites.create_private_threads = state  # noqa
    overwrites.send_messages_in_threads = state  # noqa
    overwrites.embed_links = state  # noqa
    overwrites.attach_files = state  # noqa
    overwrites.add_reactions = state  # noqa
    overwrites.use_external_emojis = state  # noqa
    overwrites.mention_everyone = state  # noqa
    overwrites.manage_messages = state  # noqa
    overwrites.read_message_history = state  # noqa

    return overwrites


class TaskerCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma
        self.roster_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.draft_sheet = DataSheet("NHL Live Draft Sheet")

    @slash_command(name="create-category", description="Create category")
    @commands.has_any_role("Owner", "General Manager")
    async def create_category(
        self,
        interaction: Interaction,
        category_name: str = SlashOption(name="category_name", description="The category name"),
    ):
        await interaction.response.defer(ephemeral=True)

        everyone = get(interaction.guild.roles, name="@everyone")
        owner = get(interaction.guild.roles, name="Owner")
        gm = get(interaction.guild.roles, name="General Manager")

        await interaction.guild.create_category(
            name=category_name,
            overwrites={
                everyone: get_over(False),
                owner: get_over(True),
                gm: get_over(True),
            },
        )

        await interaction.edit_original_message(content="Category created")

    @slash_command(name="create-channel", description="Create Channel")
    @commands.has_any_role("Owner", "General Manager")
    async def create_channel(
        self,
        interaction: Interaction,
        channel_name: str = SlashOption(name="channel_name", description="The channel name"),
        category: CategoryChannel = SlashOption(name="category", description="Mention the category"),
    ):
        await interaction.response.defer(ephemeral=True)

        exists = get(interaction.guild.text_channels, name=channel_name)

        if exists:
            return await interaction.edit_original_message(content="Can't create channel with this name")

        everyone = get(interaction.guild.roles, name="@everyone")
        owner = get(interaction.guild.roles, name="Owner")
        gm = get(interaction.guild.roles, name="General Manager")

        await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites={
                everyone: get_over(False),
                owner: get_over(True),
                gm: get_over(True),
            },
        )

        await interaction.edit_original_message(content="Channel created")

    @slash_command(name="create-role", description="Create a role")
    @commands.has_any_role("Owner", "General Manager")
    async def create_role(
        self,
        interaction: Interaction,
        name: str = SlashOption(name="name", description="The role name"),
    ):
        await interaction.response.defer(ephemeral=True)

        exists = get(interaction.guild.roles, name=name)

        if exists:
            return await interaction.edit_original_message(content="Can't create role with this name")

        await interaction.guild.create_role(name=name)
        await interaction.edit_original_message(content="Role created")

    async def toggle_state(self, channel, role, state):
        def get_permissions(_state: bool):
            permission_overwrites = PermissionOverwrite()
            permission_overwrites.send_messages = _state  # noqa
            permission_overwrites.view_channel = _state  # noqa

            return permission_overwrites

        await channel.set_permissions(target=role, overwrite=get_permissions(_state=state))

    @slash_command(
        name="toggle-availability",
        description="Forces availability submit channel top open anytime",
    )
    @commands.is_owner()
    async def toggle_availability(
        self,
        interaction: Interaction,
        state: bool = SlashOption(
            name="state",
            description="The channel state",
            choices={"Lock": False, "Unlock": True},
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != interaction.guild.owner.id:
            return await interaction.followup.send(content="You are not allowed to run this command")

        for guild in self.bot.guilds:
            if guild.id in Data.IGNORED_GUILDS:
                continue

            SUBMIT_CHANNEL = get(guild.text_channels, name=Data.AVIAL_SUBMIT_CHANNEL)  # `#submmit-availability`
            TEAM_ROLE = get(
                guild.roles,
                name=Data.PLAYERS_ROLE,
            )
            if SUBMIT_CHANNEL:
                await self.toggle_state(SUBMIT_CHANNEL, TEAM_ROLE, state)

        await interaction.followup.send(content=f"Availavility has been {'Unlocked' if state else 'Locked'}")


def setup(bot: IBot):
    bot.add_cog(TaskerCommands(bot))
