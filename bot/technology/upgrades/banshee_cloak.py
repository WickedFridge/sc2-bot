from typing import override

from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class BansheeCloak(Upgrade):
    upgrade = UpgradeId.BANSHEECLOAK
    building = UnitTypeId.STARPORTTECHLAB
    ability = AbilityId.RESEARCH_BANSHEECLOAKINGFIELD
    name = "Banshee Cloak"

    @property
    @override
    def custom_conditions(self) -> bool:
        return False