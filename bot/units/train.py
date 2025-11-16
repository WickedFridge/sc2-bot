from __future__ import annotations
from ast import List
from typing import TYPE_CHECKING

from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.utils.fake_order import FakeOrder
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from bot.utils.unit_supply import get_unit_supply
from bot.utils.unit_tags import worker_types

if TYPE_CHECKING:
    from .trainer import Trainer

class Train:
    bot: Superbot
    trainer: Trainer
    unitId: UnitTypeId
    buildingIds: List[UnitTypeId]
    order_id: AbilityId
    name: str
    i: int = 0
    check_build_order: bool = False
        
    def __init__(self, trainer: Trainer) -> None:
        self.bot = trainer.bot
        self.trainer = trainer
    
    @property
    def default_conditions(self) -> bool:
        return (
            self.bot.supply_used + get_unit_supply(self.unitId) <= self.bot.supply_cap
            and self.building_group.amount >= 1
            and (
                self.unitId in worker_types
                or self.bot.composition_manager.should_train(self.unitId)
            )
        )
    
    @property
    def custom_conditions(self) -> bool:
        return True

    @property
    def conditions(self) -> bool:
        return self.default_conditions and self.custom_conditions

    @property
    def building_group(self) -> Units:
        return self.bot.structures(self.buildingIds).ready.filter(
            lambda building: (
                len(building.orders) == 0 or
                (
                    len(building.orders) == 1
                    and building.orders[0].progress >= 0.95
                )
            )
        )

    @property
    def training_cost(self) -> Cost:
        return self.bot.calculate_cost(self.unitId)

    def log(self, i: int) -> None:
        print(f'Train {self.name}')

    def on_complete(self):
        if (self.bot.build_order.build.is_completed):
            return
        checked: bool = self.bot.build_order.build.check(self.unitId)
        if (self.check_build_order and not checked):
            print(f'Error check build order for step {self.unitId}')
            print(f'pending ids: {self.bot.build_order.build.pending_ids}')

    async def train(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        self.i = 0
        resources_updated: Resources = resources
        for building in self.building_group:
            if (not self.conditions):
                return resources_updated
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(self.training_cost)
            if (can_build == False):
                return resources_updated            
            self.log(self.i)
            building.train(self.unitId)
            # add a fake order so that other function know that we are not idle anymore
            building.orders.append(FakeOrder(self.order_id))
            self.i += 1
            self.on_complete()
        return resources_updated