from typing import override
from bot.buildings.building import Building
from bot.macro.expansion_manager import Expansions
from bot.macro.resources import Resources
from bot.utils.ability_tags import AbilityBuild
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

    @override
    @property
    def custom_conditions(self) -> bool:
        if (self.target_geyser is None):
            return False
        refinery_amount: int = self.bot.structures(UnitTypeId.REFINERY).ready.filter(
            lambda refinery: self.bot.expansions.taken.vespene_geysers.closest_to(refinery.position).has_vespene
        ).amount + self.bot.already_pending(UnitTypeId.REFINERY)

        max_refineries: int = 8
        workers_amount: int = self.bot.supply_workers
        
        match(refinery_amount):
            # Build order handles first 2 gas
            case 0 | 1:
                return True
            
            case 2:
                # build third rafinery as long as we have 3CCs and at least 40 SCVs  
                return (
                    self.bot.townhalls.amount >= 3
                    and workers_amount >= 38
                )
            
            case 3:
                # build fourth rafinery as long as we have 2 Ebays, a 3rd base takenand at least 50 SCVs
                return (
                    self.bot.structures(UnitTypeId.ENGINEERINGBAY).amount >= 2
                    and self.bot.expansions.amount_taken >= 3
                    and workers_amount >= 50
                )

            case 4 | 5:        
                return (
                    refinery_amount < max_refineries
                    and refinery_amount <= 2 * self.bot.expansions.amount_taken
                    and workers_amount >= (refinery_amount + 1) * 12.5 + 1
                )

            # TODO clean this
            case _:
                return (
                    refinery_amount < max_refineries
                    and refinery_amount <= 2 * self.bot.expansions.amount_taken
                    and workers_amount >= 75
                )    
    
    
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