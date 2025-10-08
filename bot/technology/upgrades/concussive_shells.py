from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class ConcussiveShells(Upgrade):
    upgrade = UpgradeId.PUNISHERGRENADES
    building = UnitTypeId.BARRACKSTECHLAB
    ability = AbilityId.RESEARCH_CONCUSSIVESHELLS
    requirements_ups = [UpgradeId.STIMPACK, UpgradeId.SHIELDWALL]
    name = "Concussive Shells"

    @override
    @property
    def custom_conditions(self) -> bool:
        marauder_count: int = (
            self.bot.units([UnitTypeId.MARINE, UnitTypeId.MARAUDER]).amount
            + self.bot.already_pending(UnitTypeId.MARAUDER)
        )
        target_marauder_count: int = self.bot.composition_manager.amount_to_train(UnitTypeId.MARAUDER)
        return max(marauder_count, target_marauder_count) >= 4