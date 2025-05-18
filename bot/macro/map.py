from __future__ import annotations
from sc2.bot_ai import BotAI
from sc2.position import Point2, Rect

map: MapData | None = None

class MapData:
    bot: BotAI
    top_center: Point2
    bottom_center: Point2
    left_center: Point2
    right_center: Point2
        
    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        
    def initialize(self) -> None:
        playable_area: Rect = self.bot.game_info.playable_area
        center: Point2 = playable_area.center
        bottom_y: float = playable_area.y
        top_y: float = playable_area.top
        left_x: float = playable_area.x
        right_x: float = playable_area.right
        
        self.top_center: Point2 = Point2((center.x, top_y))
        self.bottom_center: Point2 = Point2((center.x, bottom_y))
        self.left_center: Point2 = Point2((left_x, center.y))
        self.right_center: Point2 = Point2((right_x, center.y))

    @property
    def centers(self) -> list[Point2]:
        return [
            self.top_center,
            self.bottom_center,
            self.left_center,
            self.right_center
        ]
    
    def closest_center(self, position: Point2) -> Point2:
        """
        Returns the closest center to the bot's starting location
        """
        return min(self.centers, key=lambda center: center._distance_squared(position))

def get_map(bot: BotAI) -> MapData:
    global map
    if (map is None):
        map = MapData(bot)
    return map