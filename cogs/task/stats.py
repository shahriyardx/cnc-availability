import pprint

import requests
from bs4 import BeautifulSoup


def get_rows(soup: BeautifulSoup, div_id: str):
    trs = soup.find("div", {"id": div_id}).find("table").find("tbody").find_all("tr")
    players_data = []

    for tr in trs:
        datas = tr.find_all("td")
        players_data.append(
            {
                "discord_id": datas[-1].text,
                "psn": datas[1].text.split(",")[0].strip(),
                "gp": int(datas[2].text),
            }
        )

    return players_data


def get_team_data(team_id: int, season_id: str = "99743"):  # 95020
    data = requests.get(
        "https://www.mystatsonline.com/hockey/visitor/league/stats/team_hockey.aspx?"
        f"IDLeague=63342&IDSeason={season_id}&IDTeam={team_id}"
    )
    soup = BeautifulSoup(data.content, "html.parser")
    players = get_rows(soup, "maincontent_gvSkaters_pnlPlayers")
    goalies = get_rows(soup, "maincontent_gvGoalies_pnlPlayers")

    return [players, goalies]


def get_all_team_data():
    teams = [
        147894,
        147895,
        147896,
        147897,
        147898,
        147899,
        147900,
        147901,
        147902,
        147903,
        147904,
        147905,
        147906,
        147907,
        147908,
        147909,
        147910,
        147911,
        147912,
        147913,
        147914,
        147915,
        147916,
        147917,
        147918,
        147919,
        147920,
        147921,
        147922,
        147923,
        147924,
        147925,
    ]

    players_data = {}
    goalies_data = {}

    for team in teams:
        players, goalies = get_team_data(team)
        for p in players:
            players_data[p["discord_id"]] = p["gp"]

        for p in goalies:
            goalies_data[p["discord_id"]] = p["gp"]

    for key, val in goalies_data.items():
        if key in players_data:
            players_data[key] = players_data[key] + val
        else:
            players_data[key] = val

    return players_data
