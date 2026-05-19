from bot.combat.micro_units.micro_unit import MicroUnit

class MicroHellbat(MicroUnit):
    WEAPON_READY_THRESHOLD: int = 6
    bonus_against_ground_light: bool = True