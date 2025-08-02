from typing import List, Optional
from bot.combat.orders import Orders
from bot.superbot import Superbot
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types, menacing, bio
from ..utils.unit_supply import units_supply, weighted_units_supply


class Army:
    units: Units
    bot: Superbot
    orders: Orders = Orders.RETREAT

    def __init__(self, units, bot: Superbot) -> None:
        self.units = units
        self.bot = bot
    
    @property
    def radius(self) -> float:
        return self.supply * 0.2 + 10
    
    @property
    def center(self) -> Point2:
        return self.units.center
    
    @property
    def ground_center(self) -> Point2:
        return self.units.filter(lambda unit: unit.is_flying != False).center

    @property
    def ground_units(self) -> Units:
        return self.units.not_flying
    
    @property
    def speed(self) -> float:
        if (self.units.amount == 0):
            return 0
        self.units.sort(key = lambda unit: unit.real_speed)
        return self.units.first.real_speed
    
    @property
    def armored_ground_supply(self) -> float:
        armored_ground_units: Units = self.ground_units.filter(
            lambda unit: unit.is_armored
        )
        return units_supply(armored_ground_units)
    
    @property
    def supply(self) -> float:
        return units_supply(self.units)

    @property
    def potential_supply(self) -> float:
        return units_supply(self.potential_fighting_units)
    
    @property
    def weighted_supply(self) -> float:
        return weighted_units_supply(self.fighting_units)
    
    @property
    def bio_supply(self) -> float:
        return units_supply(self.bio_units)
    
    @property
    def potential_bio_supply(self) -> float:
        return units_supply(self.potential_fighting_units.filter(lambda unit: unit.type_id in bio))

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
    def bio_health_percentage(self) -> float:
        bio_units: Units = (self.units + self.passengers).filter(
            lambda unit: unit.type_id in bio
        )
        if (bio_units.amount == 0):
            return 0
        
        bio_health: float = 0
        total_health: float = 0
        for unit in bio_units:
            bio_health += unit.health + unit.shield
            total_health += unit.health_max + unit.shield_max

        return bio_health / total_health
    
    @property
    def passengers(self) -> Units:
        medivacs: Units = self.units(UnitTypeId.MEDIVAC)
        if (medivacs.amount == 0):
            return Units([], self.bot)
        passengers: Units = Units([], self.bot)
        for medivac in medivacs:
            passengers += Units(medivac.passengers, self.bot)
        return passengers

    @property
    def potential_fighting_units(self) -> Units:
        medivacs_filled: Units = self.units(UnitTypeId.MEDIVAC).filter(lambda unit: unit.cargo_used >= 1)
        if (self.fighting_units.amount >= 1):
            return self.fighting_units + self.passengers
        return medivacs_filled + self.passengers
    
    @property
    def bio_units(self) -> Units:
        return self.units.filter(lambda unit: unit.type_id in bio)
    
    @property
    def fighting_units(self) -> Units:
        attacking_units: Units = self.units.filter(
            lambda unit: (
                (unit.can_attack or unit.type_id in menacing)
                and unit.type_id not in worker_types
                and unit.type_id != UnitTypeId.MEDIVAC
            )
        )
        healing_medivacs: Units = self.units(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.energy >= 25
        )
        usable_medivacs: Units = healing_medivacs.take(attacking_units.amount)
        return attacking_units + usable_medivacs

    @property
    def leader(self) -> Optional[Unit]:
        if (self.ground_units.amount == 0):
            return None
        return self.ground_units.sorted(lambda unit: unit.tag).first
    
    @property
    def followers(self) -> Units:
        if (not self.leader):
            return self.units
        return self.units.filter(lambda unit: unit.tag != self.leader.tag)

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
    