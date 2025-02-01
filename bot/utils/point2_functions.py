from typing import List, Optional
from sc2.position import Point2

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