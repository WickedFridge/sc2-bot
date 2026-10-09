from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Thor(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.THOR
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Thor'
        self.order_id = AbilityId.FACTORYTRAIN_THOR
        self.requires_techlab = True
        self.requeue_progress = 0.98
