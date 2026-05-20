from typing import override

from bot.combat.micro_units.scouting_unit import MicroScoutingUnit


class MicroBanshee(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 4