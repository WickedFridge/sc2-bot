from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class CombatShield(Upgrade):
    upgrade = UpgradeId.SHIELDWALL
    building = UnitTypeId.BARRACKSTECHLAB
    ability = AbilityId.RESEARCH_COMBATSHIELD
    requirements_ups = [UpgradeId.STIMPACK]
    name = "Combat Shield"

    @override
    @property
    def custom_conditions(self) -> bool:
        marine_count: int = self.bot.units(UnitTypeId.MARINE).amount + self.bot.already_pending(UnitTypeId.MARINE)
        return marine_count >= 10