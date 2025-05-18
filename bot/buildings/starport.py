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
    def conditions(self) -> bool:
        starport_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.STARPORT)
        max_starport: int = 1

        # We want 1 starport so far
        return (
            starport_tech_requirement == 1
            and self.bot.townhalls.amount >= 2
            and self.starport_amount < max_starport
        )
    
    @override
    @property
    def position(self) -> Point2:
        factories: Units = self.bot.structures(UnitTypeId.FACTORY).ready + self.bot.structures(UnitTypeId.FACTORYFLYING)
        return factories.first.position.towards(self.bot.game_info.map_center, 2)