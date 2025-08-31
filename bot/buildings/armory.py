from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class Armory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.ARMORY
        self.name = "Armory"

    @override
    @property
    def conditions(self) -> bool:
        armory_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.ARMORY)
        upgrades_tech_requirement: float = self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
        armory_count: int = self.bot.structures(UnitTypeId.ARMORY).ready.amount + self.bot.already_pending(UnitTypeId.ARMORY)
        ebays_count: int = self.bot.structures(UnitTypeId.ENGINEERINGBAY).ready.amount

        # We want 1 armory once we have a +1 60% complete
        return (
            armory_tech_requirement == 1
            and upgrades_tech_requirement >= 0.6
            and armory_count == 0
            and self.bot.townhalls.amount >= 1
            and ebays_count >= 1
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