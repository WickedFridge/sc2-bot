from typing import override

from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Cyclone(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.CYCLONE
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Cyclone'
        self.order_id = AbilityId.TRAIN_CYCLONE

    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(UnitTypeId.FACTORY).ready.filter(
            lambda factory: (
                factory.has_techlab
                and (
                    len(factory.orders) == 0
                    or (
                        len(factory.orders) == 1
                        and factory.orders[0].progress >= 0.98
                    )
                )
            )
        )