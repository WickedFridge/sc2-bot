from collections import deque
import math
from typing import List, Optional

from bot.macro.map.map import MapData, get_map
from bot.utils.army import Army
from bot.utils.matchup import Matchup, get_matchup
from bot.utils.point2_functions.ramps import find_closest_bottom_ramp
from bot.utils.point2_functions.utils import center, closest_point
from bot.utils.point2_functions.dfs_positions import dfs_in_pathing
from bot.utils.unit_functions import worker_amount_mineral_field, worker_amount_vespene_geyser
from sc2.bot_ai import BotAI
from sc2.cache import CachedClass, custom_cache_once_per_frame
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import hq_types, menacing, worker_types
from functools import cached_property

class Expansion(CachedClass):
    position: Point2
    distance_from_main: float
    radius: int = 12
    last_scouted: float = 0
    _potentially_enemy: bool = False

    def __init__(self, bot: BotAI, position: Point2, distance: float) -> None:
        super().__init__(bot)
        self.position = position
        self.distance_from_main = distance

    @cached_property
    def is_main(self) -> bool:
        return self.position == self.bot.start_location
    
    @custom_cache_once_per_frame
    def is_taken(self) -> bool:
        townhalls: Units = self.bot.townhalls
        if (townhalls.amount == 0):
            return False
        for th in townhalls.not_flying:
            if (th.position == self.position):
                return True
        for townhall in townhalls.flying:
            if (townhall.order_target == self.position):
                return True
        return False
    
    @custom_cache_once_per_frame
    def is_unknown(self) -> bool:
        return self.bot.state.visibility[self.position.rounded] == 0
    
    @custom_cache_once_per_frame
    def is_visible(self) -> bool:
        return self.bot.state.visibility[self.position.rounded] == 2
    
    @custom_cache_once_per_frame
    def is_populated(self) -> bool:
        return self.bot.structures.closest_distance_to(self.position) <= 5
    
    @custom_cache_once_per_frame
    def is_enemy(self) -> bool:
        # if is enemy main unscouted, return True
        if (self.position == self.bot.enemy_start_locations[0] and self.is_unknown):
            return True

        enemy_townhalls: Units = self.bot.enemy_structures.filter(lambda unit : unit.type_id in hq_types)
        return enemy_townhalls.amount > 0 and enemy_townhalls.closest_distance_to(self.position) == 0
    
    @custom_cache_once_per_frame
    def is_ready(self) -> bool:
        return self.is_taken and self.cc.is_ready and not self.cc.is_flying

    @custom_cache_once_per_frame
    def is_safe(self) -> bool:
        # Positions with high HP PF are considered safe
        if (self.cc and self.cc.type_id == UnitTypeId.PLANETARYFORTRESS and self.cc.health_percentage >= 0.6):
            return True

        local_enemy_units: Units = self.bot.enemy_units.closer_than(8, self.position).filter(
            lambda unit: unit.can_attack_ground or unit.type_id in menacing
        )
        local_enemy_ground_units: Units = local_enemy_units.filter(lambda unit: not unit.is_flying)
        local_enemy_air_units: Units = local_enemy_units.filter(lambda unit: unit.is_flying)
        
        local_units: Units = self.bot.units.closer_than(8, self.position).filter(
            lambda unit: (
                unit.type_id not in worker_types
                and (unit.can_attack or unit.type_id in menacing)
            )
        )
        local_anti_ground_units: Units = local_units.filter(lambda unit: unit.can_attack_ground)
        local_anti_air_units: Units = local_units.filter(lambda unit: unit.can_attack_air)

        if (self.defending_structure and self.defending_structure.cargo_used >= 1):
            local_anti_ground_units.append(self.defending_structure)
        
        return (
            Army(local_anti_ground_units, self.bot).weighted_supply >= Army(local_enemy_ground_units, self.bot).weighted_supply
            and Army(local_anti_air_units, self.bot).weighted_supply >= Army(local_enemy_air_units, self.bot).weighted_supply
        )

    @custom_cache_once_per_frame
    def cc(self) -> Optional[Unit]:
        if (not self.is_taken):
            return None
        townhalls: Units = self.bot.townhalls
        for townhall in townhalls:
            if (self.position in [townhall.position, townhall.order_target]):
                return townhall
        return None
    
    @custom_cache_once_per_frame
    def mineral_fields(self) -> Units:
        return self.bot.mineral_field.closer_than(10, self.position)
    
    @custom_cache_once_per_frame
    def refineries(self) -> Units:
        return self.bot.structures(UnitTypeId.REFINERY).ready.closer_than(10, self.position).filter(
            lambda refinery: self.bot.vespene_geyser.filter(
                lambda unit: unit.position == refinery.position and unit.has_vespene
            ).amount == 1
        )
    
    @custom_cache_once_per_frame
    def vespene_geysers(self) -> Units:
        return self.bot.vespene_geyser.closer_than(10, self.position)
    
    @custom_cache_once_per_frame
    def vespene_geysers_refinery(self) -> Units:
        return self.bot.vespene_geyser.filter(
            lambda geyser: geyser.has_vespene and self.bot.structures(UnitTypeId.REFINERY).ready.closer_than(10, self.position).filter(
                lambda refinery: refinery.position == geyser.position
            ).amount == 1
        )
    
    @custom_cache_once_per_frame
    def minerals(self) -> int:
        minerals: int = 0
        for mf in self.mineral_fields:
            minerals += mf.mineral_contents
        return minerals
    
    @custom_cache_once_per_frame
    def vespene(self) -> int:
        vespene: int = 0
        for vg in self.vespene_geysers_refinery:
            vespene += vg.vespene_contents
        return vespene

    @custom_cache_once_per_frame
    def mineral_workers(self) -> Units:
        if (self.mineral_fields.amount == 0):
            return Units([], self.bot)
        return self.bot.workers.filter(
            lambda worker: (
                worker.order_target in self.mineral_fields.tags
                or (worker.is_returning and worker.distance_to(self.position) <= 8)
                or (
                    worker.is_moving
                    and isinstance(worker.order_target, Point2)
                    and worker.order_target.distance_to(self.mineral_line) <= 5
                )
            )
        )
    
    @custom_cache_once_per_frame
    def vespene_workers(self) -> Units:
        return self.bot.workers.closer_than(10, self.position).filter(
            lambda worker: (
                worker.is_carrying_vespene
                or worker.order_target in self.refineries.tags
            )
        )

    @custom_cache_once_per_frame
    def mineral_worker_count(self) -> int:
        return self.mineral_workers.amount

    @custom_cache_once_per_frame
    def vespene_worker_count(self) -> int:
        return sum(refinery.assigned_harvesters for refinery in self.refineries)
    
    @custom_cache_once_per_frame
    def optimal_mineral_workers(self) -> float:
        if self.mineral_fields.amount == 0:
            return 0
        return sum(worker_amount_mineral_field(mf.mineral_contents) for mf in self.mineral_fields)

    @custom_cache_once_per_frame
    def optimal_vespene_workers(self) -> float:
        if self.refineries.amount == 0:
            return 0
        return sum(worker_amount_vespene_geyser(vg.vespene_contents) for vg in self.vespene_geysers_refinery)

    @custom_cache_once_per_frame
    def mineral_saturation(self) -> float:
        if (self.optimal_mineral_workers == 0):
            return -1
        return self.mineral_worker_count / self.optimal_mineral_workers

    @custom_cache_once_per_frame
    def vespene_saturation(self) -> float:
        if (self.optimal_vespene_workers == 0):
            return -1
        return self.vespene_worker_count / self.optimal_vespene_workers

    @custom_cache_once_per_frame
    def desired_vespene_saturation(self) -> float:
        """
        Returns desired gas saturation between 0 and 1 based on mineral saturation:
        - 0 when mineral saturation <= 0.5
        - 1 when mineral saturation >= 0.75
        - Linear in-between
        """
        ms: float = self.mineral_saturation

        if (ms <= 0.5):
            return 0
        if (ms >= 0.75):
            return 1
        # Linear interpolation
        saturation: float = (ms - 0.5) / 0.25
        saturation = min(1.0, max(0.0, saturation))

        # Deprioritize gas if floating too much
        if self.bot.vespene >= 200 and self.bot.minerals <= 800:
            saturation *= 0.5  # or 0 if you want hard stop

        return saturation
    
    @cached_property
    def mineral_line(self) -> Point2:
        resources: Units = self.mineral_fields + self.vespene_geysers
        if (resources.amount == 0):
            return self.position.towards(self.bot.game_info.map_center, 5)
        return resources.center

    @custom_cache_once_per_frame
    def is_defended(self) -> bool:
        defenses: Units = self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready
        if (defenses.amount == 0):
            return False
        return (defenses.closest_distance_to(self.position) <= 12)
    
    @custom_cache_once_per_frame
    def detects(self) -> bool:
        turrets: Units = self.bot.structures(UnitTypeId.MISSILETURRET).ready
        if (turrets.amount == 0):
            return False
        return (turrets.closest_distance_to(self.position) <= 12)
    
    @custom_cache_once_per_frame
    def retreat_position(self) -> Point2:
        if (self.is_main):
            return self.bot.main_base_ramp.barracks_correct_placement
        if (self.is_defended and self.mineral_fields.amount >= 1):
            reference_position: Point2 = self.mineral_fields.closest_to(self.defending_structure).position
            return center([reference_position, self.defending_structure.position])
        position: Point2 = self.bunker_ramp or self.bunker_forward
        return center([position, self.mineral_line])
    
    @custom_cache_once_per_frame
    def bunker_forward_in_pathing(self) -> Point2 | None:
        """Finds the nearest buildable position for a bunker, avoiding the Command Center's hitbox."""

        start: Point2 = self.bunker_forward
        
        # Calculate preferred direction away from CC toward opponent
        opponent_position: Point2 = self.bot.enemy_start_locations[0]
        # direction_vector = opponent_position - self.position
        # preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away
        return dfs_in_pathing(self.bot, start, UnitTypeId.BUNKER, opponent_position)

    @cached_property
    def bunker_forward(self) -> Point2:
        enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
        bunker_position: Point2 = self.position.towards(enemy_spawn, 3)
        return bunker_position.rounded_half
    
    @custom_cache_once_per_frame
    def bunker_ramp(self) -> Optional[Point2]:
        if (self.is_main == True):
            # prefered_position: Point2 = self.bot.main_base_ramp.top_center
            depot_walls: List[Point2] = list(self.bot.main_base_ramp.corner_depots)
            closest_depot_wall: Point2 = closest_point(self.position, depot_walls)
            return dfs_in_pathing(self.bot, closest_depot_wall, UnitTypeId.BUNKER, self.position, radius=1)
        closest_ramp_bottom: Point2 = find_closest_bottom_ramp(self.bot, self.position).bottom_center
        if (self.position.distance_to(closest_ramp_bottom) >= 15):
            return None
        enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
        bunker_position: Point2 = center([self.position, closest_ramp_bottom])
        if (bunker_position):
            bunker_position = bunker_position.towards(enemy_spawn)
        direction_vector = self.position - closest_ramp_bottom
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away
        return dfs_in_pathing(self.bot, bunker_position.rounded_half, UnitTypeId.BUNKER, preferred_direction)
    
    @custom_cache_once_per_frame
    def bunker_position(self) -> Point2:
        if (self.is_main):
            return self.bunker_ramp
        return self.bunker_forward_in_pathing
        # matchup: Matchup = get_matchup(self.bot)
        # bunker_position: Point2 = (
        #     self.bunker_ramp
        #     if matchup == Matchup.TvZ and self.bunker_ramp is not None
        #     else self.bunker_forward_in_pathing
        # )
        # return bunker_position
    
    @custom_cache_once_per_frame
    def defending_structure(self) -> Optional[Unit]:
        if (self.is_defended == False):
            return None
        return self.bot.structures([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]).ready.closest_to(self.position)
    
    @custom_cache_once_per_frame
    def is_scouted(self) -> bool:
        return len(self.unscouted_points) == 0
    
    @custom_cache_once_per_frame
    def unscouted_points(self) -> List[Point2]:
        # Returns a list of all unscouted points within a circle of radius around the position
        radius: int = self.radius
        unscouted: List[Point2] = []

        # Iterate over the bounding square of the circle
        for x in range(int(self.position.x) - radius, int(self.position.x) + radius + 1):
            for y in range(int(self.position.y) - radius, int(self.position.y) + radius + 1):
                # Check if the point lies within the circle
                if math.sqrt((x - self.position.x)**2 + (y - self.position.y)**2) <= radius:
                    point = Point2((x, y))
                    # Unscouted
                    if (
                        self.bot.state.visibility[point] == 0
                        and self.bot.in_pathing_grid(point)
                        and self.bot.get_terrain_z_height(point) == self.bot.get_terrain_z_height(self.position)
                    ):
                        unscouted.append(point)

        return unscouted
    
    @custom_cache_once_per_frame
    def is_potentially_enemy(self):
        """
        Updated each frame with suspicions of base taken
        """
        if (self.is_enemy):
            self._potentially_enemy = True
        elif (self.is_taken):
            self._potentially_enemy = False
        elif (self.is_visible):
            self._potentially_enemy = False
        return self._potentially_enemy
    
    def in_pathing(self, target: Point2) -> Point2:
        # Convert target to the nearest grid-aligned integer point
        start = Point2((round(target.x), round(target.y)))

        # If already valid, return it
        if self.bot.in_placement_grid(start):
            return start
        
        # Calculate preferred direction away from CC toward opponent
        opponent_position: Point2 = self.bot.enemy_start_locations[0]
        direction_vector = opponent_position - self.position
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away

        # Normalize to get step direction (either -1, 0, or 1)
        step_x = 1 if preferred_direction.x > 0 else -1 if preferred_direction.x < 0 else 0
        step_y = 1 if preferred_direction.y > 0 else -1 if preferred_direction.y < 0 else 0

        # BFS search for the nearest valid point
        search_queue = deque([start])
        visited = set([start])

        # Prioritized search directions (biased away from CC)
        directions = [(step_x, step_y)]  # Move in the preferred direction first
        directions += [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Then check standard directions

        while search_queue:
            current = search_queue.popleft()

            for dx, dy in directions:
                neighbor = Point2((current.x + dx, current.y + dy))
                
                if neighbor in visited:
                    continue  # Skip already checked locations
                
                visited.add(neighbor)

                # If it's a valid buildable position, return it
                if self.bot.in_placement_grid(neighbor):
                    return neighbor

                # Otherwise, continue expanding
                search_queue.append(neighbor)

        # If no valid point is found (unlikely), return the original position
        return start
    
    def update_scout_status(self):
        if (self.bot.state.visibility[self.position.rounded] == 2):
            self.last_scouted = self.bot.time

        # suspect that bases around creep are taken
        map: MapData = get_map(self.bot)
        EXPANSION_SUSPECTED_THRESHOLD: int = 10
        ASSUME_DELAY: float = 20
        creep_distance: float = map.influence_maps.creep.distance_to_creep[self.position]
        if (
            not self.is_visible
            and self.last_scouted + ASSUME_DELAY < self.bot.time
            and creep_distance < EXPANSION_SUSPECTED_THRESHOLD
        ):
            self._potentially_enemy = True