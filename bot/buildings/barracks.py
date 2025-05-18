from typing import override
from bot.buildings.building import Building
from bot.macro.resources import Resources
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit


class Barracks(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.BARRACKS
        self.name = "Barracks"

    def _barracks_info(self) -> tuple[int, int, int]:
        barracks_pending_amount: int = max(
            self.bot.structures(UnitTypeId.BARRACKS).not_ready.amount,
            self.bot.already_pending(UnitTypeId.BARRACKS)
        )
        barracks_amount: int = (
            self.bot.structures(UnitTypeId.BARRACKS).ready.amount +
            barracks_pending_amount +
            self.bot.structures(UnitTypeId.BARRACKSFLYING).ready.amount
        )
        base_amount: int = self.bot.townhalls.amount
        return barracks_pending_amount, barracks_amount, base_amount

    @override
    @property
    def conditions(self) -> bool:
        barracks_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.BARRACKS)
        barracks_pending, barracks_total, base_amount = self._barracks_info()
        max_barracks: int = min(14, base_amount ** 2 / 2 - base_amount / 2 + 1)

        # We want 1 rax for 1 base, 2 raxes for 2 bases, 4 raxes for 3 bases, 7 raxes for 4 bases
        # y = x²/2 - x/2 + 1 where x is the number of bases and y the number of raxes
        # with a max of 12 raxes

        return (
            barracks_tech_requirement == 1
            and barracks_pending < base_amount
            and barracks_total < max_barracks
        )
    
    @override
    @property
    def position(self) -> Point2:
        _, barracks_total, _ = self._barracks_info()
        if (barracks_total == 0):
            return self.bot.main_base_ramp.barracks_correct_placement
        
        cc: Unit =  self.bot.townhalls.ready.random if self.bot.townhalls.ready.amount >= 1 else self.bot.townhalls.random
        return cc.position.towards(self.bot.game_info.map_center, 4)