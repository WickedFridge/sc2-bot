from typing import List
from bot.combat.orders import Orders
from sc2.bot_ai import BotAI
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types, menacing
from ..utils.unit_supply import units_supply, weighted_units_supply


class Army:
    units: Units
    bot: BotAI
    orders: Orders = Orders.RETREAT

    def __init__(self, units, bot) -> None:
        self.units = units
        self.bot = bot
    
    @property
    def center(self) -> Point2:
        return self.units.center

    @property
    def speed(self) -> float:
        if (self.units.amount == 0):
            return 0
        self.units.sort(key = lambda unit: unit.real_speed)
        return self.units.first.real_speed
    
    @property
    def armored_supply(self) -> float:
        armored_units: Units = self.units.filter(lambda unit: unit.is_armored)
        return units_supply(armored_units)
    
    @property
    def supply(self) -> float:
        return units_supply(self.fighting_units)

    @property
    def weighted_supply(self) -> float:
        return weighted_units_supply(self.fighting_units)

    @property
    def units_not_in_sight(self) -> Units:
        unseen_units: List[Unit] = []
        for unit in self.units:
            if unit.tag not in self.bot.enemy_units.tags:
                unseen_units.append(unit)
        return Units(unseen_units, self.bot)
    
    @property
    def recap(self) -> dict:
        return {
            'units': self.composition,
            'supply' : self.supply,
        }
    
    @property
    def composition(self) -> dict:
        return Army.get_composition(self.fighting_units)

    @property
    def fighting_units(self) -> Units:
        return self.units.filter(
            lambda unit: (
                (unit.can_attack or unit.type_id in menacing)
                and unit.type_id not in worker_types
            )
        )

    def detect_units(self, enemy_units: Units) -> None:
        for enemy in enemy_units:
            if enemy.tag not in self.units.tags:
                self.units.append(enemy)
    
    def remove_by_tag(self, tag: int) -> None:
        destroyed_unit: Unit = self.units.by_tag(tag)
        self.units.remove(destroyed_unit)
        # print("enemy unit destroyed :", destroyed_unit.name)
    
    def get_composition(_units: Units) -> dict:
        army: dict = {}
        for unit in _units:
            if (unit.name in army):
                army[unit.name] += 1
            else:
                army[unit.name] = 1
        return army
    