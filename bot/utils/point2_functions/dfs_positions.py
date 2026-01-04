from collections import deque
from typing import List, Optional
from bot.macro.map.map import MapData, get_map
from bot.utils.point2_functions.utils import grid_offsets, points_to_build_addon
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

def valid_building_position(bot: BotAI, center: Point2, unit_type: UnitTypeId, radius: int, has_addon: bool) -> bool:
    points: list[Point2] = grid_offsets(radius, initial_position=center)
    if (has_addon):
        if (not all(valid_position(bot, p, UnitTypeId.TECHREACTOR) for p in points_to_build_addon(center))):
            return False
    return all(valid_position(bot, p, unit_type) for p in points)

def valid_position(bot: BotAI, pos: Point2, unit_type: UnitTypeId) -> bool:
    map: MapData = get_map(bot)
    width, height =map.influence_maps.buildings.occupancy.map.shape
    return (
        pos.x >= 0 and pos.y >= 0
        and pos.x <= width - 1
        and pos.y <= height - 1
        and map.influence_maps.buildings.can_build(pos, unit_type)
        and map.influence_maps.creep.creep_map[pos] == 0
    )

def dfs_in_pathing(bot: BotAI, position: Point2, unit_type: UnitTypeId, preferred_direction: Optional[Point2] = None, radius: int = 1, has_addon: bool = False) -> Point2:
    """ Find a valid buildable position around the given position using BFS.
        The radius in tiles around the position to search for valid buildable positions."""
    
    # If already valid, return it
    if (valid_building_position(bot, position, unit_type, radius, has_addon)):
        return position
    
    if (preferred_direction is None):
        preferred_direction = position

    def biased_directions(current: Point2) -> list[tuple[int, int]]:
        dx = preferred_direction.x - current.x
        dy = preferred_direction.y - current.y

        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0

        directions: list[tuple[int, int]] = []

        if step_x != 0 or step_y != 0:
            directions.append((step_x, step_y))
        if step_x != 0:
            directions.append((step_x, 0))
        if step_y != 0:
            directions.append((0, step_y))

        directions += [(1, 0), (-1, 0), (0, 1), (0, -1)]

        seen = set()
        return [d for d in directions if not (d in seen or seen.add(d))]

    # BFS search for the nearest valid point
    search_queue: deque[Point2] = deque([position])
    visited: set[Point2] = {position}

    while search_queue:
        current = search_queue.popleft()

        for dx, dy in biased_directions(current):
            neighbor = Point2((current.x + dx, current.y + dy))
            
            if (neighbor in visited):
                continue  # Skip already checked locations
            
            visited.add(neighbor)

            # If it's a valid buildable position, return it
            if (valid_building_position(bot, neighbor, unit_type, radius, has_addon)):
                return neighbor

            # Otherwise, continue expanding
            search_queue.append(neighbor)

    # If no valid point is found (unlikely), return the original position
    return position