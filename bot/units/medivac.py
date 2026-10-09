from typing import List, override
from bot.units.train import Train
from bot.utils.unit_supply import get_units_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Medivac(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MEDIVAC
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Medivac'
        self.order_id = AbilityId.STARPORTTRAIN_MEDIVAC
        self.techlab_reserved_for = [UnitTypeId.RAVEN, UnitTypeId.BANSHEE, UnitTypeId.BATTLECRUISER]
        self.requeue_progress = 0.97

    @property
    @override
    def custom_conditions(self) -> bool:
        bio_unit_ids: List[UnitTypeId] = [
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.GHOST
        ]
        bio_supply: int = get_units_supply(self.bot.units(bio_unit_ids))
        barracks_inactive: Units = self.bot.structures(UnitTypeId.BARRACKS).ready.filter(lambda rax: not rax.is_active)

        return (
            bio_supply >= 10
            or barracks_inactive.amount == 0
        )