from __future__ import annotations
from typing import TYPE_CHECKING, List

from bot.macro.resources import Resources
from bot.strategy.strategy_types import Situation
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
    requirements_ups_completed: List[UpgradeId] = []
    requirements_buildings: List[UnitTypeId] = []
    name: str
    is_ability: bool = False
    block_gas_only: bool = False
    ignore_build_order: bool = False
    
    def __init__(self, search_manager: Search):
        self.bot = search_manager.bot
    
    @property
    def in_build_order(self) -> bool:
        return self.upgrade in self.bot.build_order.build.pending_ids
        
    
    @property
    def custom_conditions(self) -> bool:
        return True

    @property
    def _build_order_ok(self) -> bool:
        """Cas où l'upgrade fait partie du build order en cours."""
        return (
            self.in_build_order
            and (
                self.bot.scouting.situation == Situation.STABLE
                or self.custom_conditions
            )
        )

    @property
    def _free_research_ok(self) -> bool:
        """Cas où le build order est terminé (ou ignoré) et qu'on recherche librement."""
        return (
            self.custom_conditions
            and (self.bot.build_order.build.is_completed or self.ignore_build_order)
            and self._upgrade_requirements_met
            and self._building_requirements_met
        )

    @property
    def _upgrade_requirements_met(self) -> bool:
        return (
            all(self.bot.already_pending_upgrade(req) > 0 for req in self.requirements_ups)
            and all(self.bot.already_pending_upgrade(req) == 1 for req in self.requirements_ups_completed)
        )

    @property
    def _building_requirements_met(self) -> bool:
        return all(
            self.bot.structures(building_type).ready.amount >= 1
            for building_type in self.requirements_buildings
        )
    
    @property
    def conditions(self) -> bool:
        return (
            self.bot.already_pending_upgrade(self.upgrade) == 0
            and self.bot.structures(self.building).ready.idle.amount >= 1
            and (self._build_order_ok or self._free_research_ok)
        )
    
    def on_complete(self):
        pass
    
    async def search(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        searching_cost: Cost = self.bot.calculate_cost(self.upgrade)
        enough_resources: bool
        resources_updated: Resources
        enough_resources, resources_updated = resources.update(searching_cost)
        if (enough_resources == False):
            if (
                self.block_gas_only
                and resources_updated.vespene.short
                and resources_updated.minerals.short
            ):
                resources_updated.minerals.short = False
            return resources_updated
        
        print("Search", self.name)
        building: Unit = self.bot.structures(self.building).ready.idle.random
        if (self.is_ability):
            building(self.ability)
        else:
            building.research(self.upgrade)
        # add a fake order to the building so that we know it's not idle anymore
        building.orders.append(FakeOrder(self.ability))
        self.on_complete()
        return resources_updated