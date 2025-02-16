import math
from typing import List, Optional
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
