from collections.abc import Callable
from typing import Awaitable, Dict, List
from bot.macro.resources import Resources
from bot.superbot import Superbot
from bot.technology.tech import Tech
from bot.technology.upgrades.mech_upgrades import MechArmorLevel1, MechArmorLevel2, MechArmorLevel3, AirAttackLevel1, AirAttackLevel2, AirAttackLevel3, GroundAttackLevel1, GroundAttackLevel2, GroundAttackLevel3, MechUpgrade
from bot.technology.upgrades.blueflame import BlueFlame
from bot.technology.upgrades.building_armor import BuildingArmor
from bot.technology.upgrades.building_range import BuildingRange
from bot.technology.upgrades.caduceus_reactor import CaduceusReactor
from bot.technology.upgrades.combat_shield import CombatShield
from bot.technology.upgrades.concussive_shells import ConcussiveShells
from bot.technology.upgrades.infantry_upgrades import InfantryArmorLevel1, InfantryArmorLevel2, InfantryArmorLevel3, InfantryAttackLevel1, InfantryAttackLevel2, InfantryAttackLevel3
from bot.technology.upgrades.interference_matrix import InterferenceMatrix
from bot.technology.upgrades.magfield import MagfieldAccelerator
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
    ground_attack_level_1: GroundAttackLevel1
    ground_attack_level_2: GroundAttackLevel2
    ground_attack_level_3: GroundAttackLevel3
    air_attack_level_1: AirAttackLevel1
    air_attack_level_2: AirAttackLevel2
    air_attack_level_3: AirAttackLevel3
    mech_armor_level_1: MechArmorLevel1
    mech_armor_level_2: MechArmorLevel2
    mech_armor_level_3: MechArmorLevel3
    mech_upgrades: Dict[UpgradeId, MechUpgrade]
    caduceus_reactor: CaduceusReactor
    interference_maxtrix: InterferenceMatrix
    magfield_accelerator: MagfieldAccelerator
    blueflame: BlueFlame
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
        self.ground_attack_level_1 = GroundAttackLevel1(self)
        self.ground_attack_level_2 = GroundAttackLevel2(self)
        self.ground_attack_level_3 = GroundAttackLevel3(self)
        self.air_attack_level_1 = AirAttackLevel1(self)
        self.air_attack_level_2 = AirAttackLevel2(self)
        self.air_attack_level_3 = AirAttackLevel3(self)
        self.mech_armor_level_1 = MechArmorLevel1(self)
        self.mech_armor_level_2 = MechArmorLevel2(self)
        self.mech_armor_level_3 = MechArmorLevel3(self)
        self.mech_upgrades = {
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL1: self.ground_attack_level_1,
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL2: self.ground_attack_level_2,
            UpgradeId.TERRANVEHICLEWEAPONSLEVEL3: self.ground_attack_level_3,
            UpgradeId.TERRANSHIPWEAPONSLEVEL1: self.air_attack_level_1,
            UpgradeId.TERRANSHIPWEAPONSLEVEL2: self.air_attack_level_2,
            UpgradeId.TERRANSHIPWEAPONSLEVEL3: self.air_attack_level_3,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1: self.mech_armor_level_1,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2: self.mech_armor_level_2,
            UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3: self.mech_armor_level_3,
        }
        self.caduceus_reactor = CaduceusReactor(self)
        self.interference_maxtrix = InterferenceMatrix(self)
        self.magfield_accelerator = MagfieldAccelerator(self)
        self.blueflame = BlueFlame(self)
        self.building_armor = BuildingArmor(self)
        self.building_range = BuildingRange(self)

    @property
    def ordered_mech_upgrade_scores(self) -> List[tuple[UpgradeId, float]]:
        upgrade_scores: List[tuple[UpgradeId, float]] = [
            (upgrade_id, upgrade.score) for upgrade_id, upgrade in self.mech_upgrades.items()
        ]

        # sort by score, highest first (stable sort keeps levels in order)
        upgrade_scores.sort(key=lambda x: x[1], reverse=True)
        return upgrade_scores

    @property
    def ordered_mech_upgrade_types(self) -> List[UpgradeId]:
        return [upgrade_id for upgrade_id, _ in self.ordered_mech_upgrade_scores]

    def searcher_for(self, upgrade_id: UpgradeId) -> Callable[[Resources], Awaitable[Resources]]:
        """Map each UpgradeId to its corresponding search() function."""
        if (upgrade_id not in self.mech_upgrades.keys()):
            raise ValueError(f"No searcher available for {upgrade_id}")

        return self.mech_upgrades[upgrade_id].search

    @property
    def ordered_mech_upgrades(self) -> List[Callable[[Resources], Awaitable[Resources]]]:
        return [self.searcher_for(upgrade_id) for upgrade_id in self.ordered_mech_upgrade_types]