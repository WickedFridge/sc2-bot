from __future__ import annotations
from typing import List
from bot.macro.map.influence_maps.manager import InfluenceMapManager
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Rect

map_data: MapData | None = None

class MapData:
    bot: BotAI
    top_center: Point2
    bottom_center: Point2
    left_center: Point2
    right_center: Point2
    wall_placement: List[Point2] = []
    influence_maps: InfluenceMapManager
        
    def __init__(self, bot: BotAI) -> None:
        self.bot = bot
        self.influence_maps = InfluenceMapManager(bot)
        
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

        # Initialize the wall placement positions
        depots_positions: List[Point2] = list(self.bot.main_base_ramp.corner_depots)
        self.wall_placement = [
            depots_positions[0],
            self.bot.main_base_ramp.barracks_correct_placement,
            depots_positions[1],
        ]

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
    
    def closest_centers(self, position: Point2, amount: int) -> List[Point2]:
        """
        Returns the n closest center to the bot's starting location
        """
        if (amount <= 0):
            return []
        if (amount >= len(self.centers)):
            return self.centers
        return sorted(self.centers, key=lambda center: center._distance_squared(position))[:amount]

def get_map(bot: BotAI) -> MapData:
    global map_data
    if (map_data is None):
        map_data = MapData(bot)
    return map_data