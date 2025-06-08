from __future__ import annotations
import enum
from typing import Dict
from sc2.bot_ai import BotAI
from sc2.data import Race

matchup: Matchup | None = None

class Matchup(enum.Enum):
    TvR = 0
    TvT = 1
    TvP = 2
    TvZ = 3

    def __repr__(self) -> str:
        return self.name
    
    def __str__(self) -> str:  # Override str() so print() uses your custom format
        return self.__repr__()

for item in Matchup:
    globals()[item.name] = item


def get_matchup(bot: BotAI) -> Matchup:
    global matchup
    if (matchup is None):
        matchup = define_matchup(bot.game_info.player_races)
    return matchup

def define_matchup(player_races: Dict[int, Race]) -> Matchup:
    race1: Race = player_races[1]
    race2: Race = player_races[2]
    if (race1 == race2):
        return Matchup.TvT

    if (race1 == 1):
        match(race2):
            case 4:
                return Matchup.TvR
            case 3:
                return Matchup.TvP
            case 2:
                return Matchup.TvZ

    match(race1):
        case 4:
            return Matchup.TvR
        case 3:
            return Matchup.TvP
        case 2:
            return Matchup.TvZ