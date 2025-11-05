from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class Stimpack(Upgrade):
    upgrade = UpgradeId.STIMPACK
    building = UnitTypeId.BARRACKSTECHLAB
    ability = AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK
    name = "Stimpack"
    block_gas_only = True

    @override
    @property
    def custom_conditions(self) -> bool:
        bio_count: int = (
            self.bot.units([UnitTypeId.MARINE, UnitTypeId.MARAUDER]).amount
            + self.bot.already_pending(UnitTypeId.MARINE)
            + self.bot.already_pending(UnitTypeId.MARAUDER)
        )
        return bio_count >= 6