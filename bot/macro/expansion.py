from collections import deque
import math
from typing import List, Optional

from bot.utils.point2_functions import dfs_in_pathing, center, find_closest_bottom_ramp, grid_offsets
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class Expansion:
    bot: BotAI
    position: Point2
    distance_from_main: float
    radius: int = 12

    def __init__(self, bot: BotAI, position: Point2, distance: float) -> None:
        self.bot = bot
        self.position = position
        self.distance_from_main = distance

    @property
    def is_main(self) -> bool:
        return self.position == self.bot.start_location
    
    @property
    def is_taken(self) -> bool:
        townhalls: Units = self.bot.townhalls
        if (townhalls.amount == 0):
            return False
        if (townhalls.closest_distance_to(self.position) == 0):
            return True
        for townhall in townhalls:
            if (townhall.order_target == self.position):
                return True
        return False

    @property
    def cc(self) -> Optional[Unit]:
        if (not self.is_taken):
            return None
        townhalls: Units = self.bot.townhalls
        for townhall in townhalls:
            if (self.position in [townhall.position, townhall.order_target]):
                return townhall
        return None
    
    @property
    def is_defended(self) -> bool:
        bunkers: Units = self.bot.structures(UnitTypeId.BUNKER)
        if (bunkers.amount == 0):
            return False
        return (bunkers.closest_distance_to(self.position) <= 10)
    
    @property
    def bunker_forward_in_pathing(self) -> Point2 | None:
        """Finds the nearest buildable position for a bunker, avoiding the Command Center's hitbox."""

        start: Point2 = self.bunker_forward
        
        # Calculate preferred direction away from CC toward opponent
        opponent_position: Point2 = self.bot.enemy_start_locations[0]
        direction_vector = opponent_position - self.position
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away
        return dfs_in_pathing(self.bot, start, preferred_direction)
        

    @property
    def bunker_forward(self) -> Point2:
        enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
        bunker_position: Point2 = self.position.towards(enemy_spawn, 3).towards(self.bot.start_location, 2)
        return bunker_position.rounded_half
    
    @property
    def bunker_ramp(self) -> Optional[Point2]:
        closest_ramp_bottom: Point2 = find_closest_bottom_ramp(self.bot, self.position).bottom_center
        if (self.position.distance_to(closest_ramp_bottom) >= 15):
            return None
        enemy_spawn: Point2 = self.bot.enemy_start_locations[0]
        bunker_position: Point2 = center([self.position, closest_ramp_bottom])
        if (bunker_position):
            bunker_position = bunker_position.towards(enemy_spawn)
        direction_vector = self.position - closest_ramp_bottom
        preferred_direction = Point2((-direction_vector.x, -direction_vector.y))  # Invert to move away
        return dfs_in_pathing(self.bot, bunker_position.rounded_half, preferred_direction)
    
    @property
    def defending_bunker(self) -> Optional[Unit]:
        if (self.is_defended == False):
            return None
        return self.bot.structures(UnitTypeId.BUNKER).closest_to(self.position)
    
    @property
    def is_scouted(self) -> bool:
        return len(self.unscouted_points) == 0
    
    @property
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
                    if self.bot.state.visibility[point] == 0 and self.bot.in_pathing_grid(point):
                        unscouted.append(point)

        return unscouted
    
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