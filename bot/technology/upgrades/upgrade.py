from __future__ import annotations
from ast import List
from typing import TYPE_CHECKING

from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.utils.fake_order import FakeOrder
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit

if TYPE_CHECKING:
    from ..search import Search

class Upgrade:
    bot: Superbot
    upgrade: UpgradeId
    building: UnitTypeId
    ability: AbilityId
    requirements_ups: List[UpgradeId] = []
    requirements_buildings: List[UnitTypeId] = []
    name: str
    is_ability: bool = False

    
    def __init__(self, search_manager: Search):
        self.bot = search_manager.bot
    
    @property
    def custom_conditions(self) -> bool:
        return True

    @property
    def conditions(self) -> bool:
        return (
            self.custom_conditions
            and self.bot.already_pending_upgrade(self.upgrade) == 0
            and self.bot.structures(self.building).ready.filter(lambda unit: len(unit.orders) == 0).amount >= 1
            and self.bot.tech_requirement_progress(self.upgrade) == 1
            and all(self.bot.already_pending_upgrade(requirement) > 0 for requirement in self.requirements_ups)
            and all(self.bot.structures(building).ready.amount >= 1 for building in self.requirements_buildings)
        )
    
    async def search(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        searching_cost: Cost = self.bot.calculate_cost(self.upgrade)
        can_build: bool
        resources_updated: Resources
        can_build, resources_updated = resources.update(searching_cost)
        if (can_build == False):
            return resources_updated
        
        print("Search", self.name)
        building: Unit = self.bot.structures(self.building).ready.filter(
            lambda building: len(building.orders) == 0
        ).random
        if (self.is_ability):
            building(self.ability)
        else:
            building.research(self.upgrade)
        # add a fake order to the building so that we know it's not idle anymore
        building.orders.append(FakeOrder(self.ability))
        return resources_updated