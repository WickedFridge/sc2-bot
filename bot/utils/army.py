from typing import List
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.player import Bot
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types
from ..utils.unit_supply import supply, units_supply

class Army:
    units: Units
    bot: BotAI

    def __init__(self, units, bot) -> None:
        self.units = units
        self.bot = bot
    
    def detect_units(self, enemy_units: Units) -> None:
        for enemy in enemy_units:
            if enemy.tag not in self.units.tags:
                self.units.append(enemy)
    
    def remove_by_tag(self, tag: int) -> None:
        destroyed_unit: Unit = self.units.by_tag(tag)
        self.units.remove(destroyed_unit)
        print("enemy unit destroyed :", destroyed_unit.name)

    def recap(self) -> dict:
        return {
            'units': self.army_composition(),
            'supply' : self.army_supply(),
        }

    def army_composition(self) -> dict:
        units: Units = self.fighting_units()
        return Army.composition(units)

    def composition(_units: Units) -> dict:
        army: dict = {}
        for unit in _units:
            if (unit.name in army):
                army[unit.name] += 1
            else:
                army[unit.name] = 1
        return army
    
    def army_supply(self) -> float:
        units: Units = self.fighting_units()
        return units_supply(units)
    
    def fighting_units(self) -> Units:
        return self.units.filter(lambda unit: unit.can_attack and unit.type_id not in worker_types)