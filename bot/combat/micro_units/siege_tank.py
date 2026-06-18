from typing import List, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.superbot import Superbot
from bot.utils.army import Army
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroSiegeTank(MicroUnit):
    SIEGE_RANGE: int = 13
    MIN_RANGE_SIEGED: int = 2
    MIN_SIEGE_SPACE: int = 2
    THRESHOLD: int = 1
    bonus_against_ground_armored: bool = True

    def get_enemies_close_siege_range(self, tank: Unit):
        dont_siege_against: List[UnitTypeId] = [UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORBURROWED]
        
        local_enemies: Units = self.get_local_enemy_units(tank.position, include_structures=False).filter(
            lambda enemy: enemy.type_id not in dont_siege_against
        )
        return self.bot.enemy_structures.filter(
            lambda enemy: (
                enemy.is_flying == False
                and enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + enemy.radius - self.THRESHOLD
            )
        ) + local_enemies.filter(
            lambda enemy: (
                enemy.is_flying == False
                and self.MIN_RANGE_SIEGED <= enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + enemy.radius + self.THRESHOLD
            )
        )

    
    def switch_mode(self, tank: Unit, enemies_close: Units) -> bool:
        # don't siege too close to another tank
        other_tank_sieged_close: Units = self.bot.units.filter(
            lambda other: (
                other.tag != tank.tag
                and tank.distance_to(other) <= self.MIN_SIEGE_SPACE + tank.radius + other.radius
                and (
                    other.type_id == UnitTypeId.SIEGETANKSIEGED
                    or (
                        other.type_id == UnitTypeId.SIEGETANK
                        and len(other.orders) >= 1
                        and other.orders[0].ability.id == AbilityId.SIEGEMODE_SIEGEMODE
                    ) 
                )
            )
        )
        if (tank.type_id == UnitTypeId.SIEGETANK and enemies_close.amount >= 1 and other_tank_sieged_close.amount == 0):
            tank(AbilityId.SIEGEMODE_SIEGEMODE)
            return True
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED and enemies_close.amount == 0):
            tank(AbilityId.UNSIEGE_UNSIEGE)
            return True
        return False

    
    @override
    async def fight(self, tank: Unit, local_units: Units, chase: bool = False):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(tank)
        if (not chase and self.switch_mode(tank, enemies_close_siege_range)):
            return
        enemies_in_range: Units = self.get_enemy_units_in_range(tank).sorted(
                lambda unit: (unit.is_armored == False, unit.health + unit.shield)
        )
        if (enemies_in_range.amount >= 1):
            tank.attack(enemies_in_range.first)
        enemies_in_range: Units = self.get_enemy_units_in_range(tank)
        tank.move(local_units.center)

    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        self.switch_mode(unit, enemy_buildings)
        await self.fight(unit, local_units)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(unit)
        if (self.switch_mode(unit, enemies_close_siege_range)):
            return
        await super().harass(unit, local_units, workers)
    
    @override
    async def a_move(self, unit: Unit, target: Point2):
        self.switch_mode(unit, Units([], self.bot))
        await super().a_move(unit, target)
    
    @override
    async def attack_nearest_base(self, unit: Unit, army: Army, target: Point2):
        self.switch_mode(unit, Units([], self.bot))
        await super().attack_nearest_base(unit, army, target)

    @override
    async def chase_buildings(self, unit: Unit, army: Army, target: Point2):
        self.switch_mode(unit, Units([], self.bot))
        await super().chase_buildings(unit, army, target)

    @override
    async def retreat(self, unit: Unit, local_units: Units):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(unit)
        if (self.switch_mode(unit, enemies_close_siege_range)):
            return
        await super().retreat(unit, local_units)
        
