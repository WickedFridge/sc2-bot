from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class BuildingArmor(Upgrade):
    upgrade = UpgradeId.TERRANBUILDINGARMOR
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
        UpgradeId.TERRANINFANTRYARMORSLEVEL3,
    ]
    name = "Building Armor"

    @override
    @property
    def custom_conditions(self) -> bool:
        planetary_fortress_amount: int = (
            self.bot.structures(UnitTypeId.PLANETARYFORTRESS).amount
            + self.bot.already_pending(UnitTypeId.PLANETARYFORTRESS)
        )
        return planetary_fortress_amount >= 2