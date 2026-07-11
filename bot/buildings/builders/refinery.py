import math
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion_manager import Expansions
from bot.macro.resources import Resources
from bot.strategy.strategy_types import Situation
from bot.utils.ability_tags import AbilityBuild
from bot.utils.matchup import Matchup
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class Refinery(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.REFINERY
        self.name = "Refinery"

    @property
    @override
    def custom_conditions(self) -> bool:
        if (self.target_geyser is None):
            return False
        if (self.bot.scouting.situation in [Situation.CHEESE_WORKER_RUSH, Situation.CHEESE_CANNON_RUSH]):
            return False
        if (self.unitId in self.bot.build_order.build.pending_ids):
            return True
        depleted_refineries: int = self.bot.structures(self.unitId).filter(
            lambda unit: self.bot.vespene_geyser.closest_to(unit).has_vespene == False
        ).amount
        refinery_amount: int = self.amount - depleted_refineries

        max_refineries: int = 10
        orbital_amount: float = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        scv_amount: int = self.bot.supply_workers
        
        match(refinery_amount):
            # Build order handles first 2 gas
            case 0 | 1:
                return True
            
            case 2:
                # build third rafinery as long as we have 3CCs and at least 38 SCVs (50 including mules)
                return (
                    self.bot.townhalls.amount >= 3
                    and scv_amount >= 38
                )
            
            case 3:
                # build fourth rafinery as long as we have 2 Ebays, a 3rd orbital and at least 50 SCVs (72 including mules)
                return (
                    self.bot.structures(UnitTypeId.ENGINEERINGBAY).amount >= 2
                    and orbital_amount >= 3
                    and scv_amount >= 50
                )

            case _:
                if (
                    refinery_amount >= max_refineries
                    or refinery_amount >= 2 * self.bot.expansions.amount_taken
                    or (self.bot.vespene > 300 and self.bot.minerals < 600)
                ):
                    return False
                
                if (self.bot.minerals >= 50 * refinery_amount):
                    return True
                
                # we want at least 4 orbitals for gaz 7, 5 for gaz 8 and 6 for gaz 9
                if (refinery_amount - orbital_amount > 2):
                    return False
                
                # more scan usage in TvZ
                if (self.bot.matchup == Matchup.TvZ):
                    orbital_amount *= 0.5
                
                # formula to calculate this, see DESMOS
                return scv_amount >= 26 * math.sqrt(refinery_amount) + (3 - orbital_amount) * refinery_amount * 0.6
    
    @property
    def target_geyser(self) -> Unit | None:
        for expansion in self.bot.expansions.taken:
            if (expansion.refineries.amount <= 2):
                free_geyser: Units = expansion.vespene_geysers.filter(
                    lambda geyser: (
                        geyser.has_vespene
                        and self.bot.structures(UnitTypeId.REFINERY).closer_than(1, geyser).amount == 0
                        and self.bot.enemy_structures.of_type({UnitTypeId.REFINERY, UnitTypeId.EXTRACTOR, UnitTypeId.ASSIMILATOR}).closer_than(1, geyser).amount == 0
                    )
                )
                if (free_geyser.amount >= 1):
                    return free_geyser.first
        return None

    async def build(self, resources: Resources) -> Resources:
        if (not self.conditions):
            return resources
        
        building_cost: Cost = self.bot.calculate_cost(self.unitId)
        enough_resources: bool
        resources_updated: Resources
        enough_resources, resources_updated = resources.update(building_cost)
        if (enough_resources == False):
            return resources_updated
        
        workers: Units = self.builder.worker_builders
        if (workers.amount):
            worker: Unit = workers.closest_to(self.target_geyser)
            worker.build_gas(self.target_geyser)
            self.on_complete()
        return resources_updated