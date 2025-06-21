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
            # and self.bot.supply_left < self.bot.supply_used / 10
            and self.bot.supply_left < (self.bot.supply_used - 3) / 9
            # and concurrent_supplies <= self.bot.supply_used / 70
            and concurrent_supplies <= (self.bot.supply_used - 5) / 50
        )
    
    @override
    @property
    def position(self) -> Point2:
        depots: Units = self.bot.structures.of_type({UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED})

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
        workers_mining: int = self.bot.workers.collecting.amount
        if (
            self.bot.supply_used == 13
            and workers_mining == self.bot.supply_used
            and self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready.amount == 0
            and self.bot.minerals >= 60
        ):
            print("move worker for first depot")
            self.bot.workers.random.move(self.bot.main_base_ramp.depot_in_middle)