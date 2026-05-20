from bot.combat.micro_units.bio_unit import MicroBioUnit

class MicroHellbat(MicroBioUnit):
    WEAPON_READY_THRESHOLD: int = 8
    bonus_against_ground_light: bool = True