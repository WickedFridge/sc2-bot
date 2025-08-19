from typing import List, override
from bot.units.train import Train
from bot.utils.unit_supply import units_supply
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Medivac(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MEDIVAC
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Medivac'

    @property
    def medivac_amount(self) -> float:
        medivac_pending: float = self.bot.already_pending(self.unitId)
        return self.bot.units(UnitTypeId.MEDIVAC).amount + medivac_pending

    @property
    def max_amount(self) -> int:
        return 10

    @override
    @property
    def custom_conditions(self) -> bool:
        bio_unit_ids: List[UnitTypeId] = [
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.GHOST
        ]
        bio_supply: int = units_supply(self.bot.units(bio_unit_ids))
        barracks_inactive: Units = self.bot.structures(UnitTypeId.BARRACKS).ready.filter(lambda rax: not rax.is_active)

        return (
            self.medivac_amount < self.max_amount
            and (
                bio_supply >= 10
                or barracks_inactive.amount == 0
            )
        )
    
    @override
    @property
    def building_group(self) -> Units:
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        return starports.filter(
            lambda unit: (
                unit.is_idle
                or (
                    unit.has_reactor
                    and len(unit.orders) < 2
                )
            )
        )