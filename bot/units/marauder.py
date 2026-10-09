from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Marauder(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARAUDER
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marauder'
        self.order_id = AbilityId.BARRACKSTRAIN_MARAUDER
        self.requires_techlab = True
        self.requeue_progress = 0.98
