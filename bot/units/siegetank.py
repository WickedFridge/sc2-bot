from typing import override

from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class SiegeTank(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.SIEGETANK
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Siege Tank'
        self.order_id = AbilityId.FACTORYTRAIN_SIEGETANK
        self.requires_techlab = True

    @property
    @override
    def custom_conditions(self):
        return not self.bot.composition_manager.should_train(UnitTypeId.THOR)