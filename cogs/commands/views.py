import nextcord
from nextcord import ui
from typing import List, Callable
from nextcord import SelectOption
from .utils import CustomMember


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
    def __init__(self, placeholder: str, members: list[CustomMember], callback: Callable, default: int = None):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        for member in members:
            self.add_option(
                label=f"{member.nick} {member.position}",
                value=str(member.id),
                default=member.id == default,
            )

        self.on_change = callback

    async def callback(self, interaction: nextcord.Interaction) -> None:
        member = self.values[0] if len(self.values) > 0 else "0"

        for opt in self.options:
            opt.default = False
            if opt.value == member:
                opt.default = True

        await self.on_change(int(member), interaction)


class StagePlayers(ui.View):
    def __init__(self, lw_members: list, rw_members: list, g_members: list, p: list, defaults: dict = None):
        super().__init__()
        if not defaults:
            defaults = {
                p[0]: 0,
                p[1]: 0,
                p[2]: 0,
            }

        self.data = {**defaults}

        self.cancelled: bool = False
        self.p = p

        self.add_item(CustomMemberSelect(f"Select {p[0]} player", lw_members, self.on_a_select, defaults[p[0]]))
        self.add_item(CustomMemberSelect(f"Select {p[1]} player", rw_members, self.on_b_select, defaults[p[1]]))
        self.add_item(CustomMemberSelect(f"Select {p[2]} player", g_members, self.on_c_select, defaults[p[2]]))

    async def on_a_select(self, member: int, interaction: nextcord.Interaction):
        if member:
            self.data[self.p[0]] = member

        await interaction.response.edit_message(view=self)

    async def on_b_select(self, member: int, interaction: nextcord.Interaction):
        if member:
            self.data[self.p[1]] = member

        await interaction.response.edit_message(view=self)

    async def on_c_select(self, member: int, interaction: nextcord.Interaction):
        if member:
            self.data[self.p[2]] = member

        await interaction.response.edit_message(view=self)

    @ui.button(label="Next", custom_id="next", row=3, style=nextcord.ButtonStyle.primary)
    async def next(self, _button: ui.Button, _interaction: nextcord.Interaction):
        if not self.data[self.p[0]] or not self.data[self.p[1]] or not self.data[self.p[2]]:
            return

        self.stop()

    @ui.button(label="Cancel", custom_id="cancel", row=3, style=nextcord.ButtonStyle.danger)
    async def cancel(self, _button: ui.Button, _interaction: nextcord.Interaction):
        self.stop()
        self.cancelled = True
