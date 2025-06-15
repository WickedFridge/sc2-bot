from __future__ import annotations
import math
from typing import List, Union
from sc2.bot_ai import BotAI
from sc2.pixel_map import PixelMap
from sc2.position import Point2, Rect
from sc2.unit import Unit
from sc2.units import Units

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
        self.building_grid = self.bot.game_info.placement_grid.copy()
        for unit in self.bot.destructables:
            print(f'destructible : {unit.type_id} [{unit.position}] ({unit.radius} / {unit.footprint_radius})')
            self._clear_building_grid_for_unit(unit, round(unit.radius * 2))

        for structure in self.bot.structures:
            print(f'structure : {structure.type_id} [{structure.position}] ({structure.radius} / {structure.footprint_radius})')
            self._clear_building_grid_for_unit(structure, structure.footprint_radius * 2)

        for expansion in self.bot.expansion_locations_list:
            minerals: Units = self.bot.mineral_field.closer_than(10, expansion)
            vespene_geysers: Units = self.bot.vespene_geyser.closer_than(10, expansion)
            # clear the building grid for the expansion
            for mineral in minerals + vespene_geysers:
                selected_positions: List[Point2] = [expansion, mineral.position]
                # draw the pathing grid between the two selected units
                
                min_x, max_x = sorted([pos.x for pos in selected_positions])
                min_y, max_y = sorted([pos.y for pos in selected_positions])

                start_x = math.ceil(min_x) - 0.5
                end_x = math.floor(max_x) + 0.5
                start_y = math.ceil(min_y) - 0.5
                end_y = math.floor(max_y) + 0.5

                x = start_x
                while x <= end_x:
                    y = start_y
                    while y <= end_y:
                        self.building_grid[Point2((x, y)).rounded] = 0
                        y += 1.0
                    x += 1.0
            self._clear_building_grid_for_unit(expansion, 5, enable=True)
            

    
    def update_building_grid(self, unit: Unit) -> None:
        self._clear_building_grid_for_unit(unit, unit.footprint_radius * 2)
    
    def _clear_building_grid_for_unit(self, unit: Unit | Point2, footprint_size: float, enable: bool = False) -> None:
        """Clears building grid for all tiles covered by a destructible unit of a given footprint size (e.g., 2, 6)."""
        half = footprint_size / 2
        position: Point2 = unit.position
        min_x = int(position.x - half)
        min_y = int(position.y - half)

        for dx in range(int(footprint_size)):
            for dy in range(int(footprint_size)):
                point = Point2((min_x + dx, min_y + dy)).rounded
                self.building_grid[point] = 0 if not enable else 1
    
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