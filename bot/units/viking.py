from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
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
    def custom_conditions(self) -> bool:
        return self.bot.units([UnitTypeId.MEDIVAC]).amount >= 2
    
    def no_addon_conditions(self, starport: Unit) -> bool:
        return (
            not starport.has_add_on
            and starport.is_idle
        )
    
    def reactor_conditions(self, starport: Unit) -> bool:
        return (
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
    
    def techlab_conditions(self, starport: Unit) -> bool:
        return (
            starport.has_techlab
            and (
                starport.is_idle
                or (
                    len(starport.orders) == 1
                    and starport.orders[0].progress >= 0.95
                )
            )
            and not self.bot.composition_manager.should_train(UnitTypeId.RAVEN)
            and not self.bot.composition_manager.should_train(UnitTypeId.BANSHEE)
            and not self.bot.composition_manager.should_train(UnitTypeId.BATTLECRUISER)
        )

    @override
    @property
    def building_group(self) -> Units:
        starports: Units = self.bot.structures(UnitTypeId.STARPORT).ready
        return starports.filter(
            lambda starport: (
                self.no_addon_conditions(starport)
                or self.reactor_conditions(starport)
                or self.techlab_conditions(starport)
            )
        ).sorted(lambda starport: starport.has_reactor, reverse=True)