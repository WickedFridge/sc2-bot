from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Marauder(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARAUDER
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marauder'
        self.order_id = AbilityId.BARRACKSTRAIN_MARAUDER
    
    @property
    def custom_conditions(self) -> bool:
        marine_count: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        return (marine_count >= 8 or self.bot.composition_manager.marauders_ratio > 0.3)

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