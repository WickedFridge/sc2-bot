from typing import override
from bot.units.train import Train
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units


class Marine(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARINE
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marine'
        self.order_id = AbilityId.BARRACKSTRAIN_MARINE
    
    def no_addon_conditions(self, rax: Unit) -> bool:
        return (
            not rax.has_add_on
            and rax.is_idle
        )
    
    def reactor_conditions(self, rax: Unit) -> bool:
        return (
            rax.has_reactor
            and (
                len(rax.orders) < 2
                or (
                    len(rax.orders) == 2
                    and (
                        rax.orders[0].progress >= 0.95
                        or rax.orders[1].progress >= 0.95
                    )
                )
            )
        )
    
    def techlab_conditions(self, rax: Unit) -> bool:
        return (
            rax.has_techlab
            and (
                rax.is_idle
                or (
                    len(rax.orders) == 1
                    and rax.orders[0].progress >= 0.95
                )
            )
            and not self.bot.composition_manager.should_train(UnitTypeId.MARAUDER)
            and not self.bot.composition_manager.should_train(UnitTypeId.GHOST)
        )
    
    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda rax: (
                self.no_addon_conditions(rax)
                or self.reactor_conditions(rax)
                or self.techlab_conditions(rax)
            )
        )