from __future__ import annotations
import enum
from typing import Dict, List
from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.unit import Unit

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
    if (matchup == Matchup.TvR):
        if (bot.enemy_units.amount >= 1):
            enemy_unit: Unit = bot.enemy_units.first
            matchup = compute_matchup(bot.race, enemy_unit.race)
    return matchup

def define_matchup(player_races: Dict[int, Race]) -> Matchup:
    race1: Race = Race(player_races[1])
    race2: Race = Race(player_races[2])
    print(f'races: {race1}, {race2}')
    return compute_matchup(race1, race2)
        
def compute_matchup(race1: Race, race2: Race) -> Matchup:
    if (race1 == race2):
        return Matchup.TvT

    if (race1 == Race.Terran):
        match(race2):
            case Race.Random:
                return Matchup.TvR
            case Race.Protoss:
                return Matchup.TvP
            case Race.Zerg:
                return Matchup.TvZ

    match(race1):
        case Race.Random:
            return Matchup.TvR
        case Race.Protoss:
            return Matchup.TvP
        case Race.Zerg:
            return Matchup.TvZ