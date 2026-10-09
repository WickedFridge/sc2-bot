from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Banshee(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.BANSHEE
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Banshee'
        self.order_id = AbilityId.STARPORTTRAIN_BANSHEE
        self.requires_techlab = True
        self.requeue_progress = 0.98
