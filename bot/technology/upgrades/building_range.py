from typing import override

from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class BuildingRange(Upgrade):
    upgrade = UpgradeId.HISECAUTOTRACKING
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.RESEARCH_HISECAUTOTRACKING
    requirements_ups = [
        UpgradeId.TERRANBUILDINGARMOR,
    ]
    name = "Building Range"

    @override
    @property
    def custom_conditions(self) -> bool:
        planetary_fortress_amount: int = (
            self.bot.structures(UnitTypeId.PLANETARYFORTRESS).amount
            + self.bot.already_pending(UnitTypeId.PLANETARYFORTRESS)
        )
        return planetary_fortress_amount >= 2