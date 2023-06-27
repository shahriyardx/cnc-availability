from dataclasses import dataclass
from typing import Union

import gspread
from gspread import Spreadsheet


@dataclass
class DataSheet:
    name: str
    sheet: Spreadsheet = None

    def __post_init__(self):
        self.connection = gspread.service_account("credentials.json")
        self.sheet = self.connection.open(self.name)

    def add_row(self, sheet: str, row_count: int = 10):
        self.sheet.worksheet(sheet).add_rows(row_count)

    def get_values(self, sheet_name: str):
        return self.sheet.worksheet(sheet_name).get_all_values()

    def insert(self, sheet: str, data: list, start: str = "A", end: str = None):
        total_values = len(self.sheet.worksheet(sheet).get_all_values()) + 1
        end = end or next_char(start, len(data))

        pos = f"{start}{total_values}:{end}{total_values}"
        self.sheet.worksheet(sheet).update(pos, [data])

    def append(self, sheet: str, data: list):
        self.sheet.worksheet(sheet).append_row(data)

    def update(self, sheet_name: str, position: str = "A", data: Union[list, str, int] = None):
        self.sheet.worksheet(sheet_name).update(position, data)


def next_char(start: str, count: int) -> str:
    next_code = ord(start) + count
    if next_code <= ord("Z"):
        return chr(next_code)
    else:
        return chr(next_code - 26)
