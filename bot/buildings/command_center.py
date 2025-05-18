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
        base_count: int = self.expansions.amount
        townhalls_count: int = self.bot.townhalls.amount
        return townhalls_count <= base_count + 2
            
    @override
    @property
    def position(self) -> Point2:
        townhall_amount: int = self.bot.townhalls.amount
        cc_position: Point2 = self.expansions.next.position
        match (townhall_amount):
            case 0:
                return self.expansions.main
            case 1:
                return self.expansions.next.position
            case 2:
                return self.expansions.main.position.towards(cc_position, 2)
            case _:
                return self.bot.townhalls.closest_to(cc_position).position.towards(cc_position, 2)