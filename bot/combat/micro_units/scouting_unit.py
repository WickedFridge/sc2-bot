from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroScoutingUnit(MicroUnit):
    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        # If there isn't any visible unit (ghost units are probably menacing), move to safest spot
        enemy_ground: Units = self.enemy_all.filter(lambda unit: unit.is_flying == False)
        if (enemy_ground.amount == 0):
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(unit)
            unit.move(safest_spot)
            return

        # if no enemy is in range, we are on cooldown and are in range, shoot the lowest unit
        SAFETY: int = 2
        LIFE_THRESHOLD: int = 15
        enemy_units_in_range: Units = self.get_enemy_units_in_range(unit)
        threats: Units = self.enemies_threatening_ground_in_range(unit, safety_distance=SAFETY, range_override=20)

        # --- CASE 1: Weapon Ready ---
        if (unit.weapon_cooldown <= self.WEAPON_READY_THRESHOLD):
            # if we can safely shoot, just shoot
            local_danger: float = self.bot.map.influence_maps.danger.ground[unit.position]
            if (threats.amount == 0 or (unit.health >= LIFE_THRESHOLD and unit.health > local_danger)):
                if (enemy_units_in_range.amount >= 1):
                    # shoot weakest enemy in range
                    target: Unit = enemy_units_in_range.sorted(lambda u: (u.health + u.shield, u.distance_to_squared(unit))).first
                    unit.attack(target)
                else:
                    # move toward closest enemy to chase
                    unit.attack(enemy_ground.closest_to(unit))

            
            # if we can't safely shoot, move away
            else:
                # safest_spot is preferably away from threats
                kite_target = threats.closest_to(unit)
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, kite_target)
                unit.move(safest_spot)
        
       # --- CASE 2: Long cooldown → retreat & wait ---
        else:
            closest_enemy: Unit = enemy_ground.closest_to(unit)
            safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, closest_enemy)
            unit.move(safest_spot)

    @override
    async def disengage(self, unit: Unit, local_units: Units):
        await self.fight(unit, local_units)

    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        await self.retreat(unit, local_units)