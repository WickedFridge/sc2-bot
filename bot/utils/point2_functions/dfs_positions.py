from collections import deque
from typing import List, Optional
from bot.macro.map.influence_maps.layers.buildings_layer import ADDON_RADIUS
from bot.macro.map.map import MapData, get_map
from bot.utils.point2_functions.utils import addon_offset
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

def valid_building_position(bot: BotAI, position: Point2, unit_type: UnitTypeId, radius: float, has_addon: bool) -> bool:
    map: MapData = get_map(bot)
    if (
        has_addon
        and not map.influence_maps.buildings.should_build_building(addon_offset(position), UnitTypeId.BARRACKSTECHLAB, ADDON_RADIUS)
    ):
        return False
    should_build: bool = map.influence_maps.buildings.should_build_building(position, unit_type, radius)    
    return should_build

def dfs_in_pathing(bot: BotAI, position: Point2, unit_type: UnitTypeId, preferred_direction: Optional[Point2] = None, radius: float = 1.5, has_addon: bool = False) -> Point2:
    """ Find a valid buildable position around the given position using BFS.
        The radius in tiles around the position to search for valid buildable positions."""
    size: int = int(round(radius * 2))
    
    def normalize(p: Point2) -> Point2:
        # Odd size (3x3, 5x5) → rounded_half, Even size (2x2) → rounded
        return p.rounded_half if (size % 2 != 0) else p.rounded

    position = normalize(position)


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
            neighbor = normalize(Point2((current.x + dx, current.y + dy)))
            
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