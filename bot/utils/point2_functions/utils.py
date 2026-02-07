import math
from typing import List, Optional
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from sc2.position import Point2
from sc2.unit import Unit

def center(points: List[Point2]) -> Optional[Point2]:
    length: int = len(points)
    if (length == 0):
        return None
    x: float = 0
    y: float = 0
    for point in points:
        x += point.x
        y += point.y
    return Point2((x / length, y / length))

def closest_point(position: Point2, points: list[Point2]) -> Point2:
    closest: Point2 = points[0]
    for point in points:
        if (point._distance_squared(position) < closest._distance_squared(position)):
            closest = point
    return closest

def grid_offsets(radius: float, step: float = 1.0, initial_position: Point2 = Point2((0,0))) -> List[Point2]:
    count = int((2 * radius) / step) + 1
    values = [round(-radius + i * step, 10) for i in range(count)]
    offsets = [Point2((dx + initial_position.x, dy + initial_position.y)) for dx in values for dy in values]
    return offsets


def addon_offset(position: Point2) -> Point2:
    return position + Point2((2.5, -0.5))

def points_to_build_addon(building_position: Point2) -> List[Point2]:
    """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
    addon_position: Point2 = addon_offset(building_position)
    addon_points = [
        (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
    ]
    return addon_points

def sample_tile_path(
    start: Point2,
    end: Point2,
) -> list[Point2]:
    x0, y0 = int(start.x), int(start.y)
    x1, y1 = int(end.x), int(end.y)

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)

    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1

    err = dx - dy

    x, y = x0, y0
    path: list[Point2] = []

    while True:
        path.append(Point2((x, y)))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

    return path

def evaluate_path_debug(
    influence: InfluenceMap,
    path: list[Point2],
) -> tuple[float, float]:
    dangers = [influence[p] for p in path]

    max_danger = max(dangers)
    avg_danger = sum(dangers) / len(dangers)

    return max_danger, avg_danger