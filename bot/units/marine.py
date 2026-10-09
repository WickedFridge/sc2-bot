from typing import override
from bot.strategy.strategy_types import Situation
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class Marine(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARINE
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marine'
        self.order_id = AbilityId.BARRACKSTRAIN_MARINE

    @property
    @override
    def force_conditions(self) -> bool:
        return self.bot.scouting.situation in [Situation.CHEESE_WORKER_RUSH, Situation.CHEESE_CANNON_RUSH]
