from __future__ import annotations
from collections.abc import Iterator
import math
from typing import Any, Callable, Generator, List, Optional
from bot.macro.expansion import Expansion
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class Expansions(List):
    bot: BotAI
    expansions: List[Expansion]

    def __init__(self, bot: BotAI, expansions: List[Expansion] = []) -> None:
        self.bot = bot
        self.expansions = expansions

    def __iter__(self) -> Generator[Expansion, None, None]:
        return (item for item in self.expansions)

    def filter(self, pred: Callable[[Expansion], Any]) -> Expansions:
        return Expansions(self.bot, list(filter(pred, self)))
    
    @property
    def amount(self) -> int:
        return self.expansions.__len__()
    
    @property
    def amount_taken(self) -> int:
        expansion_count: int = 0
        for expansion in self.expansions:
            if (expansion.is_taken):
                expansion_count += 1
        return expansion_count
    
    @property
    def positions(self) -> List[Point2]:
        positions: List[Point2] = []
        for expansion in self.expansions:
            positions.append(expansion.position)
        return positions
    
    @property
    def taken(self) -> Expansions:
        return self.filter(lambda expansion: expansion.is_taken == True)
    
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
    def last(self) -> Optional[Expansion]:
        taken_expansions: Expansions = self.taken
        if (taken_expansions.amount == 0):
            return None
        return taken_expansions.expansions[taken_expansions.amount - 1]
    
    @property
    def next(self) -> Expansion:
        taken_expansions: Expansions = self.taken
        return self.expansions[taken_expansions.amount]

    @property
    def townhalls(self) -> Units:
        ccs: List[Unit] = []
        for expo in self.taken.expansions:
            ccs.append(expo.cc)
        return Units(ccs, self.bot)
    
    
    def townhalls_not_on_slot(self, type_id: Optional[UnitTypeId] = None) -> Units:
        townhalls: Units = self.bot.townhalls
        all_townhalls: Units = (
            townhalls if not type_id
            else townhalls(type_id)
        )
        return all_townhalls.filter(lambda townhall: townhall.tag not in self.townhalls.tags)

    def closest_to(self, unit: Unit | Point2) -> Expansion:
        positions: List[Point2] = self.positions.copy()
        positions.sort(key = lambda point: point.distance_to(unit))
        return positions[0]

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