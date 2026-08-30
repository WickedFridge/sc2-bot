from __future__ import annotations
from typing import List, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.scouting.ghost_units.ghost_units import GhostUnit
from bot.utils.army import Army
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import changelings

class MicroSiegeTank(MicroUnit):
    SIEGE_RANGE: int = 13
    MIN_RANGE_SIEGED: int = 2
    MIN_SIEGE_SPACE: float = 1.5
    THRESHOLD: int = 1
    bonus_against_ground_armored: bool = True

    def get_enemies_close_siege_range(self, tank: Unit) -> Units:
        dont_siege_against: List[UnitTypeId] = [UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORBURROWED]
        is_defending: bool = self.bot.structures.closest_distance_to(tank.position) < self.SIEGE_RANGE

        local_enemies: Units = self.get_local_enemy_units(tank.position, include_structures=False).filter(
            lambda enemy: (
                enemy.type_id not in dont_siege_against
            )
        )
        return self.bot.enemy_structures.filter(
            lambda enemy: (
                enemy.is_flying == False
                and enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + enemy.radius - self.THRESHOLD
            )
        ) + local_enemies.filter(
            lambda enemy: (
                enemy.is_flying == False
                and self.MIN_RANGE_SIEGED <= enemy.distance_to(tank) <= (
                    self.SIEGE_RANGE - self.THRESHOLD
                    if is_defending
                    else tank.radius + self.SIEGE_RANGE + enemy.radius + self.THRESHOLD * enemy.real_speed
                )
            )
        )

    
    def switch_mode(self, tank: Unit, enemies_close: Units, buildings_only: bool = False, visible_only: bool = False) -> bool:
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

        # don't siege against creep or changelings
        enemies_close = enemies_close.filter(
            lambda unit: (
                not self.is_creep_tumor(unit)
                and unit.type_id not in changelings
                and (unit.is_visible or not visible_only)
            )
        )

        # buildings_only only gates entering siege mode, not staying sieged:
        # a sieged tank must keep fighting any close enemy, not just buildings
        siege_targets: Units = enemies_close.filter(
            lambda unit: (
                unit.is_structure or not buildings_only
            )
        )

        if (
            tank.type_id == UnitTypeId.SIEGETANK
            and siege_targets.amount >= 1
            and other_tank_sieged_close.amount == 0
        ):
            tank(AbilityId.SIEGEMODE_SIEGEMODE)
            return True
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED and enemies_close.amount == 0):
            tank(AbilityId.UNSIEGE_UNSIEGE)
            return True
        return False

    
    @override
    async def fight(self, tank: Unit, local_units: Units, chase: bool = False):
        enemies_in_range: Units = self.get_enemy_units_in_range(tank).sorted(
            lambda unit: (unit.is_armored == False, unit.health + unit.shield)
        )
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED and enemies_in_range.amount >= 1):
            tank.attack(enemies_in_range.first)
            return
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(tank)
        if (self.switch_mode(tank, enemies_close_siege_range, buildings_only=chase)):
            return

        # if we shouldn't siege but we can hit enemy, do it
        if (tank.weapon_cooldown <= 4 and enemies_in_range.amount >= 1):
            tank.attack(enemies_in_range.first)
            return

        not_tanks: Units = local_units.filter(lambda unit: unit.type_id not in [UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED])
        if (not_tanks.amount >= 1):
            tank.move(local_units.center)
            return

        if (self.bot.enemy_units.amount >= 1):
            closest_enemy: Unit = self.bot.enemy_units.closest_to(tank)
            tank.move(closest_enemy.position)
            return

        if (self.bot.ghost_units.assumed_enemy_units.amount >= 1):
            closest_ghost: GhostUnit = self.bot.ghost_units.assumed_enemy_units.closest_to(tank)
            tank.move(closest_ghost.position)
            return


    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        self.switch_mode(unit, enemy_buildings)
        await self.fight(unit, local_units)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(unit)
        if (self.switch_mode(unit, enemies_close_siege_range, buildings_only=True, visible_only=True)):
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
        # Don't get in the way of flying townhalls
        if (self.bot.townhalls.amount == 0):
            return
        local_flying_townhall: Units = self.bot.structures([UnitTypeId.ORBITALCOMMANDFLYING, UnitTypeId.COMMANDCENTERFLYING]).in_distance_between(unit.position, 0, 10)
        retreat_position: Point2 = self.retreat_position if local_flying_townhall.amount == 0 else self.retreat_position.towards(local_flying_townhall.center, -5)
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(unit)
        
        if (unit.distance_to(retreat_position) > 5):
            if (self.switch_mode(unit, enemies_close_siege_range, visible_only=True)):
                return
            await super().retreat(unit, local_units)
            return
        
        if (unit.type_id == UnitTypeId.SIEGETANK and local_flying_townhall.amount == 0):
            unit(AbilityId.SIEGEMODE_SIEGEMODE)
