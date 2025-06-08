from __future__ import annotations
from typing import Union
from sc2.bot_ai import BotAI
from sc2.pixel_map import PixelMap
from sc2.position import Point2, Rect
from sc2.unit import Unit

map_data: MapData | None = None

class MapData:
    bot: BotAI
    top_center: Point2
    bottom_center: Point2
    left_center: Point2
    right_center: Point2
    building_grid: PixelMap
        
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
        self.initialize_building_grid()
    
    def initialize_building_grid(self) -> None:
        """
        Initializes the building grid from the game info.
        This should be called after the game info is available.
        """
        self.building_grid = self.bot.game_info.placement_grid
        for unit in self.bot.destructables:
            print(f'destructible : {unit.type_id} [{unit.position}] ({unit.radius} / {unit.footprint_radius})')
            self._clear_building_grid_for_unit(unit, round(unit.radius * 2))
        
    
    def _clear_building_grid_for_unit(self, unit: Unit, footprint_size: int):
        """Clears building grid for all tiles covered by a destructible unit of a given footprint size (e.g., 2, 6)."""
        half = footprint_size / 2
        min_x = int(unit.position.x - half)
        min_y = int(unit.position.y - half)

        for dx in range(footprint_size):
            for dy in range(footprint_size):
                point = Point2((min_x + dx, min_y + dy)).rounded
                self.building_grid[point] = 0
    
    @property
    def centers(self) -> list[Point2]:
        return [
            self.top_center,
            self.bottom_center,
            self.left_center,
            self.right_center
        ]
    
    def in_building_grid(self, pos: Union[Point2, Unit]) -> bool:
        """Returns True if a building could be built on this position.
        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.building_grid[pos] == 1 and self.bot.in_pathing_grid(pos) and self.bot.in_placement_grid(pos)
    
    def closest_center(self, position: Point2) -> Point2:
        """
        Returns the closest center to the bot's starting location
        """
        return min(self.centers, key=lambda center: center._distance_squared(position))

def get_map(bot: BotAI) -> MapData:
    global map_data
    if (map_data is None):
        map_data = MapData(bot)
    return map_data