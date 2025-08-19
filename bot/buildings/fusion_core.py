
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class FusionCore(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FUSIONCORE
        self.name = "Fusion Core"

    @override
    @property
    def conditions(self) -> bool:
        fusion_core_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.FUSIONCORE)
        fusion_core_count: int = self.bot.structures(UnitTypeId.FUSIONCORE).ready.amount + self.bot.already_pending(UnitTypeId.FUSIONCORE)
        starport_count: float = (
            self.bot.structures(UnitTypeId.STARPORT).amount
            + self.bot.structures(UnitTypeId.STARPORTFLYING).amount
            + self.bot.already_pending(UnitTypeId.STARPORT)
        )
        medivac_count: float = self.bot.units(UnitTypeId.MEDIVAC).amount + self.bot.already_pending(UnitTypeId.MEDIVAC)

        # We want a fusion core once we have a second starport and at least two medivacs
        return (
            fusion_core_tech_requirement == 1
            and fusion_core_count < 1
            and self.bot.townhalls.ready.amount >= 4
            and starport_count >= 1
            and medivac_count >= 6
            and self.bot.supply_used >= 160
        )
    
    @override
    @property
    def position(self) -> Point2:
        expansion: Expansion = self.bot.expansions.taken.random
        if (not expansion):
            return self.bot.expansions.main.position
        units_pool: Units = expansion.mineral_fields + expansion.vespene_geysers
        selected_position: Point2 = units_pool.random.position if units_pool.amount >= 1 else expansion.position
        offset: Point2 = selected_position.negative_offset(expansion.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, 2)