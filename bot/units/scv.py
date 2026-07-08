import math
from typing import List, override
from bot.strategy.strategy_types import Situation
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
        absolute_maximal_amount: int = 84
        townhalls: Units = self.bot.townhalls
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).ready.amount

        current_mining: float = sum(
            expansion.optimal_mineral_workers + expansion.optimal_vespene_workers for expansion in self.bot.expansions.taken
        )

        optimal_amount: float = current_mining
        if (townhalls.amount > self.bot.expansions.taken.amount):
            optimal_amount += 8

        maximal_amount: float = absolute_maximal_amount * (1 - 1 / (3.5 + 400 * math.exp(-orbital_count))) + 1 - 1.1 * orbital_count

        return max(minimal_amount, min([
            absolute_maximal_amount,
            round(maximal_amount),
            round(optimal_amount),
        ]))
    
    @property
    @override
    def custom_conditions(self) -> bool:
        return self.scv_amount < self.max_amount
    
    @property
    @override
    def building_group(self) -> Units:
        townhalls_type: List[UnitTypeId] = [
            UnitTypeId.PLANETARYFORTRESS,
            UnitTypeId.ORBITALCOMMAND
        ]
        if (
            not self.bot.orbital_tech_available
            or self.bot.scouting.situation in [
                Situation.CHEESE_WORKER_RUSH,
                Situation.CHEESE_CANNON_RUSH
            ]
        ):
            townhalls_type.append(UnitTypeId.COMMANDCENTER)

        return self.bot.townhalls(townhalls_type).ready.filter(
            lambda unit: (
                len(unit.orders) == 0
                or (
                    len(unit.orders) == 1
                    and unit.orders[0].ability.id == AbilityId.COMMANDCENTERTRAIN_SCV
                    and unit.orders[0].progress >= 0.95
                )
                or (
                    unit.type_id == UnitTypeId.PLANETARYFORTRESS
                    and unit.is_attacking
                    and (
                        len(unit.orders) == 1
                        or (
                            len(unit.orders) == 2
                            and unit.orders[0].ability.id == AbilityId.COMMANDCENTERTRAIN_SCV
                            and unit.orders[0].progress >= 0.95
                        )
                    )
                )
            )
        )
    
    @override
    def log(self, i: int) -> None:
        print(f'Train {self.name} [{self.scv_amount + i}/{self.max_amount}]')