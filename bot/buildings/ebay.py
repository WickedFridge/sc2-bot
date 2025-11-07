
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.units import Units
from bot.utils.unit_tags import cloaked_units, menacing


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
        need_detection: bool = UpgradeId.BURROW in self.bot.scouting.known_enemy_upgrades
        cloaked_attacking_units: Units = self.bot.scouting.known_enemy_army.units(cloaked_units).filter(lambda unit: unit.can_attack or unit.type_id in menacing)

        # If we can't build ebays yet, don't
        if (ebay_tech_requirement < 1):
            return False
    
        # If we need detection and have no ebays, build one
        if (
            ebays_count == 0
            and need_detection
            and cloaked_attacking_units.amount >= 1
        ):
            return True
        
        # We want 2 ebays once we have a 3rd CC and a Starport
        return (
            ebays_count < 2
            and self.bot.townhalls.amount >= 3
            and starport_count >= 1
            and medivac_count >= 2
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