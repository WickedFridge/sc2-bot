from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class InfantryAttackLevel1(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL1
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1
    requirements_ups = [UpgradeId.STIMPACK]
    name = "Infantry +1 Attack"

class InfantryAttackLevel2(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL2
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]
    requirements_buildings = [UnitTypeId.ARMORY]
    name = "Infantry +2 Attack"

class InfantryAttackLevel3(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYWEAPONSLEVEL3
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
        UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    ]
    name = "Infantry +3 Attack"

class InfantryArmorLevel1(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL1
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1
    requirements_ups = [UpgradeId.STIMPACK]
    name = "Infantry +1 Armor"

class InfantryArmorLevel2(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL2
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]
    requirements_buildings = [UnitTypeId.ARMORY]
    name = "Infantry +2 Armor"

class InfantryArmorLevel3(Upgrade):
    upgrade = UpgradeId.TERRANINFANTRYARMORSLEVEL3
    building = UnitTypeId.ENGINEERINGBAY
    ability = AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
        UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    ]
    name = "Infantry +3 Armor"