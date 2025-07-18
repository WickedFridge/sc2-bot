from typing import override
from bot.units.train import Train
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Marine(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.MARINE
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Marine'
    
    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(UnitTypeId.BARRACKS).ready.filter(
            lambda rax: (
                (
                    not rax.has_add_on
                    and rax.is_idle
                ) or (
                    rax.has_reactor
                    and len(rax.orders) < 2
                ) or (
                    rax.has_techlab
                    and not self.trainer.should_train_marauders
                    and not self.trainer.should_train_ghosts
                )
            )
        )