from __future__ import annotations
import math
from typing import List, Union
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.pixel_map import PixelMap
from sc2.position import Point2, Rect
from sc2.unit import Unit
from sc2.units import Units
from bot.utils.unit_tags import add_ons

map_data: MapData | None = None

class MapData:
    bot: BotAI
    top_center: Point2
    bottom_center: Point2
    left_center: Point2
    right_center: Point2
    building_grid: PixelMap
    wall_placement: List[Point2] = []
        
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

        # Initialize the wall placement positions
        depots_positions: List[Point2] = list(self.bot.main_base_ramp.corner_depots)
        self.wall_placement = [
            depots_positions[0],
            self.bot.main_base_ramp.barracks_correct_placement,
            depots_positions[1],
        ]
    
    def initialize_building_grid(self) -> None:
        """
        Initializes the building grid from the game info.
        This should be called after the game info is available.
        """
        self.building_grid = self.bot.game_info.placement_grid.copy()
        # Setup the building grid for the bases
        # Mineral line shouldn't be buildable but expansions should be

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
            self._update_building_grid_for_unit(expansion, 5, enable=True)

        for structure in self.bot.structures:
            print(f'structure : {structure.type_id} [{structure.position}] ({structure.radius} / {structure.footprint_radius})')
            self._update_building_grid_for_unit(structure, structure.footprint_radius * 2)
    
        for unit in self.bot.destructables:
            print(f'destructible : {unit.type_id} [{unit.position}] ({unit.radius} / {unit.footprint_radius})')
            if (unit.radius == 0):
                continue
            self._update_building_grid_for_unit(unit, unit.radius * 2)

    
    def update_building_grid(self, unit: Unit, enable: bool = False) -> None:
        # print(f'update building grid for {unit.type_id} [{unit.position}] ({unit.radius} / {unit.footprint_radius})')
        radius = unit.footprint_radius if unit.footprint_radius is not None and unit.footprint_radius > 0 else unit.radius
        # Flyingtownhalls have a footprint radius of 0, so we use 2.5 instead.
        if (unit.type_id in [UnitTypeId.COMMANDCENTERFLYING, UnitTypeId.ORBITALCOMMANDFLYING]):
            radius = 2.5
        # Addons have a footprint radius of 3.5, so we use 1 instead.
        if (unit.type_id in add_ons):
            radius = 1
        self._update_building_grid_for_unit(unit, radius * 2, enable)
    
    def _update_building_grid_for_unit(self, pos: Union[Point2, Unit], footprint_size: float, enable: bool = False) -> None:
        """Clears building grid for all tiles covered by a destructible unit of a given footprint size (e.g., 2, 6)."""
        assert footprint_size > 0, "footprint_size must be greater than 0"
        half = round(footprint_size) / 2
        print(f'footprint_size % 2: {footprint_size % 2}')
        position: Point2 = pos.position.rounded if footprint_size % 2 == 0 else pos.position.rounded_half
        assert isinstance(position, Point2), "unit.position is not of type Point2"
        min_x = int(position.x - half)
        min_y = int(position.y - half)

        for dx in range(int(footprint_size)):
            for dy in range(int(footprint_size)):
                point = Point2((min_x + dx, min_y + dy)).rounded
                # self.building_grid[point] = 0 if not enable else 2
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
    
    async def update(self):
        """
        Updates the map data.
        This should be called every step to update the map data in case a CC is either flying or landing.
        """
        townhalls: Units = self.bot.townhalls
        for townhall in townhalls:
            if (townhall.is_using_ability(AbilityId.LIFT)):
                self.update_building_grid(townhall, enable=True)
            elif(townhall.is_using_ability(AbilityId.LAND) and townhall.is_flying == False):
                self.update_building_grid(townhall, enable=False)
            

def get_map(bot: BotAI) -> MapData:
    global map_data
    if (map_data is None):
        map_data = MapData(bot)
    return map_data