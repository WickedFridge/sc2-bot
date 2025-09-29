from typing import override
from bot.buildings.building import Building
from bot.macro.expansion import Expansion
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
        medivac_count: int = self.bot.units(UnitTypeId.MEDIVAC).amount + self.bot.already_pending(UnitTypeId.MEDIVAC)
        pending_cc_count: int = self.bot.already_pending(UnitTypeId.COMMANDCENTER)
        max_pending_cc_count: int = 2
        orbital_count: int = self.bot.structures(UnitTypeId.ORBITALCOMMAND).amount + self.bot.already_pending(UnitTypeId.ORBITALCOMMAND)

        match(townhalls_count):
            case 0 | 1:
                return orbital_count >= 1
            case 2:
                return medivac_count >= 2 or self.bot.minerals >= 600
            case _:
                return (
                    townhalls_count <= base_count + 2 and
                    pending_cc_count < max_pending_cc_count
                )

    @override
    @property
    def position(self) -> Point2:
        townhall_amount: int = self.bot.townhalls.amount
        cc_position: Point2 = self.bot.expansions.next.position
        next_expansion: Expansion = self.bot.expansions.next
        near_cc_position: Point2 = self.bot.expansions.main.position.towards(cc_position, 2)
        match (townhall_amount):
            case 0:
                return self.bot.expansions.main.position
            case 1:
                return next_expansion.position if next_expansion.is_safe else near_cc_position
            case 2:
                return near_cc_position
            case _:
                return self.bot.expansions.taken.safe.closest_to(cc_position).position.towards(cc_position, 2)