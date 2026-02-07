import math
from typing import List, Optional
from bot.combat.orders import Orders
from sc2.bot_ai import BotAI
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import worker_types, menacing, bio
from ..utils.unit_supply import get_units_supply, weighted_units_supply


class Army(CachedClass):
    units: Units
    orders: Orders = Orders.RETREAT

    def __init__(self, units: Units, bot: BotAI) -> None:
        super().__init__(bot)
        self.units = units
    
    @property
    def tags(self) -> List[int]:
        return self.units.tags
    
    @property
    def radius(self) -> float:
        return math.sqrt(self.supply) + 10
    
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
        return get_units_supply(armored_ground_units)
    
    @property
    def armored_ratio(self) -> float:
        if (self.supply == 0):
            return 0
        return self.armored_ground_supply / self.supply
    
    @property
    def flying_fighting_supply(self) -> float:
        return get_units_supply(self.units.flying.filter(lambda unit: unit.can_attack))

    @property
    def supply(self) -> float:
        return get_units_supply(self.units)

    @property
    def fighting_supply(self) -> int:
        return get_units_supply(self.fighting_units)

    @property
    def potential_supply(self) -> float:
        return get_units_supply(self.potential_fighting_units)
    
    @property
    def weighted_supply(self) -> float:
        return weighted_units_supply(self.fighting_units)
    
    @property
    def bio_supply(self) -> float:
        return get_units_supply(self.bio_units)
    
    @property
    def potential_bio_supply(self) -> float:
        return get_units_supply(self.potential_fighting_units.filter(lambda unit: unit.type_id in bio))
    
    @property
    def can_drop_medivacs(self) -> Units:
        return self.units(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.health_percentage >= 0.4
        )
    
    @property
    def cant_drop_medivacs(self) -> Units:
        return self.units(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.health_percentage < 0.4
        )
    
    @property
    def can_heal_medivacs(self) -> Units:
        return self.units(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.energy >= 25
        )
    
    @property
    def can_attack_ground(self) -> bool:
        return self.units.filter(lambda unit: unit.can_attack_ground).amount >= 1
    
    @property
    def units_not_in_sight(self) -> Units:
        unseen_units: List[Unit] = []
        for unit in self.units:
            if (unit.tag not in self.bot.enemy_units.tags):
                unseen_units.append(unit)
        return Units(unseen_units, self.bot)
    
    @property
    def recap(self) -> dict[str, dict[UnitTypeId, int] | float]:
        return {
            'units': self.composition,
            'supply' : self.supply,
        }
    
    @property
    def composition(self) -> dict[UnitTypeId, int]:
        return Army.get_composition(self.units)

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
    def cargo_left(self) -> int:
        two_fullest_medivacs: Units = self.units(UnitTypeId.MEDIVAC).sorted(
            key = lambda medivac: medivac.cargo_used, reverse=True
        ).take(2)
        return sum([medivac.cargo_left for medivac in two_fullest_medivacs])
    
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

    @property
    def is_drop(self) -> bool:
        # we are a drop if we have more passengers than bio units or we have 2 fully loaded medivacs
        return (
            self.passengers.amount > self.bio_units.amount
            or (self.cargo_left == 0 and self.units(UnitTypeId.MEDIVAC).amount >= 2)
        )

    @property
    def is_full_drop(self) -> bool:
        return (
            self.units(UnitTypeId.MEDIVAC).amount >= 1
            and self.passengers.amount > 0
            and self.ground_units.amount == 0
        )

    @property
    def average_ground_range(self) -> float:
        attacking_units: Units = self.ground_units.filter(lambda unit: unit.can_attack)
        if (attacking_units.amount == 0):
            return 0
        total_range: float = sum([unit.ground_range for unit in attacking_units])
        return total_range / attacking_units.amount
    
    def detect_units(self, enemy_units: Units) -> None:
        for enemy in enemy_units:
            if (enemy.tag in self.units.tags):
                self.remove_by_tag(enemy.tag)
            self.units.append(enemy)
    
    def remove_by_tag(self, tag: int) -> None:
        destroyed_unit: Unit = self.units.by_tag(tag)
        self.units.remove(destroyed_unit)
        # print("enemy unit destroyed :", destroyed_unit.name)
    
    def get_composition(_units: Units) -> dict[UnitTypeId, int]:
        army: dict[UnitTypeId, int] = {}
        for unit in _units:
            if (unit.type_id in army):
                army[unit.type_id] += 1
            else:
                army[unit.type_id] = 1
        return army
    