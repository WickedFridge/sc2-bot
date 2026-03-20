from bot.combat.micro_units.scouting_unit import MicroScoutingUnit


class MicroHellion(MicroScoutingUnit):
    WEAPON_READY_THRESHOLD: int = 8
    bonus_against_ground_light: bool = True