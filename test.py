from dataclasses import dataclass


@dataclass
class Member:
    id: int = 123


def get_played_games(
    old_game_data,
    new_game_data,
    member: Member,
):
    if not old_game_data:
        old_game_data = dict()

    if not new_game_data:
        new_game_data = dict()

    # in both
    if str(member.id) in old_game_data and str(member.id) in new_game_data:
        return new_game_data[str(member.id)] - old_game_data[str(member.id)]

    # not in both
    if str(member.id) not in old_game_data and str(member.id) not in new_game_data:
        return -1

    # in any of them
    if str(member.id) in new_game_data:
        return new_game_data[str(member.id)]

    else:
        return 0


print(get_played_games({}, {}, Member(123)))

