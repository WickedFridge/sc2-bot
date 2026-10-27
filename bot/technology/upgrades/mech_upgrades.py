from typing import Dict, override
from bot.technology.upgrades.upgrade import Upgrade
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

class MechUpgrade(Upgrade):
    building = UnitTypeId.ARMORY
    requirements_ups = [
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    ]
    # unit type -> coefficient applied to the supply of these units (current + pending + to train)
    scoring_units: Dict[UnitTypeId, float] = {}
    # minimum score required for the upgrade to be researched
    min_score: float = 0

    def _weighted_projected_amount(self, unit_type: UnitTypeId) -> float:
        return (
            self.bot.total_unit_amount(unit_type)
            + self.bot.composition_manager.amount_to_train(unit_type) / 2
        )

    @property
    def score(self) -> float:
        return sum(
            weight * self._weighted_projected_amount(unit_type)
            for unit_type, weight in self.scoring_units.items()
        )

    @property
    @override
    def custom_conditions(self) -> bool:
        return self.score >= self.min_score

class GroundAttackUpgrade(MechUpgrade):
    scoring_units = {
        UnitTypeId.HELLION: 1,
        UnitTypeId.CYCLONE: 0,
        UnitTypeId.SIEGETANK: 3,
        UnitTypeId.THOR: 4,
    }
    min_score = 8

class GroundAttackLevel1(GroundAttackUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEWEAPONSLEVEL1
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1
    name = "Ground +1 Atk"
    short_name = "Gnd +1 Atk"

class GroundAttackLevel2(GroundAttackUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEWEAPONSLEVEL2
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2
    requirements_ups_completed = [
        UpgradeId.TERRANVEHICLEWEAPONSLEVEL1
    ]
    name = "Ground +2 Atk"
    short_name = "Gnd +2 Atk"

class GroundAttackLevel3(GroundAttackUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEWEAPONSLEVEL3
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3
    requirements_ups_completed = [
        UpgradeId.TERRANVEHICLEWEAPONSLEVEL2
    ]
    name = "Ground +3 Atk"
    short_name = "Gnd +3 Atk"

class AirAttackUpgrade(MechUpgrade):
    scoring_units = {
        UnitTypeId.VIKINGFIGHTER: 3,
        UnitTypeId.BANSHEE: 1,
    }
    # ~4 vikings
    min_score = 8

class AirAttackLevel1(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL1
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1
    name = "Air +1 Atk"

class AirAttackLevel2(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL2
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2
    requirements_ups_completed = [
        UpgradeId.TERRANSHIPWEAPONSLEVEL1
    ]
    name = "Air +2 Atk"

class AirAttackLevel3(AirAttackUpgrade):
    upgrade = UpgradeId.TERRANSHIPWEAPONSLEVEL3
    ability = AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3
    requirements_ups_completed = [
        UpgradeId.TERRANSHIPWEAPONSLEVEL2
    ]
    name = "Air +3 Atk"

class MechArmorUpgrade(MechUpgrade):
    # Vehicle & Ship Plating benefits every mech unit
    scoring_units = {
        UnitTypeId.HELLION: 1,
        UnitTypeId.CYCLONE: 1.5,
        UnitTypeId.SIEGETANK: 0.5,
        UnitTypeId.THOR: 2,
        UnitTypeId.VIKINGFIGHTER: 1,
        UnitTypeId.BANSHEE: 0.5,
        UnitTypeId.RAVEN: 1.25,
        UnitTypeId.MEDIVAC: 0.75,
    }
    # ~8 vikings/medivacs
    min_score = 10

class MechArmorLevel1(MechArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1
    name = "Mech +1 Def"
    short_name = "Mch +1 Def"
    is_ability = True

class MechArmorLevel2(MechArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2
    requirements_ups_completed = [
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1
    ]
    name = "Mech +2 Def"
    short_name = "Mch +2 Def"
    is_ability = True

class MechArmorLevel3(MechArmorUpgrade):
    upgrade = UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3
    ability = AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3
    requirements_ups_completed = [
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2
    ]
    name = "Mech +3 Def"
    short_name = "Mch +3 Def"
    is_ability = True
