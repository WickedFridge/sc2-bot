import math
from typing import List
from sc2.position import Point2


def get_intersections(p0: Point2, r0: float, p1: Point2, r1: float) -> List[Point2]:
    return _get_intersections(p0.x, p0.y, r0, p1.x, p1.y, r1)


def _get_intersections(x0: float, y0: float, r0: float, x1: float, y1: float, r1: float) -> List[Point2]:
    # circle 1: (x0, y0), radius r0
    # circle 2: (x1, y1), radius r1

    d = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)

    # non intersecting
    if d > r0 + r1:
        return []
    # One circle within other
    if d < abs(r0 - r1):
        return []
    # coincident circles
    if d == 0 and r0 == r1:
        return []
    else:
        a = (r0**2 - r1**2 + d**2) / (2 * d)
        h = math.sqrt(r0**2 - a**2)
        x2 = x0 + a * (x1 - x0) / d
        y2 = y0 + a * (y1 - y0) / d
        x3 = x2 + h * (y1 - y0) / d
        y3 = y2 - h * (x1 - x0) / d

        x4 = x2 - h * (y1 - y0) / d
        y4 = y2 + h * (x1 - x0) / d

        return [Point2((x3, y3)), Point2((x4, y4))]
