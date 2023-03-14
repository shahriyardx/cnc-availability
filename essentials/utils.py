def get_team_channel(name: str):
    return name[4:].replace(" ", "-").replace(".", "").lower()
