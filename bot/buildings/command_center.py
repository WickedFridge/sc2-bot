from typing import List, override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
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
        self.radius = 2

    @override
    @property
    def override_conditions(self) -> bool:
        base_count: int = self.bot.expansions.amount
        townhalls_count: int = self.bot.townhalls.amount
        pending_cc_count: int = self.bot.already_pending(UnitTypeId.COMMANDCENTER)
        max_pending_cc_count: int = 2

        return (
            townhalls_count <= base_count + 3
            and pending_cc_count < max_pending_cc_count
            and self.bot.minerals >= 600
        )
    
    @override
    @property
    def custom_conditions(self) -> bool:
        base_count: int = self.bot.expansions.amount
        townhalls_count: int = self.bot.townhalls.amount
        pending_cc_count: int = self.bot.already_pending(UnitTypeId.COMMANDCENTER)
        max_pending_cc_count: int = 2

        match(townhalls_count):
            # build order handles that
            case 0 | 1 | 2:
                return True
            case _:
                return (
                    townhalls_count <= base_count + 3 and
                    pending_cc_count < max_pending_cc_count
                )

    @override
    @property
    def position(self) -> Point2:
        townhall_amount: int = self.bot.townhalls.amount
        cc_position: Point2 = self.bot.expansions.next.position
        next_expansion: Expansion = self.bot.expansions.next
        near_cc_position: Point2 = self.bot.expansions.main.position.towards(cc_position, 2)
        in_base_builds: List[BuildOrderName] = [
            BuildOrderName.DEFENSIVE_TWO_RAX.value,
            BuildOrderName.CONSERVATIVE_EXPAND.value,
            BuildOrderName.DEFENSIVE_CYCLONE.value
        ]
        match (townhall_amount):
            case 0:
                return self.bot.expansions.main.position
            case 1:
                if (
                    self.bot.build_order.build.name in in_base_builds
                    or not next_expansion.is_safe
                ):
                    return near_cc_position
                return next_expansion.position
            case 2:
                return near_cc_position
            case _:
                return self.bot.expansions.taken.safe.closest_to(cc_position).position.towards(cc_position, 2)
            
    
    async def move_worker_expand(self):
        # move SCV for first expand
        if (self.bot.time >= 100 or self.bot.townhalls.amount >= 2):
            return
        if (self.bot.build_order.build.name == BuildOrderName.KOKA_BUILD.value):
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
        elif (self.bot.build_order.build.name == BuildOrderName.CC_FIRST_TWO_RAX.value):
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