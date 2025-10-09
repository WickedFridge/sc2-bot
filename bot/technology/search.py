from typing import List
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.technology.tech import Tech
from bot.technology.upgrades.air_upgrades import AirArmorLevel1, AirArmorLevel2, AirArmorLevel3, AirAttackLevel1, AirAttackLevel2, AirAttackLevel3
from bot.technology.upgrades.building_armor import BuildingArmor
from bot.technology.upgrades.building_range import BuildingRange
from bot.technology.upgrades.caduceus_reactor import CaduceusReactor
from bot.technology.upgrades.combat_shield import CombatShield
from bot.technology.upgrades.concussive_shells import ConcussiveShells
from bot.technology.upgrades.infantry_upgrades import InfantryArmorLevel1, InfantryArmorLevel2, InfantryArmorLevel3, InfantryAttackLevel1, InfantryAttackLevel2, InfantryAttackLevel3
from bot.technology.upgrades.stimpack import Stimpack
from bot.utils.fake_order import FakeOrder
from sc2.game_data import Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit


class Search:
    bot: Superbot
    shield_researched: bool = False
    concussive_shells_researched: bool = False
    tech_tree_primary: List[Tech] = []
    stimpack: Stimpack
    combat_shield: CombatShield
    concussive_shells: ConcussiveShells
    infantry_attack_level_1: InfantryAttackLevel1
    infantry_attack_level_2: InfantryAttackLevel2
    infantry_attack_level_3: InfantryAttackLevel3
    infantry_armor_level_1: InfantryArmorLevel1
    infantry_armor_level_2: InfantryArmorLevel2
    infantry_armor_level_3: InfantryArmorLevel3
    air_attack_level_1: AirAttackLevel1
    air_attack_level_2: AirAttackLevel2
    air_attack_level_3: AirAttackLevel3
    air_armor_level_1: AirArmorLevel1
    air_armor_level_2: AirArmorLevel2
    air_armor_level_3: AirArmorLevel3
    caduceus_reactor: CaduceusReactor
    building_armor: BuildingArmor
    building_range: BuildingRange

    def __init__(self, bot: Superbot) -> None:
        super().__init__()
        self.bot = bot
        self.stimpack = Stimpack(self)
        self.combat_shield = CombatShield(self)
        self.concussive_shells = ConcussiveShells(self)
        self.infantry_attack_level_1 = InfantryAttackLevel1(self)
        self.infantry_attack_level_2 = InfantryAttackLevel2(self)
        self.infantry_attack_level_3 = InfantryAttackLevel3(self)
        self.infantry_armor_level_1 = InfantryArmorLevel1(self)
        self.infantry_armor_level_2 = InfantryArmorLevel2(self)
        self.infantry_armor_level_3 = InfantryArmorLevel3(self)
        self.air_attack_level_1 = AirAttackLevel1(self)
        self.air_attack_level_2 = AirAttackLevel2(self)
        self.air_attack_level_3 = AirAttackLevel3(self)
        self.air_armor_level_1 = AirArmorLevel1(self)
        self.air_armor_level_2 = AirArmorLevel2(self)
        self.air_armor_level_3 = AirArmorLevel3(self)
        self.caduceus_reactor = CaduceusReactor(self)
        self.building_armor = BuildingArmor(self)
        self.building_range = BuildingRange(self)