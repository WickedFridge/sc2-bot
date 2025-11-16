from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class Factory(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.FACTORY
        self.name = "Factory"

    @override
    @property
    def custom_conditions(self) -> bool:
        facto_tech_requirement: float = self.bot.tech_requirement_progress(UnitTypeId.FACTORY)
        max_factories: int = 1
        factories_amount: int = (
            self.bot.structures(UnitTypeId.FACTORY).ready.amount
            + self.bot.structures(UnitTypeId.FACTORYFLYING).ready.amount
            + self.bot.already_pending(UnitTypeId.FACTORY)
        )
        # addons_amount: int = (
        #     self.bot.structures(UnitTypeId.BARRACKSREACTOR).amount
        #     + self.bot.structures(UnitTypeId.BARRACKSTECHLAB).amount
        # )

        # We want 1 factory so far
        return (
            facto_tech_requirement == 1
            # and self.bot.townhalls.amount >= 2
            # and addons_amount >= 1
            and factories_amount < max_factories
        )
    
    @override
    @property
    def position(self) -> Point2:
        return self.bot.expansions.main.position.towards(self.bot.game_info.map_center, 4)            