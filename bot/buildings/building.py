from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple

from bot.macro.expansion_manager import Expansions, get_expansions
from bot.macro.resources import Resources
from bot.utils.matchup import Matchup, get_matchup
from bot.utils.point2_functions import dfs_in_pathing
from sc2.bot_ai import BotAI
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

if TYPE_CHECKING:
    from .builder import Builder

class Building:
    bot: BotAI
    builder: Builder
    unitId: UnitTypeId
    abilityId: Optional[AbilityId] = None
    name: str
    radius: float = 1

    def __init__(self, build: Builder):
        self.bot = build.bot
        self.builder = build

    @property
    def matchup(self) -> Matchup:
        return get_matchup(self.bot)
    
    @property
    def expansions(self) -> Expansions:
        return get_expansions(self.bot)
    
    @property
    def conditions(self) -> bool:
        pass

    @property
    def position(self) -> Point2:
        pass

    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        building_cost: Cost = self.bot.calculate_cost(self.unitId)
        can_build: bool
        resources_updated: Resources
        can_build, resources_updated = resources.update(building_cost)
        if (can_build == False):
            return resources_updated
        
        print(f'Build {self.name}')
        position: Point2 = dfs_in_pathing(self.bot, self.position, self.bot.game_info.map_center, self.radius)
        await self.builder.build(self.unitId, position)
        return resources_updated