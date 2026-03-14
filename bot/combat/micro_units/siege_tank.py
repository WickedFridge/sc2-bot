from bot.combat.micro_units.micro_unit import MicroUnit
from bot.superbot import Superbot
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units


class MicroSiegeTank(MicroUnit):
    bot: Superbot
    SIEGE_RANGE: int = 13
    THRESHOLD: int = 1

    def fight(self, tank: Unit, local_army: Units):
        local_enemies: Units = self.get_local_enemy_units(tank.position)
        enemies_close_siege_range: Units = self.bot.enemy_structures.filter(
            lambda enemy: enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + enemy.radius - self.THRESHOLD
        ) + local_enemies.filter(
            lambda enemy: enemy.distance_to(tank) <= tank.radius + self.SIEGE_RANGE + self.THRESHOLD + enemy.radius
        )

        if (tank.type_id == UnitTypeId.SIEGETANK and enemies_close_siege_range.amount >= 1):
            tank(AbilityId.SIEGEMODE_SIEGEMODE)
            return
        if (tank.type_id == UnitTypeId.SIEGETANKSIEGED):
            if (enemies_close_siege_range.amount == 0):
                tank(AbilityId.UNSIEGE_UNSIEGE)
                return
            enemies_in_range: Units = self.get_enemy_units_in_range(tank).sorted(
                lambda unit: (unit.is_armored == False, unit.health + unit.shield)
            )
            if (enemies_in_range.amount >= 1):
                tank.attack(enemies_in_range.first)
        tank.move(local_army.center)

