from __future__ import annotations
from ast import List
from typing import TYPE_CHECKING

from bot.macro.resources import Resources
from bot.superbot import Superbot
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from bot.utils.unit_supply import supply


if TYPE_CHECKING:
    from .trainer import Trainer

class Train:
    bot: Superbot
    trainer: Trainer
    unitId: UnitTypeId
    buildingIds: List[UnitTypeId]
    name: str

    def __init__(self, trainer: Trainer) -> None:
        self.bot = trainer.bot
        self.trainer = trainer
    
    @property
    def default_conditions(self) -> bool:
        return (
            self.bot.supply_used + supply[self.unitId] <= self.bot.supply_cap
            and self.building_group.amount > 0
        )
    
    @property
    def custom_conditions(self) -> bool:
        return True

    @property
    def conditions(self) -> bool:
        return self.default_conditions and self.custom_conditions

    @property
    def building_group(self) -> Units:
        buildings: Units = Units([], self.bot)
        for buildingId in self.buildingIds:
            buildings += self.bot.structures(buildingId).ready.idle
        return buildings

    @property
    def training_cost(self) -> Cost:
        return self.bot.calculate_cost(self.unitId)

    def log(self, i: int) -> None:
        print(f'Train {self.name}')

    async def train(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        resources_updated: Resources = resources
        i: int = 0
        for building in self.building_group:
            if (not self.conditions):
                return resources_updated
            can_build: bool
            resources_updated: Resources
            can_build, resources_updated = resources.update(self.training_cost)
            if (can_build == False):
                return resources_updated            
            self.log(i)
            building.train(self.unitId)
            i += 1
        return resources_updated