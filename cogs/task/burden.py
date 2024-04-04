# async def close_lineup_submit(self, simulate: bool = False):
#     # Runs Tuesday 4 AM
#     # Keeps the lineup edit open
#
#     print("[+] START close_lineup_submit")
#     if not self.bot.tasks_enabled:  # noqa
#         if not simulate:
#             return self.start_task(self.close_lineup_submit, get_next_date("Tuesday", hour=4))
#
#         return
#
#     settings = await self.bot.prisma.settings.find_first()
#     await self.bot.prisma.settings.update(
#         where={"id": settings.id},
#         data={
#             "can_edit_lineups": True,
#             "can_submit_lineups": False,
#         },
#     )
#
#     print("[+] STOP close_lineup_submit")
#     if not simulate:
#         self.start_task(self.close_lineup_submit, get_next_date("Tuesday", hour=4))


# async def close_lineup_channel(self, simulate: bool = False):
#     # Runs Friday 2 AM UTC
#     # Closes the lineup channel
#     # Checks who did not play 3 matches
#
#     # Close lineup submit and edit both again
#     print("[+] START close_lineup_channel")
#     if not self.bot.tasks_enabled:  # noqa
#         if not simulate:
#             return self.start_task(self.close_lineup_channel, get_next_date("Friday", hour=2))
#
#         return
#
#     settings = await self.bot.prisma.settings.find_first()
#     await self.bot.prisma.settings.update(
#         where={"id": settings.id},
#         data={
#             "can_edit_lineups": False,
#             "can_submit_lineups": False,
#         },
#     )
#
#     for guild in self.bot.guilds:
#         if guild.id in Data.IGNORED_GUILDS:
#             continue
#
#         lineups_channel = get(guild.text_channels, name=Data.LINEUP_SUBMIT_CHANNEL)
#         owner_role = get(guild.roles, name="Owner")
#         gm_role = get(guild.roles, name="General Manager")
#
#         if lineups_channel and owner_role and gm_role:
#             await lineups_channel.send(":information_source: Lineup editing has been closed for this week.")
#
#             await lockdown(lineups_channel, roles=[owner_role, gm_role])
#
#     print("[+] STOP close_lineup_channel")
#
#     if not simulate:
#         self.start_task(self.close_lineup_channel, get_next_date("Friday", hour=2))
