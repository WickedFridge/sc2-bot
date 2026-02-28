from typing import override

from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class InterferenceMatrix(Upgrade):
    upgrade = UpgradeId.INTERFERENCEMATRIX
    building = UnitTypeId.STARPORTTECHLAB
    ability = AbilityId.STARPORTTECHLABRESEARCH_RESEARCHRAVENINTERFERENCEMATRIX
    name = "Raven Matrix"
    is_ability = True

    @override
    @property
    def custom_conditions(self) -> bool:
        raven_target: int = self.bot.composition_manager.composition[UnitTypeId.RAVEN]
        raven_amount: int = self.bot.units(UnitTypeId.RAVEN).amount + self.bot.already_pending(UnitTypeId.RAVEN)
        return max(raven_target, raven_amount) >= 2