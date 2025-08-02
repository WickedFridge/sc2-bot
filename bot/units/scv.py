from typing import override
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

    @property
    def scv_amount(self) -> float:
        workers_pending: float = self.bot.already_pending(self.unitId) + self.i
        return self.bot.supply_workers + workers_pending
    
    @property
    def max_amount(self) -> int:
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount
        return min([84, 100 - 4 * orbital_count, self.bot.expansions.amount_taken * 22])
    
    @override
    @property
    def custom_conditions(self) -> bool:
        return self.scv_amount < self.max_amount
    
    @override
    @property
    def building_group(self) -> Units:
        townhalls_type: UnitTypeId = (
            UnitTypeId.ORBITALCOMMAND if self.bot.orbital_tech_available
            else UnitTypeId.COMMANDCENTER
        )
        return self.bot.townhalls(townhalls_type).ready.filter(
            lambda unit: (
                unit.is_idle
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