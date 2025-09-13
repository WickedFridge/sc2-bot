from typing import List, override
from bot.units.train import Train
from bot.utils.unit_supply import units_supply
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

    @override
    @property
    def custom_conditions(self) -> bool:
        bio_unit_ids: List[UnitTypeId] = [
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.GHOST
        ]
        bio_supply: int = units_supply(self.bot.units(bio_unit_ids))
        barracks_inactive: Units = self.bot.structures(UnitTypeId.BARRACKS).ready.filter(lambda rax: not rax.is_active)

        return (
            bio_supply >= 10
            or barracks_inactive.amount == 0
        )
    
    @override
    @property
    def building_group(self) -> Units:
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        return starports.filter(
            lambda starport: (
                len(starport.orders) == 0
                or (
                    len(starport.orders) == 1
                    and starport.orders[0].progress >= 0.97
                )
                or (
                    starport.has_reactor
                    and (
                        len(starport.orders) < 2
                        or (
                            len(starport.orders) == 2
                            and (
                                starport.orders[0].progress >= 0.97                        
                                or starport.orders[1].progress >= 0.97
                            )
                        )
                    )
                )
            )
        )