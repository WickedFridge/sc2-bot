from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Reaper(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.REAPER
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Reaper'
        self.order_id = AbilityId.BARRACKSTRAIN_REAPER