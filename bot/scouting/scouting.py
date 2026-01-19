from __future__ import annotations
from typing import List
from bot.strategy.strategy_types import Situation
from bot.utils.army import Army
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import burrowed_units, cloaked_units, tower_types

scouting: Scouting | None = None

tech_unlocked: dict[UnitTypeId, List[UnitTypeId]] = {
    # zerg tech
    UnitTypeId.SPAWNINGPOOL: [UnitTypeId.ZERGLING, UnitTypeId.QUEEN],
    UnitTypeId.ROACHWARREN: [UnitTypeId.ROACH, UnitTypeId.RAVAGER],
    UnitTypeId.BANELINGNEST: [UnitTypeId.BANELING],
    UnitTypeId.LAIR: [UnitTypeId.OVERSEER],
    UnitTypeId.HYDRALISKDEN: [UnitTypeId.HYDRALISK],
    UnitTypeId.INFESTATIONPIT: [UnitTypeId.INFESTOR, UnitTypeId.SWARMHOSTMP],
    UnitTypeId.SPIRE: [UnitTypeId.MUTALISK, UnitTypeId.CORRUPTOR],
    UnitTypeId.LURKERDEN: [UnitTypeId.LURKER],
    UnitTypeId.HIVE: [UnitTypeId.VIPER],
    UnitTypeId.ULTRALISKCAVERN: [UnitTypeId.ULTRALISK],
    UnitTypeId.GREATERSPIRE: [UnitTypeId.BROODLORD],

    # terran tech
    UnitTypeId.BARRACKS: [UnitTypeId.MARINE, UnitTypeId.REAPER],
    UnitTypeId.BARRACKSTECHLAB: [UnitTypeId.MARAUDER],
    UnitTypeId.GHOSTACADEMY: [UnitTypeId.GHOST],
    UnitTypeId.FACTORY: [UnitTypeId.HELLION, UnitTypeId.WIDOWMINE],
    UnitTypeId.FACTORYTECHLAB: [UnitTypeId.CYCLONE, UnitTypeId.SIEGETANK],
    UnitTypeId.ARMORY: [UnitTypeId.HELLIONTANK, UnitTypeId.THOR],
    UnitTypeId.STARPORT: [UnitTypeId.VIKING, UnitTypeId.MEDIVAC, UnitTypeId.LIBERATOR],
    UnitTypeId.STARPORTTECHLAB: [UnitTypeId.RAVEN, UnitTypeId.BANSHEE],
    UnitTypeId.FUSIONCORE: [UnitTypeId.BATTLECRUISER],

    # protoss tech
    UnitTypeId.GATEWAY: [UnitTypeId.ZEALOT],
    UnitTypeId.CYBERNETICSCORE: [UnitTypeId.STALKER, UnitTypeId.SENTRY, UnitTypeId.ADEPT],
    UnitTypeId.TEMPLARARCHIVE: [UnitTypeId.HIGHTEMPLAR, UnitTypeId.ARCHON],
    UnitTypeId.DARKSHRINE: [UnitTypeId.DARKTEMPLAR, UnitTypeId.ARCHON],
    UnitTypeId.STARGATE: [UnitTypeId.PHOENIX, UnitTypeId.ORACLE, UnitTypeId.VOIDRAY],
    UnitTypeId.FLEETBEACON: [UnitTypeId.TEMPEST, UnitTypeId.CARRIER, UnitTypeId.MOTHERSHIP],
    UnitTypeId.ROBOTICSFACILITY: [UnitTypeId.OBSERVER, UnitTypeId.IMMORTAL, UnitTypeId.WARPPRISM],
    UnitTypeId.ROBOTICSBAY: [UnitTypeId.COLOSSUS, UnitTypeId.DISRUPTOR]
}

class Scouting:
    bot: BotAI
    known_enemy_army: Army
    known_enemy_buildings: Units
    known_enemy_tech: List[UnitTypeId] = []
    possible_enemy_composition: List[UnitTypeId] = []
    known_enemy_composition: List[UnitTypeId] = []
    known_enemy_upgrades: List[UpgradeId] = []
    situation: Situation = Situation.STABLE
    
    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.known_enemy_army = Army(Units([], bot), bot)
        self.known_enemy_buildings = Units([], bot)

    @property
    def enemy_composition(self) -> dict[UnitTypeId, float]:
        enemy_composition: dict[UnitTypeId, float] = {}
        army_composition: dict[UnitTypeId, int] = self.known_enemy_army.composition
        total_units: float = self.known_enemy_army.units.amount
        for unit_type in army_composition:
            enemy_composition[unit_type] = army_composition[unit_type] / total_units
        return enemy_composition
    
    def detect_enemy_unit(self, unit_type: UnitTypeId):
        if (unit_type not in self.known_enemy_composition):
            self.known_enemy_composition.append(unit_type)
        if (unit_type not in self.possible_enemy_composition):
            self.possible_enemy_composition.append(unit_type)
            deduced_tech: List[UnitTypeId] = self.detect_deduced_tech(unit_type)
            for tech in deduced_tech:
                self.conclude_compo_from_tech(tech)
    
    def conclude_compo_from_tech(self, tech: UnitTypeId):
        unlocked: List[UnitTypeId] = tech_unlocked.get(tech, [])
        for unit_type in unlocked:
            if (unit_type not in self.possible_enemy_composition):
                self.possible_enemy_composition.append(unit_type)
    
    def detect_enemy_army(self):
        enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.type_id not in tower_types)
        self.known_enemy_army.detect_units(enemy_units)
        for enemy in enemy_units:
            self.detect_enemy_unit(enemy.type_id)

            
    def detect_enemy_buildings(self):
        enemy_buildings: Units = self.bot.enemy_structures
        for building in enemy_buildings:
            if (building.tag not in self.known_enemy_buildings.tags):
                self.known_enemy_buildings.append(building)
            if (building.type_id not in self.known_enemy_tech):
                self.known_enemy_tech.append(building.type_id)
                unlocked: List[UnitTypeId] = tech_unlocked.get(building.type_id, [])
                for tech in unlocked:
                    if (tech not in self.possible_enemy_composition):
                        self.possible_enemy_composition.append(tech)

    def detect_deduced_tech(self, unit_type: UnitTypeId) -> List[UnitTypeId]:
        deduced_tech: List[UnitTypeId] = []
        for tech_building, units_unlocked in tech_unlocked.items():
            if (unit_type in units_unlocked and tech_building not in deduced_tech):
                deduced_tech.append(tech_building)
        return deduced_tech
    
    async def detect_enemy_upgrades(self):
        await self.detect_burrow()

    async def detect_burrow(self):
        if (UpgradeId.BURROW in self.known_enemy_upgrades):
            return
        if (
            any([unit_type in burrowed_units + cloaked_units for unit_type in self.possible_enemy_composition])
            or self.bot.enemy_units.filter(lambda unit: unit.is_burrowed).amount >= 1
            or self.bot.time > 60 * 10
        ):
            print("Burrow/cloack detected !")
            await self.bot.client.chat_send("Tag:Detection", False)
            self.known_enemy_upgrades.append(UpgradeId.BURROW)

    
    def unit_died(self, unit_tag: int):
        if (unit_tag in self.known_enemy_army.units.tags):
            self.known_enemy_army.remove_by_tag(unit_tag)
            enemy_army: dict = self.known_enemy_army.recap
            print("remaining enemy units :", enemy_army)
        elif (unit_tag in self.known_enemy_buildings.tags):
            destroyed_building: Unit = self.known_enemy_buildings.by_tag(unit_tag)
            self.known_enemy_buildings.remove(destroyed_building)
    
def get_scouting(bot: BotAI) -> Scouting:
    global scouting
    if (scouting is None):
        scouting = Scouting(bot)
    return scouting