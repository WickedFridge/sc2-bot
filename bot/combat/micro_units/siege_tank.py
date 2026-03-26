from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.superbot import Superbot
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units


class MicroSiegeTank(MicroUnit):
    SIEGE_RANGE: int = 13
    THRESHOLD: int = 1
    bonus_against_ground_armored: bool = True

    def get_enemies_close_siege_range(self, tank: Unit):
        local_enemies: Units = self.get_local_enemy_units(tank.position)
        return self.bot.enemy_structures.filter(
            lambda enemy: enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + enemy.radius - self.THRESHOLD
        ) + local_enemies.filter(
            lambda enemy: (
                enemy.is_flying == False and enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + self.THRESHOLD + enemy.radius
            )
        )

    
    def switch_mode(self, tank: Unit, enemies_close: Units) -> bool:
        if (tank.type_id == UnitTypeId.SIEGETANK and enemies_close.amount >= 1):
            tank(AbilityId.SIEGEMODE_SIEGEMODE)
            return True
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED):
            if (enemies_close.amount == 0):
                tank(AbilityId.UNSIEGE_UNSIEGE)
                return True
        return False

    
    @override
    async def fight(self, tank: Unit, local_units: Units, chase: bool = False):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(tank)
        if (self.switch_mode(tank, enemies_close_siege_range)):
            return
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED):
            enemies_in_range: Units = self.get_enemy_units_in_range(tank).sorted(
                lambda unit: (unit.is_armored == False, unit.health + unit.shield)
            )
            if (enemies_in_range.amount >= 1):
                tank.attack(enemies_in_range.first)
        tank.move(local_units.center)

    @override
    async def kill_buildings(self, unit: Unit, local_units: Units, enemy_buildings: Units):
        await self.fight(unit, local_units)

    @override
    async def retreat(self, unit: Unit, local_units: Units):
        enemies_close_siege_range: Units = self.get_enemies_close_siege_range(unit)
        if (self.switch_mode(unit, enemies_close_siege_range)):
            return
        await super().retreat(unit, local_units)
        
