from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class Factory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORY
        self.unitIdFlying = UnitTypeId.FACTORYFLYING
        self.name = "Factory"

    @override
    @property
    def custom_conditions(self) -> bool:
        max_factories: int = 1

        # We want 1 factory so far
        return (
            self.amount < max_factories
        )
    
    @override
    @property
    def position(self) -> Point2:
        return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 4)            