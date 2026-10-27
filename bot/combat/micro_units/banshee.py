from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroBanshee(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 4

    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        closest_mineral_line: Point2 = self.bot.expansions.closest_to(self.retreat_position).mineral_line
        unit.move(closest_mineral_line)