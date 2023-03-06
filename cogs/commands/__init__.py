from datetime import datetime

from nextcord import Embed, Member, SlashOption, PermissionOverwrite, CategoryChannel
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from essentials.views import TimeView
from essentials.utils import get_team_channel


def get_over(state):
    overwrites = PermissionOverwrite()
    overwrites.manage_channels = state
    overwrites.manage_permissions = state
    overwrites.send_messages = state
    overwrites.view_channel = state
    overwrites.create_public_threads = state
    overwrites.create_private_threads = state
    overwrites.send_messages_in_threads = state
    overwrites.embed_links = state
    overwrites.attach_files = state
    overwrites.add_reactions = state
    overwrites.use_external_emojis = state
    overwrites.mention_everyone = state
    overwrites.manage_messages = state
    overwrites.read_message_history = state

    return overwrites


class TaskerCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma

    @slash_command(description="Press enter and submit your availability")
    async def submitavailability(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.channel.name != Data.AVIAL_SUBMIT_CHANNEL:
            return await interaction.edit_original_message(
                content="You can't submit availability in this channel"
            )

        tu_times = TimeView()
        wd_times = TimeView()
        th_times = TimeView()

        await interaction.edit_original_message(
            content="On **Tuesday** which times will you be available to play?",
            view=tu_times,
        )
        await tu_times.wait()

        if tu_times.cancelled:
            return await interaction.edit_original_message(
                content="❌ Cancelled!",
                view=None,
            )

        await interaction.edit_original_message(
            content="On **Wednessday** which times will you be available to play?",
            view=wd_times,
        )
        await wd_times.wait()

        if wd_times.cancelled:
            return await interaction.edit_original_message(
                content="❌ Cancelled!",
                view=None,
            )

        await interaction.edit_original_message(
            content="On **Thursday** which times will you be available to play?",
            view=th_times,
        )
        await th_times.wait()

        if th_times.cancelled:
            return await interaction.edit_original_message(
                content="❌ Cancelled!",
                view=None,
            )

        await interaction.edit_original_message(
            content=f"✅ {interaction.user.mention} Availability Submitted!", view=None
        )

        SUBMITTED_ROLE = get(interaction.guild.roles, name=Data.SUBMITTED_ROLE)
        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)

        if SUBMITTED_ROLE:
            await interaction.user.add_roles(SUBMITTED_ROLE)

        message = (
            f"{interaction.user.mention} is available \n"
            f"**Tuesday**: {'/'.join(tu_times.slots) or 'None'} \n"
            f"**Wednessday**: {'/'.join(wd_times.slots) or 'None'} \n"
            f"**Thursday**: {'/'.join(th_times.slots) or 'None'}"
        )

        SUBMISSION_LOG_CHANNEL = get(
            interaction.guild.text_channels,
            name=Data.AVIAL_LOG_CHANNEL,
        )

        if SUBMISSION_LOG_CHANNEL:
            await SUBMISSION_LOG_CHANNEL.send(content=message)

        if SUPPORT_GUILD:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{interaction.guild.name[4:].replace(' ', '-').lower()}",
            )

            if TEAM_LOG_CHANNEL:
                await TEAM_LOG_CHANNEL.send(content=message)

    @slash_command(description="Press enter and submit lineups")
    async def setlineups(
        self,
        interaction: Interaction,
        day: str = SlashOption(
            name="day",
            description="Select the day of the game",
            choices={
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
            },
        ),
        time: str = SlashOption(
            name="time",
            description="Select time of the game",
            choices={
                "8:30": "8:30",
                "9:15": "9:15",
                "10:00": "10:00",
            },
        ),
        left_wing: Member = SlashOption(description="Select left wing player"),
        right_wing: Member = SlashOption(description="Select right wing player"),
        left_defense: Member = SlashOption(description="Select left defense player"),
        right_defense: Member = SlashOption(description="Select right defense player"),
        center: Member = SlashOption(description="Select center player"),
        goalie: Member = SlashOption(description="Select goalie player"),
    ):
        await interaction.response.defer()

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.edit_original_message(
                content="You can't submit lineups in this channel"
            )

        l_data = await self.prisma.lineup.create(
            data={
                "team": interaction.guild.name[4:].replace(" ", "-").lower(),
                "day": day,
                "time": time,
                "left_wing": left_wing.id,
                "right_wing": right_wing.id,
                "left_defense": left_defense.id,
                "right_defense": right_defense.id,
                "center": center.id,
                "goalie": goalie.id,
            }
        )

        embed = Embed(title=f"Lineups for `{day}` at `{time}` \n")
        embed.description = (
            f"Left Wing: {left_wing.mention} \n"
            f"Right Wing: {right_wing.mention} \n"
            f"Left Defense: {left_defense.mention} \n"
            f"Right Defense: {right_defense.mention} \n"
            f"Center: {center.mention} \n"
            f"Goalie: {goalie.mention}"
        )
        embed.set_thumbnail(url=interaction.guild.icon.url)

        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)
        LINEUP_LOG_CHANNEL = get(
            interaction.guild.text_channels, name=Data.LINEUP_LOG_CHANNEL
        )

        if LINEUP_LOG_CHANNEL:
            log_message = await LINEUP_LOG_CHANNEL.send(embed=embed)
            await self.prisma.lineup.update(
                where={"id": l_data.id}, data={"message_id_team": log_message.id}
            )

        if SUPPORT_GUILD:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{interaction.guild.name[4:].replace(' ', '-').lower()}",
            )

            if TEAM_LOG_CHANNEL:
                cmc_log_message = await TEAM_LOG_CHANNEL.send(embed=embed)
                await self.prisma.lineup.update(
                    where={"id": l_data.id},
                    data={"message_id_team": cmc_log_message.id},
                )

        members = [
            left_wing,
            right_wing,
            left_defense,
            right_defense,
            center,
            goalie,
        ]

        try:
            week = datetime.now().isocalendar().week
        except:
            week = datetime.now().isocalendar()[1]

        for member in members:
            await self.prisma.lineups.create(
                {"member_id": member.id, "week": week, "year": datetime.now().year}
            )

        await interaction.edit_original_message(
            content=f"Lineups for `{day}` at `{time}` have been submitted. ID: {l_data.id}"
        )

    @slash_command(description="Press enter and edit lineups")
    async def editlineup(
        self,
        interaction: Interaction,
        lineup_id: str = SlashOption(
            name="lineup_id", description="The id of the lineup you want to edit"
        ),
        day: str = SlashOption(
            name="day",
            description="Select the day of the game",
            choices={
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
            },
            required=False,
        ),
        time: str = SlashOption(
            name="time",
            description="Select time of the game",
            choices={
                "8:30": "8:30",
                "9:15": "9:15",
                "10:00": "10:00",
            },
            required=False,
        ),
        left_wing: Member = SlashOption(
            description="Select left wing player", required=False
        ),
        right_wing: Member = SlashOption(
            description="Select right wing player", required=False
        ),
        left_defense: Member = SlashOption(
            description="Select left defense player", required=False
        ),
        right_defense: Member = SlashOption(
            description="Select right defense player", required=False
        ),
        center: Member = SlashOption(
            description="Select center player", required=False
        ),
        goalie: Member = SlashOption(
            description="Select goalie player", required=False
        ),
    ):
        await interaction.response.defer()
        old_lineup = await self.prisma.lineup.find_unique(
            where={
                "id": lineup_id,
            }
        )
        team_name = get_team_channel(interaction.guild.name)

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.edit_original_message(
                content="You can't edit lineups in this channel"
            )

        if not old_lineup or old_lineup.team != team_name:
            return await interaction.followup.send(content="Lineup was not found")

        new_lineup_data = {
            "day": day or old_lineup.day,
            "time": time or old_lineup.time,
            "left_wing": left_wing.id if left_wing else old_lineup.left_wing,
            "right_wing": right_wing.id if right_wing else old_lineup.right_wing,
            "left_defense": left_defense.id
            if left_defense
            else old_lineup.left_defense,
            "right_defense": right_defense.id
            if right_defense
            else old_lineup.right_defense,
            "center": center.id if center else old_lineup.center,
            "goalie": goalie.id if goalie else old_lineup.goalie,
        }

        await self.prisma.lineup.update(
            where={"id": old_lineup.id}, data=new_lineup_data
        )

        embed = Embed(
            title=f"Lineups for `{day or old_lineup.day}` at `{time or old_lineup.time}` \n"
        )

        left_wing_member = (
            left_wing.mention
            if left_wing
            else interaction.guild.get_member(old_lineup.left_wing).mention
        )
        right_wing_member = (
            right_wing.mention
            if right_wing
            else interaction.guild.get_member(old_lineup.right_wing).mention
        )
        left_defense_member = (
            left_defense.mention
            if left_defense
            else interaction.guild.get_member(old_lineup.left_defense).mention
        )
        right_defense_member = (
            right_defense.mention
            if right_defense
            else interaction.guild.get_member(old_lineup.right_defense).mention
        )
        center_member = (
            center.mention
            if center
            else interaction.guild.get_member(old_lineup.center).mention
        )
        goalie_member = (
            goalie.mention
            if goalie
            else interaction.guild.get_member(old_lineup.goalie).mention
        )

        embed.description = (
            f"Left Wing: {left_wing_member} \n"
            f"Right Wing: {right_wing_member} \n"
            f"Left Defense: {left_defense_member} \n"
            f"Right Defense: {right_defense_member} \n"
            f"Center: {center_member} \n"
            f"Goalie: {goalie_member}"
        )
        embed.set_thumbnail(url=interaction.guild.icon.url)

        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)
        LINEUP_LOG_CHANNEL = get(
            interaction.guild.text_channels, name=Data.LINEUP_LOG_CHANNEL
        )

        if LINEUP_LOG_CHANNEL:
            try:
                old_message = await LINEUP_LOG_CHANNEL.fetch_message(
                    old_lineup.message_id_team
                )
                if old_message:
                    await old_message.delete()
            except:
                pass

            message = await LINEUP_LOG_CHANNEL.send(embed=embed)
            await self.prisma.lineup.update(
                where={"id": lineup_id}, data={"message_id_team": message.id}
            )

        if SUPPORT_GUILD:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{team_name}",
            )

            if TEAM_LOG_CHANNEL:
                try:
                    old_message = await TEAM_LOG_CHANNEL.fetch_message(
                        old_lineup.message_id_cnc
                    )
                    if old_message:
                        await old_message.delete()
                except:
                    pass

                message = await TEAM_LOG_CHANNEL.send(embed=embed)
                await self.prisma.lineup.update(
                    where={"id": lineup_id}, data={"message_id_cnc": message.id}
                )

        await interaction.followup.send(
            content=f"Lineup ID: `{lineup_id}` has been updated."
        )

    @slash_command(name="create-category", description="Create category")
    @commands.has_any_role("Owner", "General Manager")
    async def create_category(
        self,
        interaction: Interaction,
        category_name: str = SlashOption(
            name="category_name", description="The category name"
        ),
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
        channel_name: str = SlashOption(
            name="channel_name", description="The channel name"
        ),
        category: CategoryChannel = SlashOption(
            name="category", description="Mention the category"
        ),
    ):
        await interaction.response.defer(ephemeral=True)

        exists = get(interaction.guild.text_channels, name=channel_name)

        if exists:
            return await interaction.edit_original_message(
                content="Can't create channel with this name"
            )

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
            return await interaction.edit_original_message(
                content="Can't create role with this name"
            )

        await interaction.guild.create_role(name=name)
        await interaction.edit_original_message(content="Role created")


def setup(bot: IBot):
    bot.add_cog(TaskerCommands(bot))
