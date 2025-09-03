from typing import override
from bot.units.train import Train
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Viking(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.VIKINGFIGHTER
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Viking'

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