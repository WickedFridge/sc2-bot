import math
from typing import List, Optional
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
                    if self.bot.state.visibility[point] == 0:  # Unscouted
                        unscouted.append(point)

        return unscouted