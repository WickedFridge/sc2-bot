from collections import deque
import math
from typing import List, Literal, Optional, Tuple
from sc2.bot_ai import BotAI
from sc2.game_info import Ramp
from sc2.position import Point2
from sc2.unit import Unit

def center(points: List[Point2]) -> Optional[Point2]:
    length: int = points.__len__()
    if (length == 0):
        return None
    x: float = 0
    y: float = 0
    for point in points:
        x += point.x
        y += point.y
    return Point2((x / length, y / length))

def closest_point(unit: Unit, points: List [Point2]) -> Point2:
    closest_point: Point2 = points[0]
    closest_distance: float = math.inf
    for point in points:
        distance: float = unit.distance_to_squared(point)
        if (distance < closest_distance):
            closest_point = point
            closest_distance = distance
    return closest_point

def find_closest_bottom_ramp(bot: BotAI, position: Point2) -> Ramp:
        return _find_closest_ramp(bot, position, "bottom")

def find_closest_top_ramp(bot: BotAI, position: Point2) -> Ramp:
    return _find_closest_ramp(bot, position, "top")

def _find_closest_ramp(bot: BotAI, position: Point2, extremity: Literal["top","bottom"]):
    closest_ramp: Ramp = bot.game_info.map_ramps[0]
    for ramp in bot.game_info.map_ramps:
        match extremity:
            case "top":
                if (ramp.top_center.distance_to(position) < closest_ramp.top_center.distance_to(position)):
                    closest_ramp = ramp
            case "bottom":
                if (ramp.bottom_center.distance_to(position) < closest_ramp.bottom_center.distance_to(position)):
                    closest_ramp = ramp
            case _:
                print("Error : specify top or bottom of the ramp")
    return closest_ramp

def grid_offsets(radius: float, step: float = 1.0, initial_position: Point2 = Point2((0,0))) -> List[Point2]:
    count = int((2 * radius) / step) + 1
    values = [round(-radius + i * step, 10) for i in range(count)]
    offsets = [Point2((dx + initial_position.x, dy + initial_position.y)) for dx in values for dy in values]
    return offsets

def dfs_in_pathing(bot: BotAI, position: Point2, preferred_direction: Point2, radius: int = 1) -> Point2:
    # If already valid, return it
    start_placement_grid: List[Point2] = grid_offsets(radius, initial_position = position)
    if all((bot.in_placement_grid(pos) and bot.in_pathing_grid(pos)) for pos in start_placement_grid):
        return position
    
    # Normalize to get step direction (either -1, 0, or 1)
    step_x = 1 if preferred_direction.x > 0 else -1 if preferred_direction.x < 0 else 0
    step_y = 1 if preferred_direction.y > 0 else -1 if preferred_direction.y < 0 else 0

    # BFS search for the nearest valid point
    search_queue = deque([position])
    visited = set([position])

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
            neighbor_grid: List[Point2] = grid_offsets(radius, initial_position = neighbor)
            if all((bot.in_placement_grid(neighbor_point) and bot.in_pathing_grid(neighbor_point)) for neighbor_point in neighbor_grid):
                return neighbor

            # Otherwise, continue expanding
            search_queue.append(neighbor)

    # If no valid point is found (unlikely), return the original position
    return position