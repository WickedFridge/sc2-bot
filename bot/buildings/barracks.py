from typing import List, override
from bot.buildings.building import Building
from bot.macro.expansion_manager import Expansions
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

class Barracks(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKS
        self.name = "Barracks"

    def _barracks_info(self) -> tuple[int, int, int]:
        barracks_pending_amount: float = max(
            self.bot.structures(UnitTypeId.BARRACKS).not_ready.amount,
            self.bot.already_pending(UnitTypeId.BARRACKS)
        )
        barracks_amount: float = (
            self.bot.structures(UnitTypeId.BARRACKS).ready.amount +
            barracks_pending_amount +
            self.bot.structures(UnitTypeId.BARRACKSFLYING).ready.amount
        )
        base_amount: int = self.bot.townhalls.amount
        return barracks_pending_amount, barracks_amount, base_amount

    @property
    def max_barracks(self) -> int:
        """
        We want 1 rax for 1 base, 2 raxes for 2 bases, 3 raxes for 3 bases, 5 raxes for 4 bases, 8 raxes for 5 bases, then 12
        with a max of 12 raxes
        """
        _, _, base_amount = self._barracks_info()
        rax_amount: List[int] = [1, 2, 3, 5, 8, 12]
        if (base_amount > len(rax_amount) - 1):
            return max(rax_amount)
        return rax_amount[base_amount - 1]
    
    @override
    @property
    def conditions(self) -> bool:
        townhall_amount: int = self.bot.townhalls.ready.amount
        barracks_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracks_pending, barracks_total, base_amount = self._barracks_info()

        return (
            townhall_amount >= 1
            and barracks_tech_requirement == 1
            and barracks_pending < base_amount
            and barracks_total < self.max_barracks
        )
    
    @override
    @property
    def position(self) -> Point2:
        _, barracks_total, _ = self._barracks_info()
        if (barracks_total == 0):
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