from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.utils.matchup import Matchup
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class Bunker(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BUNKER
        self.name = "Bunker"

    @property
    def expansions_without_defense(self) -> Expansions:
        return self.bot.expansions.taken.without_main.filter(
            lambda expansion: (
                self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).amount == 0
                or self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).closest_distance_to(expansion.position) > 12
            )
        )
    
    @override
    @property
    def conditions(self) -> bool:    
        bunker_tech_requirements: float = self.bot.tech_requirement_progress(UnitTypeId.BUNKER)
        defense_count: float = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready.amount + max(
            self.bot.already_pending(UnitTypeId.BUNKER),
            self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        )
        expansions_count: int = self.bot.expansions.amount_taken

        # We want a bunker at each base after the first
        return (
            bunker_tech_requirements == 1
            and self.bot.supply_army >= 1
            and self.expansions_without_defense.amount >= 1
            and defense_count < expansions_count - 1
        )
    
    @override
    @property
    def position(self) -> Point2:
        expansion_not_defended: Expansion = self.expansions_without_defense.first
        bunker_position: Point2 = (
            expansion_not_defended.bunker_ramp
            if self.bot.matchup == Matchup.TvZ and expansion_not_defended.bunker_ramp is not None
            else expansion_not_defended.bunker_forward_in_pathing
        )
        return bunker_position