from typing import List, override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.point2_functions.utils import center
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


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
            self.precarious
            and self.bot.expansions.taken.amount < 3
        ):
            expansions.add(self.bot.expansions.main)

        return expansions.filter(
            lambda expansion: (
                self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).amount == 0
                or self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).closest_distance_to(expansion.position) > 12
            )
        )
    
    @override
    @property
    def custom_conditions(self) -> bool:    
        bunker_tech_requirements: float = self.bot.tech_requirement_progress(UnitTypeId.BUNKER)
        reaper_amount: int = self.bot.units(UnitTypeId.REAPER).amount + self.bot.already_pending(UnitTypeId.REAPER)
        marine_amount: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        defense_count: float = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready.amount + max(
            self.bot.already_pending(UnitTypeId.BUNKER),
            self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        )
        bunker_to_construct_amount: int = self.bot.already_pending(UnitTypeId.BUNKER) - self.bot.structures(UnitTypeId.BUNKER).not_ready.amount
        expansions_count: int = self.bot.expansions.amount_taken
        bunker_amount_target: int = expansions_count - 1
        useless_bunker_count: int = (
            0 if expansions_count == 0
            else self.bot.structures(UnitTypeId.BUNKER).filter(
                lambda bunker: self.bot.expansions.taken.closest_to(bunker).position.distance_to(bunker) > 10
            ).amount
        )
        
        # place a bunker in the main if we're under attack on b2
        ramp_bunkers: Units = self.bot.structures(UnitTypeId.BUNKER).filter(lambda bunker: bunker.distance_to(self.bot.main_base_ramp.top_center) < 8)
        if (
            ramp_bunkers.amount >= 1 or (
                self.precarious and self.bot.expansions.taken.amount < 3
            )
        ):
            bunker_amount_target += 1

        # We want a bunker at each base after the first
        return (
            bunker_tech_requirements == 1
            and (reaper_amount >= 1 or marine_amount >= 2)
            and (
                self.expansions_without_defense.amount >= 1
                or self.precarious
            )
            and defense_count < bunker_amount_target - useless_bunker_count
            and bunker_to_construct_amount == 0
        )
    
    @override
    @property
    def position(self) -> Point2:
        expansion_not_defended: Expansion = self.expansions_without_defense.first
        return expansion_not_defended.bunker_position