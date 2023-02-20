from nextcord import Embed, SlashOption, Member
from nextcord.ext import commands
from nextcord.utils import get
from nextcord.application_command import slash_command
from nextcord.interactions import Interaction
from prisma import Prisma
from datetime import datetime

from essentials.models import IBot, Data, ALL_GUILD
from essentials.views import TimeView


class TaskerCommands(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.prisma = bot.prisma

    @slash_command(
        description="Press enter and submit your availability",
        guild_ids=ALL_GUILD,
    )
    async def submitavailability(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

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

    @slash_command(
        description="Press enter and submit lineups",
        guild_ids=ALL_GUILD,
    )
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
        await interaction.response.defer(ephemeral=True)
        SUPPORT_GUILD = self.bot.get_guild(Data.SUPPORT_GUILD)

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

        if SUPPORT_GUILD:
            TEAM_LOG_CHANNEL = get(
                SUPPORT_GUILD.text_channels,
                name=f"╟・{interaction.guild.name[4:].replace(' ', '-').lower()}",
            )
            LINEUP_LOG_CHANNEL = get(interaction.guild.text_channels, name=Data.LINEUP_LOG_CHANNEL)

            if TEAM_LOG_CHANNEL:
                await TEAM_LOG_CHANNEL.send(embed=embed)
            
            if LINEUP_LOG_CHANNEL:
                await LINEUP_LOG_CHANNEL.send(embed=embed)

        await interaction.edit_original_message(
            content=f"Lineups for `{day}` at `{time}` have been submitted"
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
            await self.prisma.lineups.create({
                "memberId": str(member.id),
                "week": week,
                "year": datetime.now().year
            })

def setup(bot: IBot):
    bot.add_cog(TaskerCommands(bot))
