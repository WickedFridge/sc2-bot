from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class InfantryUpgrades(Upgrade):
    building = UnitTypeId.ENGINEERINGBAY
    
    @override
    @property
    def custom_conditions(self) -> bool:
        bio_count: int = (
            self.bot.units([UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.GHOST]).amount
            + self.bot.already_pending(UnitTypeId.MARINE)
            + self.bot.already_pending(UnitTypeId.MARAUDER)
            + self.bot.already_pending(UnitTypeId.GHOST)
        )
        return bio_count >= 10

class InfantryAttackLevel1(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL1
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1
    requirements_ups = [UpgradeId.STIMPACK]
    name = "Infantry +1 Attack"

class InfantryAttackLevel2(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL2
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]
    requirements_buildings = [UnitTypeId.ARMORY]
    name = "Infantry +2 Attack"

class InfantryAttackLevel3(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL3
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
        UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    ]
    name = "Infantry +3 Attack"

class InfantryArmorLevel1(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL1
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1
    requirements_ups = [UpgradeId.STIMPACK]
    name = "Infantry +1 Armor"

class InfantryArmorLevel2(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL2
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]
    requirements_buildings = [UnitTypeId.ARMORY]
    name = "Infantry +2 Armor"

class InfantryArmorLevel3(InfantryUpgrades):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL3
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
        UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    ]
    name = "Infantry +3 Armor"