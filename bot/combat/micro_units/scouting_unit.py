from itertools import permutations
from typing import List, Optional, override

from bot.combat.micro_units.micro_unit import MicroUnit
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.scouting.ghost_units.ghost_units import GhostUnit, GhostUnits
from bot.utils.matchup import Matchup
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.point2_functions.utils import closest_point
from sc2.cache import custom_cache_once_per_frame
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class MicroScoutingUnit(MicroUnit):
    # scouts make a detour to any unscouted base spot closer than this
    DETOUR_SCOUT_DISTANCE: float = 20
    # past this distance from the next unscouted point, head for the base center instead
    BASE_APPROACH_DISTANCE: float = 15

    @custom_cache_once_per_frame
    def enemy_bases_to_scout(self) -> Expansions:
        # always scouted in this order
        return Expansions(self.bot, [
            self.bot.expansions.enemy_b2,
            self.bot.expansions.enemy_main,
            self.bot.expansions.enemy_b3,
            self.bot.expansions.enemy_b4,
        ])

    @custom_cache_once_per_frame
    def home_bases_to_scout(self) -> Expansions:
        home_bases: Expansions = Expansions(self.bot, [])

        match(self.bot.matchup):
            case Matchup.TvZ:
                home_bases.add(self.bot.expansions.b2)

            case Matchup.TvP:
                # scout main + 3 closest air base
                home_bases = self.bot.expansions.sorted(
                    lambda expansion: expansion.position.distance_to(self.bot.expansions.main.position)
                ).take(4)

            case Matchup.TvT | Matchup.TvR:
                # scout main + 3 closest ground base
                home_bases = self.bot.expansions.sorted(
                    lambda expansion: expansion.distance_from_main
                ).take(4)

        return home_bases.filter(lambda base: base not in self.enemy_bases_to_scout.expansions)

    def home_scout_route(self, start: Point2) -> Expansions:
        """
        Unscouted home bases, ordered to minimize the path start -> bases -> enemy natural.
        At most 4 bases, so brute forcing every permutation (24 max) is cheap.
        """
        bases: Expansions = self.home_bases_to_scout.filter(lambda base: not base.is_fully_scouted)
        end: Point2 = self.bot.expansions.enemy_b2.position

        def route_length(order: tuple[Expansion, ...]) -> float:
            points: List[Point2] = [start] + [base.position for base in order] + [end]
            return sum(a.distance_to(b) for a, b in zip(points, points[1:]))

        return Expansions(self.bot, list(min(permutations(bases), key=route_length)))

    def needs_scouting(self, base: Expansion) -> bool:
        # enemy bases: seeing the spot or a building next to it is enough to move on
        if (base in self.enemy_bases_to_scout.expansions):
            return not base.is_scouted and not base.has_enemy_buildings_around
        # other bases must be fully scouted
        return not base.is_fully_scouted

    def base_scout_point(self, unit: Unit, base: Expansion) -> Point2:
        if (base in self.enemy_bases_to_scout.expansions):
            return base.position
        target: Point2 = closest_point(unit.position, base.unscouted_points)
        if (unit.distance_to(target) > self.BASE_APPROACH_DISTANCE):
            return base.position
        return target

    def scout_target(self, unit: Unit) -> Point2:
        # if we pass close to a base that still needs scouting, take a look on the way
        nearby_unscouted_bases: Expansions = self.bot.expansions.filter(
            lambda base: (
                base.position.distance_to(unit) <= self.DETOUR_SCOUT_DISTANCE
                and not base.has_enemy_buildings_around
                and not base.is_scouted
            )
        )
        if (nearby_unscouted_bases.amount >= 1):
            return self.base_scout_point(unit, nearby_unscouted_bases.closest_to(unit))

        for base in self.home_scout_route(unit.position).extended(self.enemy_bases_to_scout.expansions):
            if (self.needs_scouting(base)):
                return self.base_scout_point(unit, base)

        return self.bot.expansions.enemy_main.mineral_line

    @override
    async def scout(self, unit: Unit, local_units: Units):
        unit.move(self.scout_target(unit))

    @override
    async def fight(self, unit: Unit, local_units: Units, chase: bool = False):
        # If there isn't any visible unit (ghost units are probably menacing), move to safest spot
        enemy_ground: Units = self.enemy_all.filter(lambda unit: unit.is_flying == False)
        if (enemy_ground.amount == 0):
            closest_ghost_unit: Optional[GhostUnit] = self.closest_local_ghost(unit)
            if (unit.weapon_cooldown > self.WEAPON_READY_THRESHOLD or closest_ghost_unit is None):
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_around_unit(unit)
                unit.move(safest_spot)
                return
            unit.attack(closest_ghost_unit.position)
            return

        # if no enemy is in range, we are on cooldown and are in range, shoot the lowest unit
        SAFETY: int = 2
        LIFE_THRESHOLD: int = 15
        enemy_ground_in_range: Units = self.get_enemy_units_in_range(unit).filter(lambda unit: unit.is_flying == False)
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
                if (enemy_ground_in_range.amount >= 1):
                    # shoot weakest enemy in range
                    target: Unit = enemy_ground_in_range.sorted(lambda u: (u.health + u.shield, u.distance_to_squared(unit))).first
                    unit.attack(target)
                else:
                    # move toward closest enemy to chase
                    unit.attack(enemy_ground.closest_to(unit))

            
            # if we can't safely shoot, move away
            else:
                # safest_spot is preferably away from threats
                closest_enemy: Unit = enemy_ground.closest_to(unit)
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, closest_enemy)
                unit.move(safest_spot)
        
       # --- CASE 2: Long cooldown → retreat & wait ---
        else:
            closest_enemy: Unit = enemy_ground.closest_to(unit)
            if (threats.amount >= 1):
                safest_spot: Point2 = self.bot.map.influence_maps.safest_spot_away(unit, closest_enemy)
                unit.move(safest_spot)
            else:
                best_attacking_spot: Point2 = self.bot.map.influence_maps.best_attacking_spot(unit, closest_enemy, risk=1)
                unit.move(best_attacking_spot)

    @override
    async def harass(self, unit: Unit, local_units: Units, workers: Units):
        # calculate the range of the unit based on its movement speed + range + cooldown
        closest_worker: Unit = workers.closest_to(unit)
        worker_potential_targets: Units = self.get_potential_targets(unit).sorted(
            lambda worker: ((worker.health + worker.shield), worker.distance_to(unit))
        )
        
        # first case : we're dangerously close to a worker => retreat to a safer spot
        if (workers.closest_distance_to(unit) <= 1.5):
            default_retreat_spot: Point2 = unit.position.towards(closest_worker, -1)
            retreat_spot: Point2 = (
                default_retreat_spot
                if (self.bot.map.influence_maps.danger.ground_terrain[default_retreat_spot] < 999)
                else self.bot.map.influence_maps.safest_spot_around_point(default_retreat_spot, 2)
            )
            unit.move(retreat_spot)
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