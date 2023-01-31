"""
@Author: Hassan Mohamed - https://www.upwork.com/freelancers/~01a257b2e6b6612d8e?s=1110580764771602432
@Doc: Scrapes Soccer Data from soccerstats.com, and extracts them into google sheets.
@For: Luc Delobel - https://www.upwork.com/jobs/Developing-Custom-Built-Automated-Scrapers_~01328c5b35947e74be/
"""
import os

from helpers import Leagues, extract_season_name, get_avaliable_seasons, scrape_season_data


def scrape_data(league: Leagues):
    if os.path.exists(f"./{league.name}.xlsx"):
        ans = ""
        while ans not in ["y", "n"]:
            ans = input(
                f"Found ({league.name}) already, Do you want to rescrape it (y/n)? "
            ).lower()
        if ans == "n":
            print(f"{league.name} Will not be rescraped.")
            return
        else:
            os.remove(f"{league.name}.xlsx")

    # Get all avaliable seasons in soccer stats.
    print(f"Downloading {league.name}")
    seasons_links = get_avaliable_seasons(league.value)
    # Scrape each season.
    for season_link in seasons_links:
        scrape_season_data(
            season_link, league.value, league.name, extract_season_name(season_link)
        )
    print(f"Finished {league.name}")


if __name__ == "__main__":
    # Loop over the leagues we would like to scrape.
    # They are defined in the helpers file.
    for league in Leagues:
        scrape_data(league)
