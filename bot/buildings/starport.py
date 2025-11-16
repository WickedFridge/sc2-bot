from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class Starport(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.STARPORT
        self.name = "Starport"

    @property
    def starport_amount(self) -> int:
        return (
            self.bot.structures(UnitTypeId.STARPORT).ready.amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).ready.amount
            + self.bot.already_pending(UnitTypeId.STARPORT)
        )
    
    @override
    @property
    def custom_conditions(self) -> bool:
        starport_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.STARPORT)
        if (starport_tech_requirement < 1):
            return False
        
        # We want 1st starport after we have a 2nd base
        if (self.starport_amount == 0):
            return self.bot.townhalls.amount >= 2
        
        
        # TODO we will see this later
        # We want 2nd starport after we have a 3rd base if our composition is mostly air units
        if (self.starport_amount == 1):
            return (
                self.bot.townhalls.amount >= 3
                and (
                    self.bot.composition_manager.vikings_amount >= 8
                    or self.bot.composition_manager.composition[UnitTypeId.RAVEN] >= 1
                )
            )
        return False
            
    @override
    @property
    def position(self) -> Point2:
        factories: Units = self.bot.structures(UnitTypeId.FACTORY).ready + self.bot.structures(UnitTypeId.FACTORYFLYING)
        return factories.first.position.towards(self.bot.game_info.map_center, 2)