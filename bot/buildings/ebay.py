
from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class Ebay(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ENGINEERINGBAY
        self.name = "Ebay"

    @override
    @property
    def conditions(self) -> bool:
        ebay_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.ENGINEERINGBAY)
        ebays_count: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready.amount + self.bot.already_pending(UnitTypeId.ENGINEERINGBAY)
        starport_count: float = (
            self.bot.structures(UnitTypeId.STARPORT).amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).amount
            + self.bot.already_pending(UnitTypeId.STARPORT)
        )
        medivac_count: float = self.bot.units(UnitTypeId.MEDIVAC).amount + self.bot.already_pending(UnitTypeId.MEDIVAC)

        # We want 2 ebays once we have a 3rd CC and a Starport
        return (
            ebay_tech_requirement == 1
            and ebays_count < 2
            and self.bot.townhalls.amount >= 3
            and starport_count >= 1
            and medivac_count >= 2
        )
    
    @override
    @property
    def position(self) -> Point2:
        return self.bot.townhalls.ready.center