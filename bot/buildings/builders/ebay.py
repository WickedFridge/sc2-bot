
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.utils.point2_functions.utils import position_behind_worker_line
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

    @property
    @override
    def override_conditions(self) -> bool:
        need_detection: bool = UpgradeId.BURROW in self.bot.scouting.known_enemy_upgrades

        return (
            self.in_build_order or (
                self.amount == 0
                and need_detection
            )
        )
    
    @property
    @override
    def custom_conditions(self) -> bool:
        barracks_count: float = (
            self.bot.structures(UnitTypeId.BARRACKS).ready.amount
            + self.bot.structures(UnitTypeId.BARRACKSFLYING).amount
            + max(self.bot.already_pending(UnitTypeId.BARRACKS), self.bot.structures(UnitTypeId.BARRACKS).not_ready.amount)
        )
        
        # We want 2 ebays once we have a 3rd CC and 3 raxes (by this time we probably already have a Starport and such)
        return (
            self.amount < 2
            and self.bot.townhalls.amount >= 3
            and barracks_count >= 3
        )
    
    @property
    @override
    def position(self) -> Point2:
        expansion: Expansion = (
            self.bot.expansions.main
            if self.bot.expansions.main.is_taken
            else self.bot.expansions.taken.random
        )
        if (not expansion):
            return self.bot.expansions.main.position
        base_ressources: Units = expansion.mineral_fields + expansion.vespene_geysers
        return position_behind_worker_line(base_ressources, expansion.position, random=True)