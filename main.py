import os
from typing import Optional

import nextcord
from dotenv import load_dotenv
from nextcord import Intents
from nextcord.ext import commands
from nextcord.utils import get

from essentials.models import Data
from prisma import Prisma
from utils.gspread import DataSheet

load_dotenv(".env")

intents = Intents.default()
intents.members = True # noqa
intents.guilds = True # noqa


def get_number(value):
    print(f'Value: {value}')
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class Availability(commands.AutoShardedBot):
    def __init__(self, command_prefix: str, **kwargs):
        super().__init__(command_prefix, **kwargs)
        self.prisma = Prisma()
        self.SUPPORT_GUILD: Optional[nextcord.Guild] = None
        self.roster_sheet = DataSheet("NHL Live Draft Sheet")
        self.draft_sheet = DataSheet("OFFICIAL NHL ROSTER SHEET")
        self.ecu_sheet = DataSheet("ECU Sheet")
        self.tasks_enabled = True
        self.playoffs = False

    async def on_ready(self):
        await self.prisma.connect()
        self.SUPPORT_GUILD = self.get_guild(Data.SUPPORT_GUILD)

        settings = await self.prisma.settings.find_first()
        self.tasks_enabled = settings.tasks_enabled
        self.playoffs = settings.playofss

        if not settings:
            await self.prisma.settings.create(
                data={
                    "can_edit_lineups": False,
                    "can_submit_lineups": False,
                }
            )

        print(f"{self.user} is ready..")

        # all_roaster = self.roster_sheet.get_values("Data import")
        # nick_dict = {member.display_name: member.id for member in self.SUPPORT_GUILD.members}
        #
        # for index, row in enumerate(all_roaster):
        #     await asyncio.sleep(2)
        #     print(row[0], index)
        #     if row[0] in nick_dict:
        #         self.roster_sheet.update("Data import", f"D{index + 1}", str(nick_dict[row[0]]))

    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id in Data.IGNORED_GUILDS:
            return

        team_role = get(member.guild.roles, name="Team")
        if not team_role:
            print("No team")
            return

        cnc_member = self.SUPPORT_GUILD.get_member(member.id)
        if not cnc_member:
            print("No member of CNC")
            return

        all_ecu = self.ecu_sheet.get_values("ecuData")
        print(all_ecu)
        for row in all_ecu[1:]:
            try:
                uid = int(row[3])
            except (TypeError, ValueError):
                continue

            print(uid, member.id, member.guild.name, f"CNC {row[0]}")
            if uid == member.id and member.guild.name == f"CNC {row[0]}":
                ecu_role = get(member.guild.roles, name="ECU")
                if not ecu_role:
                    ecu_role = await member.guild.create_role(name="ECU")
                await member.add_roles(ecu_role)
                chat = get(member.guild.text_channels, name="chat")
                if chat:
                    owner_role = get(member.guild.roles, name="Owner")
                    gm_role = get(member.guild.roles, name="General Manager")
                    agm_role = get(member.guild.roles, name="AGM")

                    mentions = ", ".join([role.mention for role in [owner_role, gm_role, agm_role] if role])

                    await chat.send(content=(
                        f"{mentions} - {member.mention} has arrived to be your ECU this entire "
                        f"week and is guaranteed 3 games"
                    ))

        team_name = member.guild.name.split(" ", maxsplit=1)[1].strip()
        right_team = get(cnc_member.roles, name=team_name)

        if not right_team:
            return

        role_names = {
            "LW": "Left Wing",
            "RW": "Right Wing",
            "LD": "Left Defense",
            "RD": "Right Defense",
            "G": "Goalie",
            "C": "Center",
        }

        all_roster = self.roster_sheet.get_values("Data import")

        for row in all_roster[1:]:
            try:
                member_id = int(row[3])
            except (ValueError, TypeError):
                continue

            if member_id == member.id:
                await member.add_roles(team_role)
                await member.edit(nick=row[0])

                primary_position = get(member.guild.roles, name=role_names.get(row[1]))
                secondary_position = get(member.guild.roles, name=role_names.get(row[2]))

                if primary_position:
                    await member.add_roles(primary_position)

                if secondary_position:
                    await member.add_roles(secondary_position)

                break

        owner_id = get_number(self.draft_sheet.get_value(team_name, "B27")[0][0])
        gm_id = get_number(self.draft_sheet.get_value(team_name, "B28")[0][0])
        agm_id = get_number(self.draft_sheet.get_value(team_name, "B29")[0][0])

        if owner_id == member.id:
            nick = self.draft_sheet.get_value(team_name, "A27")[0][0]
            owner_role = get(member.guild.roles, name="Owner")
            team_role = get(member.guild.roles, name="Team")
            await member.add_roles(owner_role)
            await member.remove_roles(team_role)
            if nick:
                await member.edit(nick=nick)

        if gm_id == member.id:
            nick = self.draft_sheet.get_value(team_name, "A28")[0][0]
            gm_role = get(member.guild.roles, name="General Manager")
            team_role = get(member.guild.roles, name="Team")
            await member.add_roles(gm_role)
            await member.remove_roles(team_role)

            if nick:
                await member.edit(nick=nick)

        if agm_id == member.id:
            agm_role = get(member.guild.roles, name="AGM")
            await member.add_roles(agm_role)

    def get_command_mention(self, command_name) -> str:
        cmd = None
        all_commands = self.get_application_commands()

        for command in all_commands:
            if command.qualified_name == command_name:
                cmd = command

        if cmd:
            return f"</{command_name}:{cmd.command_ids[None]}>"
        else:
            return f"/{command_name}"


bot = Availability(command_prefix="a.", intents=intents)

bot.load_extension("cogs.commands")
bot.load_extension("cogs.commands.admin")
bot.load_extension("cogs.commands.ecu")
bot.load_extension("cogs.task")
bot.load_extension("cogs.utility")

TOKEN = os.environ["TOKEN"]
bot.run(TOKEN)
