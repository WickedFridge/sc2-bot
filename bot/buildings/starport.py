from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Starport(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.STARPORT
        self.unitIdFlying = UnitTypeId.STARPORTFLYING
        self.name = "Starport"
    
    @override
    @property
    def custom_conditions(self) -> bool:
        if (self.bot.build_order.build.is_completed == False):
            return True
        
        if (self.amount < 1):
            return True
        
        ebays_amount: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).amount

        # We want 2nd/3rd starport after we have a 3rd base and 2 Ebays if our composition is mostly air units
        return (
            self.base_amount >= 3
            and self.amount < 2
            and ebays_amount >= 2
            and (
                self.bot.composition_manager.vikings_amount >= 4 * self.amount
                or self.bot.composition_manager.composition[UnitTypeId.RAVEN] >= 1
            )
        )
            
    @override
    @property
    def position(self) -> Point2:
        factories: Units = self.bot.structures(UnitTypeId.FACTORY).ready + self.bot.structures(UnitTypeId.FACTORYFLYING)
        return factories.first.position.towards(self.bot.game_info.map_center, 2)