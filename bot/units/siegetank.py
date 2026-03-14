from typing import override

from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class SiegeTank(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.SIEGETANK
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Siege Tank'
        self.order_id = AbilityId.FACTORYTRAIN_SIEGETANK

    @override
    @property
    def custom_conditions(self):
        return not self.bot.composition_manager.should_train(UnitTypeId.THOR)
    
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