from typing import override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroScoutingUnit(MicroUnit):
    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        # If there isn't any visible unit (ghost units are probably menacing), move to safest spot
        enemy_ground: Units = self.enemy_all.filter(lambda unit: unit.is_flying == False)
        if (enemy_ground.amount == 0):
            enemy_ghosts: GhostUnits = self.bot.ghost_units.assumed_enemy_units.sorted(
                lambda ghost_unit: unit.distance_to(ghost_unit.position)
            )
            if (unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD or enemy_ghosts.amount == 0):
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(unit)
                unit.move(safest_spot)
                return
            closest_ghost_unit: GhostUnit = enemy_ghosts.first
            unit.attack(closest_ghost_unit.position)
            return

        # if no enemy is in range, we are on cooldown and are in range, shoot the lowest unit
        SAFETY: int = 2
        LIFE_THRESHOLD: int = 15
        enemy_units_in_range: Units = self.get_enemy_units_in_range(unit)
        threats: Units = (
            self.enemies_threatening_ground_in_range(unit, safety_distance=SAFETY, range_override=20)
            if unit.is_flying == False
            else self.enemies_threatening_air_in_range(unit, safety_distance=SAFETY, range_override=20)
        )
        
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
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        # calculate the range of the unit based on its movement speed + range + cooldown
        closest_worker: Unit = workers.closest_to(unit)
        worker_potential_targets: Units = self.get_potential_targets(unit).sorted(
            lambda worker: ((worker.health + worker.shield), worker.distance_to(unit))
        )
        
        # first case : we're dangerously close to a worker => retreat to a safer spot
        if (workers.closest_distance_to(unit) <= 1.5):
            unit.move(unit.position.towards(closest_worker, -1))
            return
        
        # in these case we should target a worker
        if (worker_potential_targets.amount >= 1 or unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD):
            # define the best target
            target: Unit = worker_potential_targets.first if worker_potential_targets.amount >= 1 else closest_worker
            # if we're not on cooldown and workers are really close, run away
            if (unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD):
                if (workers.closest_distance_to(unit) <= 1.5 and unit.health_percentage < 1):
                    # safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, workers.closest_to(unit), range_modifier=unit.health_percentage)
                    # unit.move(safest_spot)
                    unit.move(unit.position.towards(closest_worker, -1))
                else:
                    # move towards the unit but not too close
                    best_position: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, target, risk=1)
                    unit.move(best_position)
            # if we're on cooldown, shoot at it
            else:
                unit.attack(target)
        else:
            unit.attack(closest_worker)

    @override
    async def disengage(self, unit: Unit, local_units: Units):
        await self.fight(unit, local_units)

    @override
    async def heal_up(self, unit: Unit, local_units: Units):
        await self.retreat(unit, local_units)