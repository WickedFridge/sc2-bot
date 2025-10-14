from typing import FrozenSet, Set, override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.resources import Resources
from bot.strategy.strategy_types import Situation
from sc2.game_data import Cost
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
    
    @property
    def max_depots_pending(self) -> int:
        """Allow more simultaneous depots as the game progresses."""
        thresholds = [(160, 4), (120, 3), (42, 2)]
        for threshold, value in thresholds:
            if (self.bot.supply_used >= threshold):
                return value
        return 1
    
    
    @override
    @property
    def conditions(self) -> bool:
        current_supply: float = self.bot.supply_cap + self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
        pending_depots: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).not_ready
        for pending_depot in pending_depots:
            current_supply += pending_depot.build_progress * 8
        future_supply: float = current_supply + self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) * 8 + self.bot.already_pending(UnitTypeId.COMMANDCENTER) * 15
        concurrent_supply_depots: int = self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
        
        if (future_supply >= 200 or concurrent_supply_depots >= self.max_depots_pending):
            return False
        
        if (current_supply <= 15):
            return self.bot.supply_used >= 14
        if (current_supply <= 23):
            return self.bot.supply_used >= 21 or self.bot.scouting.situation == Situation.UNDER_ATTACK
        if (current_supply <= 46):
            return self.bot.supply_used >= 35 and self.bot.supply_workers >= 26
        if (current_supply <= 54):
            return self.bot.supply_used >= 42 and self.bot.supply_workers >= 30
        return (
            self.bot.supply_left < self.bot.supply_used / 6
        )
    
    @override
    @property
    def position(self) -> Point2:
        depots: Units = self.bot.structures([UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED])

        # Filter locations close to finished supply depots
        
        if (depots.amount == 0):
            return self.bot.map.wall_placement[0]
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
        # move SCV for first depot
        workers_mining: Units = self.bot.workers.filter(
            lambda worker: worker.is_collecting or len(worker.orders) == 2 and worker.orders[1] == AbilityId.HARVEST_GATHER_SCV
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
            builder.hold_position(True)