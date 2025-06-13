from __future__ import annotations
import math
import random
from typing import Any, Callable, Generator, List, Optional
from bot.macro.expansion import Expansion
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

expansions: Expansions | None = None

class Expansions:
    bot: BotAI
    expansions: List[Expansion]

    def __init__(self, bot: BotAI, expansions: Optional[List[Expansion]] = None) -> None:
        self.bot = bot
        self.expansions = expansions if expansions is not None else []

    def __iter__(self) -> Generator[Expansion, None, None]:
        return (item for item in self.expansions)

    def __getitem__(self, index: int) -> Expansion:
        return self.expansions[index]

    def __len__(self) -> int:
        return len(self.expansions)

    def filter(self, pred: Callable[[Expansion], Any]) -> Expansions:
        return Expansions(self.bot, list(filter(pred, self)))
    
    def copy(self) -> Expansions:
        return Expansions(self.bot, self.expansions.copy())

    def sort(self, key: Optional[Callable[[Expansion], Any]] = None, reverse: bool = False) -> None:
        self.expansions.sort(key=key, reverse=reverse)
    
    def sorted(self, key: Optional[Callable[[Expansion], Any]] = None, reverse: bool = False) -> Expansions:
        # Return a new Expansions object with the list sorted, without mutating the original.
        sorted_expansions = sorted(self.expansions, key=key, reverse=reverse)
        return Expansions(self.bot, sorted_expansions)
    
    @property
    def amount(self) -> int:
        return self.expansions.__len__()
    
    @property
    def first(self) -> Expansion:
        return self.expansions[0]
    
    @property
    def last(self) -> Expansion:
        return self.expansions[self.amount -1]
    
    @property
    def amount_taken(self) -> int:
        expansion_count: int = 0
        for expansion in self.expansions:
            if (expansion.is_taken):
                expansion_count += 1
        return expansion_count
    
    @property
    def positions(self) -> List[Point2]:
        return [expansion.position for expansion in self.expansions]
    
    @property
    def taken(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_taken == True)
    
    @property
    def ready(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_ready == True)

    @property
    def free(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_taken == False)

    @property
    def defended(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_defended == True)
    
    @property
    def not_defended(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_defended == False)
    
    @property
    def without_main(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_main == False)
    
    @property
    def random(self) -> Optional[Expansion]:
        if (len(self.expansions) == 0):
            return None
        return random.choice(self.expansions)
    
    @property
    def main(self) -> Optional[Expansion]:
        return self.expansions[0]
    
    @property
    def b2(self) -> Optional[Expansion]:
        return self.expansions[1]

    @property
    def b3(self) -> Optional[Expansion]:
        return self.expansions[2]

    @property
    def b4(self) -> Optional[Expansion]:
        return self.expansions[3]
    
    @property
    def enemy_main(self) -> Optional[Expansion]:
        return self.expansions[self.expansions.__len__() - 1]
    
    @property
    def enemy_b2(self) -> Optional[Expansion]:
        return self.expansions[self.expansions.__len__() - 2]
    
    @property
    def enemy_b3(self) -> Optional[Expansion]:
        return self.expansions[self.expansions.__len__() - 3]

    @property
    def enemy_b4(self) -> Optional[Expansion]:
        return self.expansions[self.expansions.__len__() - 4]
    
    @property
    def last_taken(self) -> Optional[Expansion]:
        taken_expansions: Expansions = self.taken
        if (taken_expansions.amount == 0):
            return None
        return taken_expansions.expansions[taken_expansions.amount - 1]
    
    @property
    def next(self) -> Expansion:
        taken_expansions: Expansions = self.taken
        if (taken_expansions.amount == self.amount):
            return self.last_taken
        return self.free[0]

    @property
    def townhalls(self) -> Units:
        return Units([expansion.cc for expansion in self.taken.expansions], self.bot)
    
    @property
    def mineral_fields(self) -> Units:
        return Units([expansion.mineral_fields for expansion in self.taken.expansions], self.bot)

    @property
    def vespene_geysers(self) -> Units:
        return Units([expansion.vespene_geysers for expansion in self.taken.expansions], self.bot)

    @property
    def minerals(self) -> int:
        return sum(expansion.minerals for expansion in self.expansions)

    @property
    def vespene(self) -> int:
        return sum(expansion.vespene for expansion in self.expansions)
    
    def townhalls_not_on_slot(self, type_id: Optional[UnitTypeId] = None) -> Units:
        townhalls: Units = self.bot.townhalls
        all_townhalls: Units = (
            townhalls if not type_id
            else townhalls(type_id)
        )
        return all_townhalls.filter(lambda townhall: townhall.tag not in self.townhalls.tags)

    def closest_to(self, unit: Unit | Point2) -> Expansion:
        expansions: List[Expansion] = self.expansions.copy()
        expansions.sort(key = lambda expo: expo.position.distance_to(unit))
        return expansions[0]

    async def set_expansion_list(self):
        expansions: List[Expansion] = []
        for location in self.bot.expansion_locations_list:
            player_start: Point2 = self.bot.game_info.player_start_location
            enemy_start: Point2 = self.bot.enemy_start_locations[0]
            d = await self.bot.client.query_pathing(player_start, location)
            enemy_d = await self.bot.client.query_pathing(enemy_start, location)
            if (d is None or enemy_d is None):
                continue
            expansions.append(Expansion(self.bot, location, d - enemy_d))
        expansions.append(Expansion(self.bot, player_start, -math.inf))
        expansions.append(Expansion(self.bot, enemy_start, math.inf))
        expansions.sort(key = lambda expansion: expansion.distance_from_main)
        
        self.expansions = expansions

def get_expansions(bot: WickedBot) -> Expansions:
    global expansions
    if (expansions is None):
        expansions = Expansions(bot)
    return expansions