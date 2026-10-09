from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Cyclone(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.CYCLONE
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Cyclone'
        self.order_id = AbilityId.TRAIN_CYCLONE
        self.requires_techlab = True
        self.requeue_progress = 0.98
