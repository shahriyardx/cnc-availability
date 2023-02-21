from typing import Any, List

from nextcord import ButtonStyle, ui
from nextcord.interactions import Interaction


class TimeView(ui.View):
    def __init__(self):
        super().__init__()
        self.slots = []
        self.cancelled = False

    async def _update(self, interaction: Interaction):
        buttons: List[Any] = self.children

        for btn in buttons:
            if btn.custom_id in self.slots and btn.custom_id not in [
                "None",
                "Done",
                "Cancel",
            ]:
                btn.label = btn.custom_id + " (Selected)"
                btn.style = ButtonStyle.gray
            elif btn.custom_id not in ["Done", "None", "Cancel"]:
                btn.label = btn.custom_id
                btn.style = ButtonStyle.primary

        await interaction.response.edit_message(view=self)

    @ui.button(label="8:30pm EST", style=ButtonStyle.primary, custom_id="8:30pm EST")
    async def e3p(self, button: ui.Button, interaction: Interaction):
        self.slots.remove(
            button.custom_id
        ) if button.custom_id in self.slots else self.slots.append(button.custom_id)

        await self._update(interaction)

    @ui.button(label="9:15pm EST", style=ButtonStyle.primary, custom_id="9:15pm EST")
    async def nfp(self, button: ui.Button, interaction: Interaction):
        self.slots.remove(
            button.custom_id
        ) if button.custom_id in self.slots else self.slots.append(button.custom_id)

        await self._update(interaction)

    @ui.button(label="10:00pm EST", style=ButtonStyle.primary, custom_id="10:00pm EST")
    async def tp(self, button: ui.Button, interaction: Interaction):
        self.slots.remove(
            button.custom_id
        ) if button.custom_id in self.slots else self.slots.append(button.custom_id)

        await self._update(interaction)

    @ui.button(label="None", style=ButtonStyle.secondary, custom_id="None")
    async def none(self, button: ui.Button, interaction: Interaction):
        self.slots = []
        self.stop()

    @ui.button(label="Done", style=ButtonStyle.green, custom_id="Done")
    async def done(self, button: ui.Button, interaction: Interaction):
        if self.slots:
            self.stop()

    @ui.button(label="Cancel", style=ButtonStyle.danger, custom_id="Cancel")
    async def cancel(self, button: ui.Button, interaction: Interaction):
        self.slots = []
        self.cancelled = True
        self.stop()


class Positions(ui.View):
    def __init__(self):
        super().__init__()
        self._selects: list = []

    @ui.button(label="LW", custom_id="LW", style=ButtonStyle.blurple)
    async def LW(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="RW", custom_id="RW", style=ButtonStyle.blurple)
    async def RW(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="LD", custom_id="LD", style=ButtonStyle.blurple)
    async def LD(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="RD", custom_id="RD", style=ButtonStyle.blurple)
    async def RD(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="C", custom_id="C", style=ButtonStyle.blurple)
    async def C(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="G", custom_id="G", style=ButtonStyle.blurple)
    async def G(self, button: ui.Button, ita: Interaction):
        if button.custom_id in self._selects:
            self._selects.remove(button.custom_id)
            button.label = button.custom_id
            button.style = ButtonStyle.blurple
        else:
            self._selects.append(button.custom_id)
            button.label = f"{button.custom_id} (Selected)"
            button.style = ButtonStyle.red

        await ita.response.edit_message(view=self)

    @ui.button(label="Done", style=ButtonStyle.green)
    async def done(self, button: ui.Button, ita: Interaction):
        self.stop()
