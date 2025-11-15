from collections import deque
from typing import List
from bot.macro.map.map import MapData, get_map
from bot.utils.point2_functions.utils import grid_offsets, points_to_build_addon
from sc2.bot_ai import BotAI
from sc2.position import Point2


def dfs_in_pathing(bot: BotAI, position: Point2, preferred_direction: Point2, radius: int = 1, has_addon: bool = False) -> Point2:
    """ Find a valid buildable position around the given position using BFS.
        The radius in tiles around the position to search for valid buildable positions."""
    map: MapData = get_map(bot)
    # If already valid, return it
    start_placement_grid: List[Point2] = grid_offsets(radius, initial_position = position)
    if (has_addon):
        start_placement_grid += points_to_build_addon(position)
    if all(
        (
            pos.x >= 0 and pos.y >= 0
            and pos.x <= map.building_grid.width - 1
            and pos.y <= map.building_grid.height - 1
            and bot.in_placement_grid(pos)
            and map.in_building_grid(pos)
        )
        for pos in start_placement_grid
    ):
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
            if (has_addon):
                neighbor_grid += points_to_build_addon(neighbor)
            if all((bot.in_placement_grid(neighbor_point) and map.in_building_grid(neighbor_point)) for neighbor_point in neighbor_grid):
                return neighbor

            # Otherwise, continue expanding
            search_queue.append(neighbor)

    # If no valid point is found (unlikely), return the original position
    return position