from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Viking(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.VIKINGFIGHTER
        self.buildingIds = [UnitTypeId.STARPORT]
        self.name = 'Viking'
        self.order_id = AbilityId.STARPORTTRAIN_VIKINGFIGHTER

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