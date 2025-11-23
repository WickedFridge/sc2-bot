from typing import List, override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Scv(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.SCV
        self.buildingId = [
            UnitTypeId.COMMANDCENTER,
            UnitTypeId.ORBITALCOMMAND,
            UnitTypeId.PLANETARYFORTRESS,
        ]
        self.name = 'SCV'
        self.order_id = AbilityId.COMMANDCENTERTRAIN_SCV

    @property
    def scv_amount(self) -> float:
        workers_pending: float = self.bot.already_pending(self.unitId) + self.i
        return self.bot.supply_workers + workers_pending
    
    @property
    def max_amount(self) -> int:
        minimal_amount: int = 24
        maximal_amount: int = 84
        townhalls: Units = self.bot.townhalls
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        return max(minimal_amount, min([
            maximal_amount, 100 - 4 * orbital_count,
            townhalls.ready.amount * 22 + townhalls.not_ready.amount * 11,
        ]))
    
    @override
    @property
    def custom_conditions(self) -> bool:
        return self.scv_amount < self.max_amount
    
    @override
    @property
    def building_group(self) -> Units:
        townhalls_type: List[UnitTypeId] = (
            [
                UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.ORBITALCOMMAND if self.bot.orbital_tech_available
                else UnitTypeId.COMMANDCENTER
            ]
        )
        return self.bot.townhalls(townhalls_type).ready.filter(
            lambda unit: (
                len(unit.orders) == 0
                or (
                    len(unit.orders) == 1
                    and unit.orders[0].ability.id == AbilityId.COMMANDCENTERTRAIN_SCV
                    and unit.orders[0].progress >= 0.95
                )
            )
        )
    
    @override
    def log(self, i: int) -> None:
        print(f'Train {self.name} [{self.scv_amount + i}/{self.max_amount}]')