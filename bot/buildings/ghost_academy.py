from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.utils.matchup import Matchup
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.units import Units


class GhostAcademy(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.GHOSTACADEMY
        self.name = "Ghost Academy"

    @override
    @property
    def conditions(self) -> bool:
        ghost_academy_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.GHOSTACADEMY)
        upgrades_tech_requirement: float = self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYARMORSLEVEL2)
        ghost_academy_count: int = self.bot.structures(UnitTypeId.GHOSTACADEMY).ready.amount + self.bot.already_pending(UnitTypeId.GHOSTACADEMY)
        supply_min: int = 140 if self.bot.matchup == Matchup.TvP else 120

        # We want a ghost academy once we have at least 4 bases and 2/2 started
        # but no ghost in TvT
        return (
            ghost_academy_tech_requirement == 1
            and upgrades_tech_requirement > 0
            and self.bot.expansions.taken.amount >= 4
            and ghost_academy_count == 0
            and self.bot.supply_used >= supply_min
            and self.bot.matchup != Matchup.TvT
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