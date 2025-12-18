from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.strategy.strategy_types import Situation
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.point2_functions.utils import center
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class Bunker(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BUNKER
        self.name = "Bunker"
        self.ignore_build_order = True

    @property
    def expansions_without_defense(self) -> Expansions:
        expansions: Expansions = self.bot.expansions.taken.without_main
        
        # build a bunker in the main if we're getting proxy'd
        if (
            self.bot.scouting.situation in [
                Situation.PROXY_BUILDINGS,
                Situation.UNDER_ATTACK
            ]
            and self.bot.expansions.taken.amount < 3
        ):
            expansions.add(self.bot.expansions.main)

        return expansions.filter(
            lambda expansion: (
                self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).amount == 0
                or self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).closest_distance_to(expansion.position) > 12
            )
        )
    
    @property
    def wall_position(self) -> Point2:
        prefered_position: Point2 = self.bot.main_base_ramp.top_center
        return dfs_in_pathing(self.bot, prefered_position, radius=1)
    
    @override
    @property
    def custom_conditions(self) -> bool:    
        bunker_tech_requirements: float = self.bot.tech_requirement_progress(UnitTypeId.BUNKER)
        defense_count: float = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready.amount + max(
            self.bot.already_pending(UnitTypeId.BUNKER),
            self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        )
        bunker_to_construct_amount: int = self.bot.already_pending(UnitTypeId.BUNKER) - self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        expansions_count: int = self.bot.expansions.amount_taken
        bunker_amount_target: int = expansions_count - 1
        
        # place a bunker in the main if we're under attack on b2
        situation = self.bot.scouting.situation
        precarious_situation: bool = situation in [Situation.PROXY_BUILDINGS, Situation.UNDER_ATTACK]
        if (precarious_situation and self.bot.expansions.taken.amount < 3):
            bunker_amount_target += 1

        # We want a bunker at each base after the first
        return (
            bunker_tech_requirements == 1
            and self.bot.supply_army >= 1
            and (
                self.expansions_without_defense.amount >= 1
                or precarious_situation
            )
            and defense_count < bunker_amount_target
            and bunker_to_construct_amount == 0
        )
    
    @override
    @property
    def position(self) -> Point2:
        expansion_not_defended: Expansion = self.expansions_without_defense.first
        # return wall if we're talking about the main
        if (expansion_not_defended.position == self.bot.expansions.main.position):
            return self.wall_position
        
        bunker_position: Point2 = (
            expansion_not_defended.bunker_ramp
            if self.bot.matchup == Matchup.TvZ and expansion_not_defended.bunker_ramp is not None
            else expansion_not_defended.bunker_forward_in_pathing
        )
        return bunker_position