from typing import override
from bot.units.train import Train
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units


class Ghost(Train):
    def __init__(self, trainer):
        super().__init__(trainer)
        self.unitId = UnitTypeId.GHOST
        self.buildingIds = [UnitTypeId.BARRACKS]
        self.name = 'Ghost'
    
    @property
    def custom_conditions(self) -> bool:
        return (
            self.trainer.should_train_ghosts
            and not self.trainer.should_train_marauders
        )

    @override
    @property
    def building_group(self) -> Units:
        return self.bot.structures(UnitTypeId.BARRACKS).ready.idle.filter(lambda rax: rax.has_techlab)