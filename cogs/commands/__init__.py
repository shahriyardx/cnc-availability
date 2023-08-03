from datetime import datetime

from nextcord import CategoryChannel, Embed, Member, PermissionOverwrite, SlashOption
from nextcord.application_command import slash_command
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.utils import get

from essentials.models import Data, IBot
from essentials.utils import get_team_name
from essentials.views import TimeView
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
                "9:10": "9:10",
                "9:50": "9:50",
            },
        ),
        left_wing: Member = SlashOption(description="Select left wing player"),
        center: Member = SlashOption(description="Select center player"),
        right_wing: Member = SlashOption(description="Select right wing player"),
        left_defense: Member = SlashOption(description="Select left defense player"),
        right_defense: Member = SlashOption(description="Select right defense player"),
        goalie: Member = SlashOption(description="Select goalie player"),
    ):
        await interaction.response.defer()

        settings = await self.bot.prisma.settings.find_first()

        if not settings.can_submit_lineups:
            return await interaction.followup.send(content="Lineups can't be submitted right now")

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.edit_original_message(content="You can't submit lineups in this channel")

        players = [left_wing, left_defense, right_wing, right_defense, goalie, center]
        team_role = get(interaction.guild.roles, name=Data.PLAYERS_ROLE)
        ecu_role = get(interaction.guild.roles, name="ECU")
        owner_role = get(interaction.guild.roles, name="Owner")
        gm_role = get(interaction.guild.roles, name="General Manager")
        ir_role = get(interaction.guild.roles, name="IR")

        for player in players:
            if ir_role in player.roles:
                return await interaction.followup.send(
                    content=f"Player {player.mention} is not eligible for lineup. Reason: Player is on IR"
                )

            if (
                team_role in player.roles
                or owner_role in player.roles
                or gm_role in player.roles
                or ecu_role in player.roles
            ):
                continue
            else:
                return await interaction.followup.send(
                    content=(
                        f"Player {player.mention} is not eligible for lineup. "
                        "Reason: Member does not have Team, Owner or General Manager role"
                    )
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

        content = " ".join([player.mention for player in players])
        embed = Embed(title=f"Lineups for `{day}` at `{time}` \n")
        embed.description = (
            f"Left Wing: {left_wing.mention} \n"
            f"Center: {center.mention} \n"
            f"Right Wing: {right_wing.mention} \n"
            f"Left Defense: {left_defense.mention} \n"
            f"Right Defense: {right_defense.mention} \n"
            f"Goalie: {goalie.mention}"
        )
        embed.set_thumbnail(url=interaction.guild.icon.url)

        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)
        LINEUP_LOG_CHANNEL = get(interaction.guild.text_channels, name=Data.LINEUP_LOG_CHANNEL)

        if LINEUP_LOG_CHANNEL:
            log_message = await LINEUP_LOG_CHANNEL.send(content=content, embed=embed)
            await self.prisma.lineup.update(where={"id": l_data.id}, data={"message_id_team": log_message.id})

        if SUPPORT_GUILD:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{get_team_name(interaction.guild.name)}",
            )

            if TEAM_LOG_CHANNEL:
                cmc_log_message = await TEAM_LOG_CHANNEL.send(content=content, embed=embed)
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

        week = datetime.now().isocalendar()[1]

        for member in members:
            await self.prisma.playerlineup.create(
                {
                    "member_id": member.id,
                    "week": week,
                    "year": datetime.now().year,
                    "lineupId": l_data.id,
                }
            )

        await interaction.edit_original_message(
            content=f"Lineups for `{day}` at `{time}` have been submitted. ID: {l_data.id}"
        )
        await interaction.channel.send(content=f"```{l_data.id}```")

    @slash_command(description="Press enter and edit lineups")
    async def editlineup(
        self,
        interaction: Interaction,
        lineup_id: str = SlashOption(name="lineup_id", description="The id of the lineup you want to edit"),
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
                "9:10": "9:10",
                "9:50": "9:50",
            },
            required=False,
        ),
        left_wing: Member = SlashOption(description="Select left wing player", required=False),
        center: Member = SlashOption(description="Select center player", required=False),
        right_wing: Member = SlashOption(description="Select right wing player", required=False),
        left_defense: Member = SlashOption(description="Select left defense player", required=False),
        right_defense: Member = SlashOption(description="Select right defense player", required=False),
        goalie: Member = SlashOption(description="Select goalie player", required=False),
    ):
        await interaction.response.defer()
        settings = await self.bot.prisma.settings.find_first()

        if not settings.can_edit_lineups:
            return await interaction.followup.send(content="Lineups can't be editted right now")

        old_lineup = await self.prisma.lineup.find_unique(
            where={
                "id": lineup_id.strip(),
            }
        )
        team_name = get_team_name(interaction.guild.name)

        if interaction.channel.name != Data.LINEUP_SUBMIT_CHANNEL:
            return await interaction.edit_original_message(content="You can't edit lineups in this channel")

        players = [
            p
            for p in [
                left_wing,
                left_defense,
                right_wing,
                right_defense,
                goalie,
                center,
            ]
            if p
        ]
        team_role = get(interaction.guild.roles, name=Data.PLAYERS_ROLE)
        owner_role = get(interaction.guild.roles, name="Owner")
        ecu_role = get(interaction.guild.roles, name="ECU")
        gm_role = get(interaction.guild.roles, name="General Manager")
        ir_role = get(interaction.guild.roles, name="IR")

        for player in players:
            if ir_role in player.roles:
                return await interaction.followup.send(
                    content=f"Player {player.mention} is not eligible for lineup. Reason: Player is on IR"
                )

            if (
                team_role in player.roles
                or owner_role in player.roles
                or gm_role in player.roles
                or ecu_role in player.roles
            ):
                continue
            else:
                return await interaction.followup.send(
                    content=(
                        f"Player {player.mention} is not eligible for lineup. "
                        "Reason: Member does not have Team, Owner or General Manager role"
                    )
                )

        if not old_lineup:
            return await interaction.followup.send(content="Lineup was not found")

        old_players = [
            interaction.guild.get_member(old_lineup.left_wing),
            interaction.guild.get_member(old_lineup.left_defense),
            interaction.guild.get_member(old_lineup.right_wing),
            interaction.guild.get_member(old_lineup.right_defense),
            interaction.guild.get_member(old_lineup.center),
            interaction.guild.get_member(old_lineup.goalie),
        ]

        new_players = [
            interaction.guild.get_member(left_wing.id)
            if left_wing
            else interaction.guild.get_member(old_lineup.left_wing),
            interaction.guild.get_member(right_wing.id)
            if right_wing
            else interaction.guild.get_member(old_lineup.right_wing),
            interaction.guild.get_member(left_defense.id)
            if left_defense
            else interaction.guild.get_member(old_lineup.left_defense),
            interaction.guild.get_member(right_defense.id)
            if right_defense
            else interaction.guild.get_member(old_lineup.right_defense),
            interaction.guild.get_member(center.id) if center else interaction.guild.get_member(old_lineup.center),
            interaction.guild.get_member(goalie.id) if goalie else interaction.guild.get_member(old_lineup.goalie),
        ]

        new_lineup_data = {
            "day": day or old_lineup.day,
            "time": time or old_lineup.time,
            "left_wing": left_wing.id if left_wing else old_lineup.left_wing,
            "center": center.id if center else old_lineup.center,
            "right_wing": right_wing.id if right_wing else old_lineup.right_wing,
            "left_defense": left_defense.id if left_defense else old_lineup.left_defense,
            "right_defense": right_defense.id if right_defense else old_lineup.right_defense,
            "goalie": goalie.id if goalie else old_lineup.goalie,
        }

        await self.prisma.lineup.update(where={"id": old_lineup.id}, data=new_lineup_data)

        embed = Embed(title=f"Lineups for `{day or old_lineup.day}` at `{time or old_lineup.time}` \n")

        embed.description = (
            f"Left Wing: {new_players[0].mention} \n"
            f"Right Wing: {new_players[1].mention} \n"
            f"Left Defense: {new_players[2].mention} \n"
            f"Right Defense: {new_players[3].mention} \n"
            f"Center: {new_players[4].mention} \n"
            f"Goalie: {new_players[5].mention}"
        )
        embed.set_thumbnail(url=interaction.guild.icon.url)

        content = " ".join([player.mention for player in new_players])
        week = datetime.now().isocalendar()[1]

        await self.prisma.playerlineup.delete_many(where={"lineupId": lineup_id})

        for player in new_players:
            await self.prisma.playerlineup.create(
                {
                    "member_id": player.id,
                    "week": week,
                    "year": datetime.now().year,
                    "lineupId": lineup_id,
                }
            )

        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)
        LINEUP_LOG_CHANNEL = get(interaction.guild.text_channels, name=Data.LINEUP_LOG_CHANNEL)

        if LINEUP_LOG_CHANNEL and old_lineup.message_id_team:
            try:
                old_message = await LINEUP_LOG_CHANNEL.fetch_message(int(old_lineup.message_id_team))
                if old_message:
                    await old_message.delete()
            except Exception as e:
                print(e)
                pass

            message = await LINEUP_LOG_CHANNEL.send(content=content, embed=embed)
            await self.prisma.lineup.update(where={"id": lineup_id.strip()}, data={"message_id_team": message.id})

        print(SUPPORT_GUILD, old_lineup.message_id_cnc)

        if SUPPORT_GUILD and old_lineup.message_id_cnc:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{team_name}",
            )

            if not TEAM_LOG_CHANNEL:
                print(f"Team channle not found ╟・{team_name}")

            if TEAM_LOG_CHANNEL:
                print(f"CNC Message id: {int(old_lineup.message_id_cnc)}")

                try:
                    old_message = await TEAM_LOG_CHANNEL.fetch_message(int(old_lineup.message_id_cnc))
                    if old_message:
                        await old_message.delete()
                except Exception as e:
                    print(e)
                    pass

                message = await TEAM_LOG_CHANNEL.send(content=content, embed=embed)
                await self.prisma.lineup.update(where={"id": lineup_id.strip()}, data={"message_id_cnc": message.id})

        await interaction.followup.send(content=f"Lineup ID: `{lineup_id.strip()}` has been updated.")

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
