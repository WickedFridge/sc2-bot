from __future__ import annotations
from typing import List
from bot.utils.army import Army
from sc2.bot_ai import BotAI
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.units import Units

scouting: Scouting | None = None

class Scouting:
    bot: BotAI
    known_enemy_army: Army
    known_enemy_composition: List[UnitTypeId] = []
    known_enemy_upgrades: List[UpgradeId] = []
    
    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.known_enemy_army = Army(Units([], bot), bot)

    @property
    def enemy_composition(self) -> dict[UnitTypeId, float]:
        enemy_composition: dict[UnitTypeId, float] = {}
        army_composition: dict[UnitTypeId, int] = self.known_enemy_army.composition
        total_units: float = self.known_enemy_army.units.amount
        for unit_type in army_composition:
            enemy_composition[unit_type] = army_composition[unit_type] / total_units
        return enemy_composition
    
    def detect_enemy_army(self):
        enemy_units: Units = self.bot.enemy_units
        self.known_enemy_army.detect_units(enemy_units)
        for enemy in enemy_units:
            if (enemy.type_id not in self.known_enemy_composition):
                self.known_enemy_composition.append(enemy.type_id)
            
    def detect_enemy_upgrades(self):
        self.detect_burrow()

    def detect_burrow(self):
        if (UpgradeId.BURROW in self.known_enemy_upgrades):
            return
        if (
            self.bot.enemy_units(UnitTypeId.ROACHBURROWED).amount >= 1
            or self.bot.enemy_units.filter(lambda unit: unit.is_burrowed).amount >= 1
        ):
            print("Burrow detected")
            self.known_enemy_upgrades.append(UpgradeId.BURROW)

    
    def unit_died(self, unit_tag: int):
        if (unit_tag not in self.known_enemy_army.units.tags):
            return
        self.known_enemy_army.remove_by_tag(unit_tag)
        enemy_army: dict = self.known_enemy_army.recap
        print("remaining enemy units :", enemy_army)
    
def get_scouting(bot: BotAI) -> Scouting:
    global scouting
    if (scouting is None):
        scouting = Scouting(bot)
    return scouting