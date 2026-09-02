from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class MagfieldAccelerator(Upgrade):
    upgrade = UpgradeId.CYCLONELOCKONDAMAGEUPGRADE
    building = UnitTypeId.FACTORYTECHLAB
    ability = AbilityId.RESEARCH_CYCLONELOCKONDAMAGE
    name = "Magfield Accelerator"

    @property
    @override
    def custom_conditions(self) -> bool:
        cyclone_target: int = self.bot.composition_manager.composition[UnitTypeId.CYCLONE]
        cyclone_amount: int = self.bot.units(UnitTypeId.CYCLONE).amount + self.bot.already_pending(UnitTypeId.CYCLONE)
        return max(cyclone_target, cyclone_amount) >= 3 and cyclone_amount >= 1