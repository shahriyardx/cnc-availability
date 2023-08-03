import nextcord
from nextcord import ui
from typing import Optional, List, Callable
from nextcord import SelectOption


class DayAndTimeView(ui.View):
    def __init__(self):
        super().__init__()
        self.days: List[str] = []
        self.times: List[str] = []
        self.cancelled = False

    @ui.string_select(
        placeholder="Select Day",
        custom_id="day",
        min_values=1,
        max_values=3,
        options=[
            SelectOption(label="Tuesday", value="Tuesday"),
            SelectOption(label="Wednesday", value="Wednesday"),
            SelectOption(label="Thursday", value="Thursday"),
        ],
        row=1,
    )
    async def day(self, select: ui.StringSelect, interaction: nextcord.Interaction):
        self.days = select.values
        for opt in select.options:
            if opt.value in select.values:
                opt.default = True

        await interaction.response.edit_message(view=self)

    @ui.string_select(
        placeholder="Select Time",
        custom_id="time",
        min_values=1,
        max_values=3,
        options=[
            SelectOption(label="8:30pm", value="8:30pm"),
            SelectOption(label="9:10pm", value="9:10pm"),
            SelectOption(label="9:50pm", value="9:50pm"),
        ],
        row=2,
    )
    async def times(self, select: ui.StringSelect, interaction: nextcord.Interaction):
        self.times = select.values
        for opt in select.options:
            if opt.value in select.values:
                opt.default = True

        await interaction.response.edit_message(view=self)

    @ui.button(label="Next", custom_id="next", row=3, style=nextcord.ButtonStyle.primary)
    async def next(self, _button: ui.Button, _interaction: nextcord.Interaction):
        self.stop()

    @ui.button(label="Cancel", custom_id="cancel", row=3, style=nextcord.ButtonStyle.danger)
    async def cancel(self, _button: ui.Button, _interaction: nextcord.Interaction):
        self.stop()
        self.cancelled = True


class CustomMemberSelect(ui.StringSelect):
    def __init__(self, placeholder: str, members: list, callback: Callable):
        print("Initiate")

        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

        for member in members:
            self.add_option(
                label=member,
                value=member,
                default=member in self.values,
            )

        self.on_change = callback

    async def callback(self, interaction: nextcord.Interaction) -> None:
        member = self.values[0] if len(self.values) > 0 else None
        for opt in self.options:
            opt.default = False

            if opt.value == member:
                opt.default = True

        await self.on_change(member, interaction)


class StagePlayers(ui.View):
    def __init__(self, lw_members: list, rw_members: list, g_members: list):
        super().__init__()
        self.a: Optional[str] = None
        self.b: Optional[str] = None
        self.c: Optional[str] = None
        self.cancelled: bool = False

        self.add_item(CustomMemberSelect("Select LW player", lw_members, self.on_lw_select))
        self.add_item(CustomMemberSelect("Select RW player", rw_members, self.on_rw_select))
        self.add_item(CustomMemberSelect("Select G player", g_members, self.on_g_select))

    async def on_lw_select(self, member: Optional[str], interaction: nextcord.Interaction):
        if member:
            self.a = member
        await interaction.response.edit_message(view=self)

    async def on_rw_select(self, member: Optional[str], interaction: nextcord.Interaction):
        if member:
            self.b = member
        await interaction.response.edit_message(view=self)

    async def on_g_select(self, member: Optional[str], interaction: nextcord.Interaction):
        if member:
            self.c = member
        await interaction.response.edit_message(view=self)

    @ui.button(label="Next", custom_id="next", row=3, style=nextcord.ButtonStyle.primary)
    async def next(self, _button: ui.Button, _interaction: nextcord.Interaction):
        self.stop()

    @ui.button(label="Cancel", custom_id="cancel", row=3, style=nextcord.ButtonStyle.danger)
    async def cancel(self, _button: ui.Button, _interaction: nextcord.Interaction):
        self.stop()
        self.cancelled = True
