from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Ghost(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.GHOST
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Ghost'
        self.order_id = AbilityId.BARRACKSTRAIN_GHOST
        self.requires_techlab = True
        self.requeue_progress = 0.98
