from typing import List, override
from bot.buildings.building import Building
from bot.macro.expansion_manager import Expansions
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

class Barracks(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKS
        self.unitIdFlying = UnitTypeId.BARRACKSFLYING
        self.name = "Barracks"

    @override
    @property
    def force_position(self) -> bool:
        return self.bot.structures(UnitTypeId.BARRACKS).amount == 0

    @property
    def max_barracks(self) -> int:
        rax_amount: List[int] = [1, 2, 4, 6, 8, 10, 12]
        if (self.base_amount > len(rax_amount) - 1):
            return max(rax_amount)
        return rax_amount[self.base_amount - 1]
    
    @override
    @property
    def custom_conditions(self) -> bool:
        townhall_amount: int = self.bot.townhalls.ready.amount

        if (self.bot.build_order.build.is_completed):
            return (
                townhall_amount >= 1
                and self.pending_amount < self.base_amount
                and self.amount < self.max_barracks
            )    

        return (
            townhall_amount >= 1
        )
    
    @override
    @property
    def position(self) -> Point2:
        if (self.amount == 0):
            return self.bot.main_base_ramp.barracks_correct_placement
        
        # select only expansions that have less than 5 raxes around them
        expansions: Expansions = self.bot.expansions.ready.filter(
            lambda expansion: (
                self.bot.structures(UnitTypeId.BARRACKS).closer_than(5, expansion.position).amount < 5
            )
        )
        if (expansions.amount >= 1):    
            return expansions.random.position.towards(self.bot.game_info.map_center, 4)
        return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 8)