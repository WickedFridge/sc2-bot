from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Viking(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.VIKINGFIGHTER
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Viking'
        self.order_id = AbilityId.STARPORTTRAIN_VIKINGFIGHTER
        self.techlab_reserved_for = [UnitTypeId.RAVEN, UnitTypeId.BANSHEE, UnitTypeId.BATTLECRUISER]
        self.requeue_progress = 0.97

    @property
    @override
    def custom_conditions(self) -> bool:
        return self.bot.units([UnitTypeId.MEDIVAC]).amount >= 2
