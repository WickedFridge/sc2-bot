from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Raven(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.RAVEN
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Raven'
        self.order_id = AbilityId.STARPORTTRAIN_RAVEN
        self.requires_techlab = True
        self.requeue_progress = 0.98
