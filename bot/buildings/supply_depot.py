from typing import FrozenSet, Set, override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

class SupplyDepot(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.SUPPLYDEPOT
        self.name = "Supply Depot"
        self.radius = 0.5
    
    @override
    @property
    def conditions(self) -> bool:
        current_supply: int = self.bot.supply_cap + self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) * 8
        concurrent_supplies: int = self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
        return (
            current_supply < 200
            and self.bot.supply_left < self.bot.supply_used / 10
            and concurrent_supplies <= self.bot.supply_used / 70
        )
    
    @override
    @property
    def position(self) -> Point2:
        supply_placement_positions: FrozenSet[Point2] = self.bot.main_base_ramp.corner_depots
        depots: Units = self.bot.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

        # Filter locations close to finished supply depots
        if (depots):
            supply_placement_positions: Set[Point2] = {
                d
                for d in supply_placement_positions if depots.closest_distance_to(d) > 1
            }
        if (len(supply_placement_positions) >= 1) :
            return supply_placement_positions.pop()
        
        expansion: Expansion = self.expansions.taken.random
        if (not expansion):
            return self.expansions.main.position
        mineral_field: Unit = expansion.mineral_fields.random if expansion.mineral_fields else expansion.position
        selected_position: Point2 = mineral_field.position
        offset: Point2 = selected_position.negative_offset(expansion.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, 2)
    
    async def move_worker_first(self):
        # move SCV for first depot
        workers_mining: int = self.bot.workers.collecting.amount
        if (
            self.bot.supply_used == 13
            and workers_mining == self.bot.supply_used
            and self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready.amount == 0
            and self.bot.minerals.amount >= 60
        ):
            print("move worker for first depot")
            self.bot.workers.random.move(self.bot.main_base_ramp.depot_in_middle)