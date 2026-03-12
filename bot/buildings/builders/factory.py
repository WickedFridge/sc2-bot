from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Factory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORY
        self.unitIdFlying = UnitTypeId.FACTORYFLYING
        self.name = "Factory"

    @override
    @property
    def custom_conditions(self) -> bool:
        max_factories: int = 2

        # We want up to 2 factories so far
        return (
            self.amount == 0 or (
                self.amount < max_factories
                and self.bot.composition_manager.composition[UnitTypeId.THOR] > self.amount
            )
        )
    
    @override
    @property
    def position(self) -> Point2:
        if (self.bot.build_order.build.name in ['Defensive Cyclone']):
            raxes: Units = self.bot.structures(UnitTypeId.BARRACKS).ready
            if (raxes.amount > 0):
                return raxes.first.position.towards(self.bot.expansions.main.position, 2.5)
        return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 4)