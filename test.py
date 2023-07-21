from dataclasses import dataclass


@dataclass
class Member:
    display_name: str


def get_played_games(
        old_game_data: dict, new_game_data: dict, member: Member
):
    if old_game_data and new_game_data:
        if member.display_name in old_game_data and member.display_name in new_game_data:
            return new_game_data[member.display_name] - old_game_data[member.display_name]

        elif member.display_name in new_game_data:
            return new_game_data[member.display_name]

        else:
            return 0

    if new_game_data and member.display_name in new_game_data:
        return new_game_data[member.display_name]

    return 0


old_game_data = {
    "x": 1,
}

new_game_data = {
    "x": 3,
}

print(get_played_games(old_game_data, None, Member("x")))