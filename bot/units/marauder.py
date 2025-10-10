from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.units import Units


class Marauder(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARAUDER
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marauder'
        self.order_id = AbilityId.BARRACKSTRAIN_MARAUDER

    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda rax: (
                rax.has_techlab
                and (
                    len(rax.orders) == 0
                    or (
                        len(rax.orders) == 1
                        and rax.orders[0].progress >= 0.98
                    )
                )
            )
        )