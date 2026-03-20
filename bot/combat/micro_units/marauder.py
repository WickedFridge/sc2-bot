from bot.combat.micro_units.bio_unit import MicroBioUnit


class MicroMarauder(MicroBioUnit):
    WITH_MEDIVAC_HEALTH_THRESHOLD: int = 40
    WITHOUT_MEDIVAC_HEALTH_THRESHOLD: int = 55
    bonus_against_ground_armored: bool = True
        