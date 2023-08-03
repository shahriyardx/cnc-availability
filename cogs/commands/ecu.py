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
from typing import Optional


team_invites = {
    "Anaheim Ducks": "https://discord.gg/GezGD4MxTk",
    "Arizona Coyotes": "https://discord.gg/DGTPvT3sQt",
    "Boston Bruins": "https://discord.gg/Jd32mMybPX",
    "Buffalo Sabres": "https://discord.gg/QFsf9aB4HD",
    "Carolina Hurricanes": "https://discord.gg/3skaKFyTVH",
    "Columbus Blue Jackets": "https://discord.gg/eNS7rpNXnk",
    "Calgary Flames": "https://discord.gg/BkWVvwuBWh",
    "Chicago Blackhawks": "https://discord.gg/7zEgS7BMGe",
    "Colorado Avalanche": "https://discord.gg/XzaFAhtwzy",
    "Dallas Stars": "https://discord.gg/TpPFMBthtN",
    "Detroit Red Wings": "https://discord.gg/3DEDUuwwKm",
    "Edmonton Oilers": "https://discord.gg/PsBXWzuJE5",
    "Florida Panthers": "https://discord.gg/sQypPgT7Jd",
    "Los Angeles Kings": "https://discord.gg/b4KyRrKw45",
    "Minnesota Wild": "https://discord.gg/Qg5xZCdpgD",
    "Montreal Canadiens": "https://discord.gg/NKWB8jvfRk",
    "New Jersey Devils": "https://discord.gg/6DJhvXhQa6",
    "Nashville Predators": "https://discord.gg/PrnDNpFbku",
    "New York Islanders": "https://discord.gg/5NhdBbTfva",
    "New York Rangers": "https://discord.gg/JZG9rVpqpQ",
    "Ottawa Senators": "https://discord.gg/F5fU7HSYcQ",
    "Philadelphia Flyers": "https://discord.gg/VzGRWG7yvH",
    "Pittsburgh Penguins": "https://discord.gg/pPNXwYp2Hd",
    "Seattle Kraken": "https://discord.gg/x3Jpf3BhWe",
    "San Jose Sharks": "https://discord.gg/9Z22Wx5rkr",
    "St Louis Blues": "https://discord.gg/pammDhKmkf",
    "Tampa Bay Lightning": "https://discord.gg/qtkup4ARGa",
    "Toronto Maple Leafs": "https://discord.gg/HXN3mpSDUY",
    "Vancouver Canucks": "https://discord.gg/DPXTRSsqaT",
    "Vegas Golden Knights": "https://discord.gg/3qr9jHX7z2",
    "Winnipeg Jets": "https://discord.gg/fmcYMaUzDR",
    "Washington Capitals": "https://discord.gg/wx8FdRxp9R",
}


class ECUCommand(commands.Cog):
    def __init__(self, bot: IBot) -> None:
        self.bot = bot
        self.roster = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.ecu = DataSheet("ECU Sheet")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, event: nextcord.RawReactionActionEvent):
        if event.guild_id:
            return

        try:
            channel = await self.bot.fetch_channel(event.channel_id)
        except Exception as e:
            print(e)
            return

        try:
            message = await channel.fetch_message(event.message_id)
            if message.author.id == event.user_id:
                raise ValueError("Unable")
        except Exception as e:
            print(e)
            return

        content = message.content
        info_row = content.split("\n")[0]
        infos = info_row.split(" | ")
        team = infos[0].split(":")[1].strip()
        position = infos[1].split(":")[1].strip()
        channel_id = infos[2].split(":")[1].strip()

        team_guild = get(self.bot.guilds, name=f"CNC {team}")
        if not team_guild:
            return

        ir_role = get(team_guild.roles, name="IR")
        position_needing_ecu = []

        for member in ir_role.members:
            for role in member.roles:
                if role.name in [
                    "Left Wing",
                    "Right Wing",
                    "Left Defense",
                    "Right Defense",
                    "Goalie",
                    "Center",
                ]:
                    pos = ""
                    poses = role.name.split(" ")
                    for p in poses:
                        pos += p[0]

                    position_needing_ecu.append(pos)

        selected_for_ecu = self.ecu.get_values("ecuData")
        selected_players = []

        for row in selected_for_ecu[1:]:
            if row[0] == team:
                selected_players.append(row)

        for player in selected_players:
            if player[2] in position_needing_ecu:
                position_needing_ecu.remove(player[2])

        if position not in position_needing_ecu:
            return await channel.send(content="The position is unavailable. Please try other position")

        ecu_data = self.ecu.get_values("ecuData")
        for row in ecu_data:
            if row[3] == str(event.user_id):
                return await channel.send(content=f"You are already on the **{team}** for ECU this week.")

        cnc_channel = self.bot.get_channel(int(channel_id))
        author = cnc_channel.guild.get_member(event.user_id)

        if cnc_channel:
            await cnc_channel.send(content=f"$add {author.mention}")

        await author.send(content=f"Welcome to **{team}** {team_invites.get(team)}")
        self.ecu.append(
            "ecuData",
            [
                team,
                author.display_name,
                position,
                str(author.id),
            ],
        )

    async def send_messages(self, interaction: Interaction, team: nextcord.Role, search_position: str):
        nicks = []

        players = self.ecu.get_values("players")
        for player in players:
            if player[1] == search_position:
                nicks.append(player[0])

        print(nicks)
        for nick in nicks:
            member = get(interaction.guild.members, nick=nick)
            if not member:
                print(f"Unable to find member with nick {nick}")
                continue

            if member:
                msg = await member.send(
                    content=(
                        f"Team: {team.name} | Position: {search_position} | Channel ID: {interaction.channel_id}\n\n"
                        f"{member.mention}, You are one of the undrafted players chosen to play "
                        f"for the **{team.name}** this week. \n\n"
                        "- We Play: Tues, Wed, and Thurs at 8:30/9:10/9:50 pm EST.\n"
                        "- **Hit the thumbs up if you can play at least 3 games this week.**"
                    )
                )

                await msg.add_reaction("👍")
                await asyncio.sleep(5)

    @slash_command(description="Automatic ecu")
    async def autoecu(
        self,
        interaction: Interaction,
        team: nextcord.Role = SlashOption(description="The team role", required=True),
        player: nextcord.Member = SlashOption(description="The player that needs to be replaced", required=False),
        position: nextcord.Role = SlashOption(description="Select the position", required=False),
    ):
        if interaction.guild_id not in [1055597639028183080, 831166408888942623]:
            return

        await interaction.response.defer()

        try:
            sheet_data = self.roster.get_values(team.name)
        except:  # noqa
            return await interaction.edit_original_message(content=f"Data for the {team.name} not found")

        search_position: Optional[str] = None

        if position:
            pos = ""
            poses = position.name.split(" ")
            for p in poses:
                pos += p[0]

            search_position = pos.strip()
        else:
            if player:
                for data in sheet_data:
                    if data[0] == player.display_name:
                        search_position = data[3]

                if not search_position:
                    return await interaction.edit_original_message(
                        content=f"Unable to find primary position of {player.mention}"
                    )

        if search_position:
            await interaction.edit_original_message(
                content=(f"Starting ECU for the {team.name}, Position: {search_position}")
            )
            return await self.send_messages(interaction, team, search_position)

        team_guild = get(self.bot.guilds, name=f"CNC {team.name}")
        if not team_guild:
            return await interaction.edit_original_message(content=f"Unable to find team discord of {team.name}")

        ir = get(team_guild.roles, name="IR")
        position_needing_ecu = []

        for member in ir.members:
            for role in member.roles:
                if role.name in [
                    "Left Wing",
                    "Right Wing",
                    "Left Defense",
                    "Right Defense",
                    "Goalie",
                    "Center",
                ]:
                    pos = ""
                    poses = role.name.split(" ")
                    for p in poses:
                        pos += p[0]

                    position_needing_ecu.append(pos)

        await interaction.edit_original_message(
            content=(f"Starting ECU for the {team.name}, Positions: {', '.join(position_needing_ecu)}")
        )

        for ir_pos in position_needing_ecu:
            await self.send_messages(interaction, team, ir_pos)


def setup(bot: IBot):
    bot.add_cog(ECUCommand(bot))
