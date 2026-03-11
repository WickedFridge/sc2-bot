from typing import override

from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units


class Hellion(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.HELLION
        self.buildingIds = [UnitTypeId.FACTORY]
        self.name = 'Hellion'
        self.order_id = AbilityId.FACTORYTRAIN_HELLION
    
    def no_addon_conditions(self, facto: Unit) -> bool:
        return (
            not facto.has_add_on
            and facto.is_idle
        )
    
    def reactor_conditions(self, facto: Unit) -> bool:
        return (
            facto.has_reactor
            and (
                len(facto.orders) < 2
                or (
                    len(facto.orders) == 2
                    and (
                        facto.orders[0].progress >= 0.95
                        or facto.orders[1].progress >= 0.95
                    )
                )
            )
        )
    
    def techlab_conditions(self, facto: Unit) -> bool:
        return (
            facto.has_techlab
            and (
                facto.is_idle
                or (
                    len(facto.orders) == 1
                    and facto.orders[0].progress >= 0.95
                )
            )
            and not self.bot.composition_manager.should_train(UnitTypeId.CYCLONE)
            and not self.bot.composition_manager.should_train(UnitTypeId.SIEGETANK)
            and not self.bot.composition_manager.should_train(UnitTypeId.THOR)
        )
    
    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(self.buildingIds).ready.filter(
            lambda rax: (
                self.no_addon_conditions(rax)
                or self.reactor_conditions(rax)
                or self.techlab_conditions(rax)
            )
        ).sorted(lambda rax: rax.has_reactor, reverse=True)