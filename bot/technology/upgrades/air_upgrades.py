from typing import override
from bot.technology.upgrades.upgrade import Upgrade
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class AirAttackUpgrade(Upgrade):
    building = UnitTypeId.ARMORY
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]

    @override
    @property
    def custom_conditions(self) -> bool:
        vikings_amount_target: int = (
            self.bot.units(UnitTypeId.VIKINGFIGHTER).amount
            + self.bot.already_pending(UnitTypeId.VIKINGFIGHTER)
            + self.bot.composition_manager.amount_to_train(UnitTypeId.VIKINGFIGHTER)
        )
        return vikings_amount_target >= 4

class AirAttackLevel1(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL1
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1
    name = "Air +1 Attack"

class AirAttackLevel2(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL2
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2
    requirements_ups = AirAttackUpgrade.requirements_ups + [
        UpgradeId.TERRANSHIPWEAPONSLEVEL1
    ]
    name = "Air +2 Attack"

class AirAttackLevel3(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL3
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3
    requirements_ups = AirAttackUpgrade.requirements_ups + [
        UpgradeId.TERRANSHIPWEAPONSLEVEL2
    ]
    name = "Air +3 Attack"

class AirArmorUpgrade(Upgrade):
    building = UnitTypeId.ARMORY
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]

    @override
    @property
    def custom_conditions(self) -> bool:
        vikings_amount_target: int = (
            self.bot.units(UnitTypeId.VIKINGFIGHTER).amount
            + self.bot.already_pending(UnitTypeId.VIKINGFIGHTER)
            + self.bot.composition_manager.amount_to_train(UnitTypeId.VIKINGFIGHTER)
        )
        medivacs_amount: int = (
            self.bot.units(UnitTypeId.MEDIVAC).amount
            + self.bot.already_pending(UnitTypeId.MEDIVAC)
        )
        return vikings_amount_target + medivacs_amount >= 8
    
class AirArmorLevel1(AirArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1
    name = "Air +1 Armor"
    is_ability = True

class AirArmorLevel2(AirArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2
    requirements_ups = AirArmorUpgrade.requirements_ups + [
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1
    ]
    name = "Air +2 Armor"
    is_ability = True

class AirArmorLevel3(AirArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3
    requirements_ups = AirArmorUpgrade.requirements_ups + [
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2
    ]
    name = "Air +3 Armor"
    is_ability = True