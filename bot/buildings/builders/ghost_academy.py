from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.utils import position_behind_worker_line
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.units import Units


class GhostAcademy(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.GHOSTACADEMY
        self.name = "Ghost Academy"

    @property
    @override
    def custom_conditions(self) -> bool:
        upgrades_tech_requirement: float = self.bot.already_pending_upgrade(UpgradeId.TERRANINFANTRYARMORSLEVEL2)
        supply_min: int = 120
        supply_max: int = 160
        gas_threshold: int = 800

        # We want a ghost academy once we have at least 4 bases and 2/2 started
        # but no ghost in TvT
        return (
            self.amount == 0
            and self.bot.matchup != Matchup.TvT
            and self.bot.supply_used >= supply_min
            and (
                (
                    self.bot.expansions.taken.amount >= 4
                    and upgrades_tech_requirement > 0
                )
                or self.bot.vespene >= gas_threshold
                or self.bot.supply_used >= supply_max
            )
        )
    
    @property
    @override
    def position(self) -> Point2:
        expansion: Expansion = self.bot.expansions.taken.random
        if (not expansion):
            return self.bot.expansions.main.position
        base_ressources: Units = expansion.mineral_fields + expansion.vespene_geysers
        return position_behind_worker_line(base_ressources, expansion.position, random=True)
