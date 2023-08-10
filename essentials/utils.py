def get_team_name(name: str, prefix: str = None):
    name = name[4:].replace(" ", "-").replace(".", "").lower()
    if prefix:
        name = prefix + name

    return name
