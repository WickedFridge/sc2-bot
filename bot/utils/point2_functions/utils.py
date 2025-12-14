import math
from typing import List, Optional
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

def closest_point(unit: Unit, points: List [Point2]) -> Point2:
    closest_point: Point2 = points[0]
    closest_distance: float = math.inf
    for point in points:
        distance: float = unit.distance_to_squared(point)
        if (distance < closest_distance):
            closest_point = point
            closest_distance = distance
    return closest_point

def grid_offsets(radius: float, step: float = 1.0, initial_position: Point2 = Point2((0,0))) -> List[Point2]:
    count = int((2 * radius) / step) + 1
    values = [round(-radius + i * step, 10) for i in range(count)]
    offsets = [Point2((dx + initial_position.x, dy + initial_position.y)) for dx in values for dy in values]
    return offsets


def points_to_build_addon(building_position: Point2) -> List[Point2]:
    """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
    addon_offset: Point2 = Point2((2.5, -0.5))
    addon_position: Point2 = building_position + addon_offset
    addon_points = [
        (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
    ]
    return addon_points