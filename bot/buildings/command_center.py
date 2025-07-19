from typing import override
from bot.buildings.building import Building
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2


class CommandCenter(Building):
    def __init__(self, build):
        super().__init__(build)
        self.unitId = UnitTypeId.COMMANDCENTER
        self.name = "Command Center"
        self.radius = 2

    @override
    @property
    def conditions(self) -> bool:
        base_count: int = self.bot.expansions.amount
        townhalls_count: int = self.bot.townhalls.amount
        factory_count: int = (
            self.bot.structures(UnitTypeId.FACTORY) + 
            self.bot.structures(UnitTypeId.FACTORYFLYING)
        ).amount
        pending_cc_count: int = self.bot.already_pending(UnitTypeId.COMMANDCENTER)
        return (
            (townhalls_count <= 2 or factory_count >= 1) and
            townhalls_count <= base_count + 2 and
            pending_cc_count <= 2
        )    
    @override
    @property
    def position(self) -> Point2:
        townhall_amount: int = self.bot.townhalls.amount
        cc_position: Point2 = self.bot.expansions.next.position
        match (townhall_amount):
            case 0:
                return self.bot.expansions.main.position
            case 1:
                return self.bot.expansions.next.position
            case 2:
                return self.bot.expansions.main.position.towards(cc_position, 2)
            case _:
                return self.bot.townhalls.closest_to(cc_position).position.towards(cc_position, 2)