
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.utils.point2_functions.utils import position_behind_worker_line
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class FusionCore(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FUSIONCORE
        self.name = "Fusion Core"
        self.max_amount = 1

    @property
    @override
    def custom_conditions(self) -> bool:
        starport_count: float = (
            self.bot.structures(UnitTypeId.STARPORT).amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).amount
            + self.bot.already_pending(UnitTypeId.STARPORT)
        )
        medivac_count: float = self.bot.units(UnitTypeId.MEDIVAC).amount + self.bot.already_pending(UnitTypeId.MEDIVAC)

        # We want a fusion core once we have 4 finished CCs, 160 supply and at least 5 medivacs
        return (
            self.bot.townhalls.ready.amount >= 4
            and starport_count >= 1
            and medivac_count >= 5
            and self.bot.supply_used >= 160
        )
    
    @property
    @override
    def position(self) -> Point2:
        expansion: Expansion = self.bot.expansions.taken.random
        if (not expansion):
            return self.bot.expansions.main.position
        base_ressources: Units = expansion.mineral_fields + expansion.vespene_geysers
        return position_behind_worker_line(base_ressources, expansion.position, random=True)
