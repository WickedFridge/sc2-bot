from typing import override
from bot.buildings.building import Building
from bot.strategy.build_order.bo_names import BuildOrderName
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Factory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORY
        self.unitIdFlying = UnitTypeId.FACTORYFLYING
        self.name = "Factory"

    @property
    @override
    def custom_conditions(self) -> bool:
        if (not self.bot.build_order.build.is_completed):
            return True

        # We want up to 3 factories so far
        max_factories: int = 3

        tank_target: int = self.bot.composition_manager.composition[UnitTypeId.SIEGETANK]
        cyclone_target: int = self.bot.composition_manager.composition[UnitTypeId.CYCLONE]
        thor_target: int = self.bot.composition_manager.composition[UnitTypeId.THOR]
        hellion_target: int = self.bot.composition_manager.composition[UnitTypeId.HELLION]
        
        return (
            self.amount == 0 or (
                self.amount < max_factories
                and self.bot.expansions.amount_taken >= self.amount * 2
                and (
                    thor_target * 2
                    + tank_target
                    + cyclone_target
                    + hellion_target / 2 > 6 * self.amount
                )
            )
        )
    
    @property
    @override
    def position(self) -> Point2:
        return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 4)