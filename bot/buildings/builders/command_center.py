from typing import List, override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.strategy.build_order.bo_names import BuildOrderName
from bot.utils.matchup import Matchup
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class CommandCenter(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.COMMANDCENTER
        self.name = "Command Center"
        self.radius = 2.5

    @property
    def max_pending(self) -> int:
        max: int = 2
        if (self.bot.minerals >= 800):
            max += 1
        if (self.bot.minerals >= 1200):
            max += 1
        return max;
    
    @property
    @override
    def override_conditions(self) -> bool:
        return (
            self.custom_conditions 
            and self.bot.minerals >= 600
        )
    
    @property
    @override
    def custom_conditions(self) -> bool:
        base_count: int = self.bot.expansions.amount
        townhall_amount: int = self.bot.townhalls.amount

        match(townhall_amount):
            # build order handles that
            case 0 | 1 | 2:
                return True
            case _:
                return (
                    townhall_amount <= base_count + 3 and
                    self.pending_amount < self.max_pending
                )

    @property
    @override
    def position(self) -> Point2:
        townhall_amount: int = self.bot.townhalls.amount
        cc_position: Point2 = self.bot.expansions.next.position
        next_expansion: Expansion = self.bot.expansions.next
        near_cc_position: Point2 = self.bot.expansions.main.position.towards(cc_position, 2)
        safe_expansions: Expansions = self.bot.expansions.taken.safe
        
        # calculate the optimal worker count based on mineral field left in bases
        optimal_worker_count: float = (
            sum(expansion.optimal_mineral_workers for expansion in self.bot.expansions.taken)
            + sum(expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken)
        )
        current_worker_count: float = (
            sum(expansion.mineral_worker_count for expansion in self.bot.expansions.taken)
            + sum(expansion.vespene_worker_count for expansion in self.bot.expansions.taken)
        )
        are_bases_saturated: bool = current_worker_count >= optimal_worker_count - 5

        match (townhall_amount):
            case 0:
                return self.bot.expansions.main.position
            case 1:
                if (
                    self.bot.build_order.build.in_base_cc
                    or not next_expansion.is_safe
                ):
                    return near_cc_position
                return next_expansion.position
            case 2:
                return near_cc_position
            case _:
                if (safe_expansions.amount >= 1):
                    if (are_bases_saturated):
                        return self.bot.expansions.taken.safe.closest_to(cc_position).position.towards(cc_position, 2)
                    return self.bot.expansions.taken.safe.random.position.towards(cc_position, 2)
                return self.bot.expansions.main.position
    
    async def move_worker_expand(self):
        # move SCV for first expand
        if (self.bot.time >= 100 or self.bot.townhalls.amount >= 2):
            return
        reaper_expand_builds: List[BuildOrderName] = [
            BuildOrderName.KOKA_BUILD,
            BuildOrderName.MACRO_CYCLONE,
            BuildOrderName.GREEDY_2_2_TIMING,
            BuildOrderName.BANSHEESEBURGER,
            BuildOrderName.CYCLONE_3_RAVEN,
        ]
        if (self.bot.build_order.build.name in reaper_expand_builds):
            rax_builder: Units = self.bot.workers.filter(
                lambda unit: (
                    len(unit.orders) == 1
                    and unit.orders[0].ability.id == AbilityId.TERRANBUILD_BARRACKS
                )
            )
            if (rax_builder.amount == 0):
                return
            print("queue gather command for expand")
            mineral_field: Unit = self.bot.expansions.b2.mineral_fields.random
            rax_builder.first.gather(mineral_field, True)
        elif (self.bot.build_order.build.name == BuildOrderName.CC_FIRST_TWO_RAX):
            b2: Point2 = self.bot.expansions.b2.position
            supply_builder: Units = self.bot.workers.filter(
                lambda unit: (
                    len(unit.orders) == 1
                    and unit.orders[0].ability.id == AbilityId.TERRANBUILD_SUPPLYDEPOT
                )
            )
            if (supply_builder.amount == 0):
                return
            print("queue gather command for expand")
            mineral_field: Unit = self.bot.expansions.b2.mineral_fields.random
            supply_builder.first.gather(mineral_field, True)
            supply_builder.first.move(b2, True)
            supply_builder.first.patrol(b2.towards(self.bot.expansions.main.position), True)