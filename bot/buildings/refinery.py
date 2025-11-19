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
            case 0:
                return True
            case 1:
                return True
            
            # case 0:
            #     # build first refinery as soon as we have a barracks and at least 15 SCVs
            #     return (
            #     self.bot.structures(UnitTypeId.BARRACKS).amount > 0
            #     and workers_amount >= 15
            # )

            # case 1:
            #     # build second refinery as soon as we have a factory and at least 21 SCVs
            #     return (
            #         self.bot.structures(UnitTypeId.FACTORY).amount > 0
            #         and self.bot.townhalls.amount >= 2
            #         and workers_amount >= 21
            #     )
            
            case 2:
                # build third rafinery as long as we have 3CCs, 4 rax and at least 40 SCVs  
                return (
                    self.bot.townhalls.amount >= 3
                    and self.bot.structures(UnitTypeId.BARRACKS).amount >= 4
                    and workers_amount >= 38
                )
            
            case 3:
                # build fourth rafinery as long as we have 2 Ebays, a 3rd base takenand at least 50 SCVs
                return (
                    self.bot.structures(UnitTypeId.ENGINEERINGBAY).amount >= 2
                    and self.bot.expansions.amount_taken >= 3
                    and workers_amount >= 50
                )

            # TODO clean this
            case 6:
                return (
                    refinery_amount < max_refineries
                    and refinery_amount <= 2 * self.bot.expansions.amount_taken
                    and workers_amount >= 75
                )

            case _:        
                # TODO: fix refinery count for gas #7 and #8
                return (
                    refinery_amount < max_refineries
                    and refinery_amount <= 2 * self.bot.expansions.amount_taken
                    and workers_amount >= (refinery_amount + 1) * 12.5 + 1
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
        can_build: bool
        resources_updated: Resources
        can_build, resources_updated = resources.update(building_cost)
        if (can_build == False):
            return resources_updated
        
        workers: Units = self.builder.worker_builders
        if (workers.amount):
            worker: Unit = workers.closest_to(self.target_geyser)
            worker.build_gas(self.target_geyser)
            print(f'Build {self.name}')
            self.on_complete()
        return resources_updated