def get_team_name(name: str):
    return name[4:].replace(" ", "-").replace(".", "").lower()
