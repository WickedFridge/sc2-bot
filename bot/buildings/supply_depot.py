import math
from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.strategy.strategy_types import Situation
from sc2.ids.ability_id import AbilityId
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
        self.ignore_build_order = True
    
    @override
    @property
    def force_position(self) -> bool:
        return self.bot.structures(UnitTypeId.SUPPLYDEPOT).amount < 2
    
    @property
    def max_depots_pending(self) -> int:
        """Allow more simultaneous depots as the game progresses."""
        thresholds = [(80, 4), (60, 3), (30, 2)]
        for threshold, value in thresholds:
            if (self.bot.supply_workers >= threshold):
                return value
        excess_supply: int = self.bot.supply_used - self.bot.supply_cap
        if (excess_supply <= 0):
            return 1
        return 2 + math.floor(excess_supply / 8)
    
    
    @override
    @property
    def custom_conditions(self) -> bool:
        SUPPLY_DEPOT: int = 8
        SUPPLY_CC: int = 15
        MAX_SUPPLY: int = 200

        concurrent_supply_depots: int = self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
        concurrent_cc: int = self.bot.already_pending(UnitTypeId.COMMANDCENTER)
        
        current_supply: float = self.bot.supply_cap
        pending_depots: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).not_ready
        pending_ccs: Units = self.bot.structures(UnitTypeId.COMMANDCENTER).not_ready
        
        for pending_depot in pending_depots:
            current_supply += SUPPLY_DEPOT / 2
            if (pending_depot.build_progress >= 0.5):
                current_supply += pending_depot.build_progress * SUPPLY_DEPOT / 2
        for pending_cc in pending_ccs:
            if (pending_cc.build_progress >= 0.75):
                current_supply += pending_cc.build_progress * SUPPLY_CC

        
        future_supply: float = (
            current_supply
            + concurrent_supply_depots * SUPPLY_DEPOT
            + concurrent_cc * SUPPLY_CC
        )
        concurrent_supply_depots: int = self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
        
        if (future_supply >= MAX_SUPPLY or concurrent_supply_depots >= self.max_depots_pending):
            return False
        
        if (current_supply <= 15):
            return self.bot.supply_used >= 14
        if (current_supply <= 23):
            # 21 if 1 rax, 20 if 2 rax
            return (
                self.bot.scouting.situation.is_precarious
                or self.bot.supply_used >= 22 - self.bot.structures(UnitTypeId.BARRACKS).amount
            )
        
        # y = 2.5 + 0.22x + sqrt(0.5x)
        supply_threshold: float = 2.5 + 0.22 * self.bot.supply_workers + math.sqrt(0.5 * self.bot.supply_workers)
        return current_supply - self.bot.supply_used < supply_threshold
    
    @override
    @property
    def position(self) -> Point2:
        depots: Units = self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED])
        possible_supply_positions: list[Point2] = [
            self.bot.map.wall_placement[0],
            self.bot.map.wall_placement[2],
        ]

        # choose between the two wall supply positions depending on how far enemy units are from it
        if (depots.amount == 0):
            if (self.bot.enemy_units.amount == 0):
                return self.bot.map.wall_placement[0]
            
            highest_distance: float = 0
            best_position: Point2 = possible_supply_positions[0]
            for pos in possible_supply_positions:
                distance: float = self.bot.enemy_units.closest_distance_to(pos)
                if (distance > highest_distance):
                    highest_distance = distance
                    best_position: Point2 = pos
            return best_position

        if (depots.amount == 1):
            return self.bot.map.wall_placement[2] if depots.first.position == self.bot.map.wall_placement[0] else self.bot.map.wall_placement[0]
        
        expansion: Expansion = self.bot.expansions.taken.random
        if (not expansion):
            return self.bot.expansions.main.position
        units_pool: Units = expansion.mineral_fields + expansion.vespene_geysers
        selected_position: Point2 = units_pool.random.position if units_pool.amount >= 1 else expansion.position
        offset: Point2 = selected_position.negative_offset(expansion.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, 2)
    
    async def move_worker_first(self):
        if (self.bot.time >= 60):
            return
        
        # move SCV for first depot
        workers_mining: Units = self.bot.workers.filter(
            lambda worker: (
                worker.is_collecting
                or (
                    len(worker.orders) == 2
                    and worker.orders[1] == AbilityId.HARVEST_GATHER_SCV
                )
            )
        )
        if (
            self.bot.supply_used == 13
            and workers_mining.amount == 12
            and self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready.amount == 0
            and self.bot.minerals >= 65
        ):
            print("move worker for first depot")
            depot_position: Point2 = self.bot.main_base_ramp.depot_in_middle.position
            builder: Unit = workers_mining.filter(lambda unit: not unit.is_carrying_resource).closest_to(depot_position)
            builder.move(depot_position)
            builder.patrol(self.bot.map.wall_placement[0], True)