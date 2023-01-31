"""
@author: Hassan Mohamed 
@doc: Helper functions used by the main script.
"""
import logging
import os
import unicodedata
from dataclasses import dataclass
from enum import Enum

import bs4
import pandas as pd
import requests

SOCCERSTATS_URL = "https://www.soccerstats.com/"


@dataclass
class Score:
    home_team: int
    away_team: int


@dataclass
class MatchData:
    home_team: str
    away_team: str
    FT: Score
    HT: Score


class Leagues(Enum):
    """A class that stores the names of the leagues and their corresponding code name on soccer stats"""

    ENGLAND_PREMIERE_LEAGUE = "england"
    ENGLAND_CHAMPIONSHIP = "england2"
    SPAIN_LIGA_SEGUNDA = "spain2"
    FRANCE_LIGUE_1 = "france"


def get_avaliable_seasons(league: str) -> list[str]:
    """Get The number of seasons avaliable in soccer stats for the league.

    Args:
        League (str): The Name of the league.
    """
    league_url = f"{SOCCERSTATS_URL}results.asp?league={league}"
    page = requests.get(league_url).text
    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(page, "html.parser")

    # Find The drop-down button that contains the links to all the seasons.
    seasons = soup.find(name="a", string="2022/23").parent.children

    # Extract links and store them.
    avaliable_seasons_links = []
    for season in seasons:
        if isinstance(season, bs4.element.NavigableString):
            continue
        url: str = season["href"]
        url = url.replace("latest", "results")
        avaliable_seasons_links.append(url)

    return avaliable_seasons_links


def get_match_week_links(season_url: str, league: list[str]) -> list[str]:
    """Return a list with links to the matchweeks.

    Args:
        season_url (str): a str that points to the results.asp page of the league.

    Returns:
        list[str]: with the urls of each week.
    """

    season = requests.get(season_url).text
    soup = bs4.BeautifulSoup(season, "html.parser")
    weeks = soup.find_all(name="a", class_="horiz")
    matchweeks_links = []
    cur_week = 1
    for week in weeks:
        if (
            week["href"].find(league) == -1
            or week["href"].find("results") == -1
            or week["href"].find("grid") != -1
            or week["href"].find("pmtype=round") == -1
            or week["href"].find(f"round{cur_week}") == -1
        ):
            continue
        matchweeks_links.append(SOCCERSTATS_URL + week["href"])
        cur_week += 1

    return matchweeks_links


def scrape_match_week_data(
    match_week,
) -> list[MatchData]:
    """
    Scrpaes the data of the week.
    returns a list of named_tubles that looks like this:
    [
        {
            "home_team": "Blackburn",
            "away_team": "Cardiff City",
            "HT": [1, 1],
            "FT": [1, 1],
        }
    ]
    """
    week = requests.get(match_week).text
    soup = bs4.BeautifulSoup(week, "html.parser")
    table = soup.find(id="btable")
    matches = table.find_all(name="tr", class_="odd")

    matches_data = []
    match: bs4.Tag
    for match in matches:
        try:
            # Scrape the data from the row.
            home_team = match.find_all(name="td", align="right")[1].text
            away_team = match.find(name="td", align="left").text
            full_time_score = match.find(name="td", align="center").text
            ft = full_time_score.split("-")

            half_time_score = match.find_all(name="td", align="center")[2].text
            half_time_score = half_time_score.replace("(", "")
            half_time_score = half_time_score.replace(")", "")
            ht = half_time_score.split("-")
        except Exception as e:
            print(e)
            print(match_week)
            continue

        # Skip over matches that isn't played yet or post-poned.
        if ht == [""]:
            continue

        matches_data.append(
            MatchData(
                unicodedata.normalize("NFKC", home_team),
                unicodedata.normalize("NFKC", away_team),
                Score(int(ft[0]), int(ft[1])),
                Score(int(ht[0]), int(ht[1])),
            )
        )
    return matches_data


def calculate_parameters(data: list[MatchData]) -> list[int]:
    """Takes the weekly data of the matches and returns the 22 parameteres.

    Args:
        data (list[MatchData]): the data of week.

    Returns:
        list[int]: a list of 22 parameters that are used for the research.
    """
    values = {
        "nbr_games_played": len(data),
        "nbr_games_00_ft": 0,
        "nbr_games_00_ht": 0,
        "nbr_games_min_1_ht": 0,
        "nbr_games_min_2_ht": 0,
        "nbr_games_min_3_ht": 0,
        "nbr_games_max_1_ht": 0,
        "nbr_games_both_teams_score_FT": 0,
        "nbr_games_both_teams_score_HT": 0,
        "nbr_games_min_1_ft": 0,
        "nbr_games_min_2_ft": 0,
        "nbr_games_min_3_ft": 0,
        "nbr_games_min_4_ft": 0,
        "nbr_games_min_5_ft": 0,
        "nbr_games_max_1_ft": 0,
        "nbr_games_max_2_ft": 0,
        "nbr_games_max_3_ft": 0,
        "nbr_games_home_team_ft": 0,
        "nbr_games_away_team_ft": 0,
        "nbr_games_draw_ft": 0,
        "nbr_games_draw_ht": 0,
        "nbr_games_home_team_ht": 0,
        "nbr_games_away_team_ht": 0,
    }

    # Type Annotations.
    for match_data in data:
        # Check for zero-zero score. (1&2)
        if match_data.FT.home_team == 0 and match_data.FT.away_team == 0:
            values["nbr_games_00_ft"] += 1
        if match_data.HT.home_team == 0 and match_data.HT.away_team == 0:
            values["nbr_games_00_ht"] += 1

        # Check for the minumum goals at HT (3-5)
        total_score_ht = match_data.HT.home_team + match_data.HT.away_team
        if total_score_ht >= 3:
            values["nbr_games_min_3_ht"] += 1
        if total_score_ht >= 2:
            values["nbr_games_min_2_ht"] += 1
        if total_score_ht >= 1:
            values["nbr_games_min_1_ht"] += 1

        # Check for the maximum goals at HT (6)
        if total_score_ht <= 1:
            values["nbr_games_max_1_ht"] += 1

        # Check if they both scored at HT and FT
        if match_data.FT.away_team > 0 and match_data.FT.home_team > 0:
            values["nbr_games_both_teams_score_FT"] += 1
        if match_data.HT.away_team > 0 and match_data.HT.home_team > 0:
            values["nbr_games_both_teams_score_HT"] += 1

        # Check for the minimum goals at FT (9-13)
        total_score_ft = match_data.FT.home_team + match_data.FT.away_team
        # WE don't ELIF as we need  to increase all values if a value is correct.
        if total_score_ft >= 5:
            values["nbr_games_min_5_ft"] += 1
        if total_score_ft >= 4:
            values["nbr_games_min_4_ft"] += 1
        if total_score_ft >= 3:
            values["nbr_games_min_3_ft"] += 1
        if total_score_ft >= 2:
            values["nbr_games_min_2_ft"] += 1
        if total_score_ft >= 1:
            values["nbr_games_min_1_ft"] += 1

        # Check for the maximum goals at FT
        if total_score_ft <= 3:
            values["nbr_games_max_3_ft"] += 1
        if total_score_ft <= 2:
            values["nbr_games_max_2_ft"] += 1
        if total_score_ft <= 1:
            values["nbr_games_max_1_ft"] += 1

        # Check for the team winning at FT. (17&19)
        if match_data.FT.home_team > match_data.FT.away_team:
            values["nbr_games_home_team_ft"] += 1
        if match_data.FT.home_team < match_data.FT.away_team:
            values["nbr_games_away_team_ft"] += 1

        # Check for the team winning at HT. (20&22)
        if match_data.HT.home_team > match_data.HT.away_team:
            values["nbr_games_home_team_ht"] += 1
        if match_data.HT.home_team < match_data.HT.away_team:
            values["nbr_games_away_team_ht"] += 1

        # Check for draws. (18-21)
        if match_data.FT.home_team == match_data.FT.away_team:
            values["nbr_games_draw_ft"] += 1
        if match_data.HT.home_team == match_data.HT.away_team:
            values["nbr_games_draw_ht"] += 1
    return values


def scrape_season_data(season: str, league: str, league_name: str, season_name: str) -> None:
    """Scrapes all matchweeks' data from a season of a team."""

    print(f"Downloading {season_name}")
    season_url = SOCCERSTATS_URL + season
    season_data = []
    match_weeks = get_match_week_links(season_url, league)
    for match_week in match_weeks:
        season_data.append(scrape_match_week_data(match_week))

    print(f"Finished Downloading {season_name}")
    print(season_data)
    if not season_data:
        print(f"No Data for {season_name}")
        return

    print(f"Start Processing {season_name}")
    data = []
    for week_data in season_data:
        data.append(calculate_parameters(week_data))
    print(f"Finished Processing {season_name}, adding to excel...")

    # Set The dataframe ready to extract!
    df = pd.DataFrame.from_dict(data)
    df.index += 1
    df.index.name = "match_week"
    file_name = f"{league_name}.xlsx"

    if not os.path.exists(file_name):
        with pd.ExcelWriter(file_name, mode="w", engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=season_name)
    else:
        with pd.ExcelWriter(
            file_name, mode="a", engine="openpyxl", if_sheet_exists="replace"
        ) as writer:
            df.to_excel(writer, sheet_name=season_name)


def extract_season_name(season_link: str) -> str:
    league = season_link.split("=")[1]
    league = league.split("_")
    # If there's no season name then it is the current season.
    # Must be Updated after the season change i.e. next year!
    if len(league) == 1:
        return "2022-23"
    ans = int(league[1])
    return f"{ans-1}-{str(ans)[2:]}"
