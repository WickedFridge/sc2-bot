from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Hellion(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.HELLION
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Hellion'
        self.order_id = AbilityId.FACTORYTRAIN_HELLION
        # self.techlab_reserved_for = [UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK, UnitTypeId.THOR]
