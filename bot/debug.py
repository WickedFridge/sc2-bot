import math
from typing import List, Optional
from bot.army_composition.composition import Composition
from bot.macro.expansion import Expansion
from bot.superbot import Superbot
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, ORANGE, PURPLE, RED, WHITE, YELLOW
from bot.utils.point2_functions import grid_offsets
from bot.utils.unit_functions import find_by_tag
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units


class Debug:
    bot: Superbot
    rush_started: bool = False
    
    def __init__(self, bot: Superbot) -> None:
        self.bot = bot

    def draw_sphere_on_world(self, pos: Point2, radius: float = 2, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_sphere_out(
            Point3((pos.x, pos.y, z_height)), 
            radius, color=draw_color
        )

    def draw_flying_box(self, pos: Point2, size: float = 0.25, draw_color: tuple = (255, 0, 0)):
        self.bot.client.debug_box2_out(
            Point3((pos.x, pos.y, 5)),
            size,
            draw_color,
        )
    
    def draw_box_on_world(self, pos: Point2, size: float = 0.25, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_box2_out(
            Point3((pos.x, pos.y, z_height-0.45)),
            size,
            draw_color,
        )

    def draw_grid_on_world(self, pos: Point2, size: int = 3, text: str = ""):
        # if the grid is even, a 2x2 should be rounded first
        point_positions: List[Point2] = []
        self.draw_text_on_world(pos.rounded_half, text, font_size=10)
        match(size):
            case 2:
                point_positions = grid_offsets(0.5, initial_position = pos.rounded)
            case 3:
                point_positions = grid_offsets(1, initial_position = pos.rounded_half)
            case 5:
                point_positions = grid_offsets(2, initial_position = pos.rounded_half)
        for i, point_position in enumerate(point_positions):
            draw_color = GREEN if (self.bot.map.in_building_grid(point_position)) else RED
            self.draw_box_on_world(point_position, 0.5, draw_color)
            self.draw_text_on_world(point_position, f'{i}', draw_color, 10)


    def draw_text_on_world(self, pos: Point2, text: str, draw_color: tuple = (255, 102, 255), font_size: int = 14) -> None:
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_text_world(
            text,
            Point3((pos.x, pos.y, z_height)),
            color=draw_color,
            size=font_size,
        )

    def draw_text_on_screen(self, text: str, pos: Point2 = Point2((0.01, 0.01)), draw_color: tuple = WHITE, font_size: int = 12) -> None:
        self.bot.client.debug_text_screen(
            text,
            pos,
            color=draw_color,
            size=font_size,
        )


    async def colorize_bunkers(self):
        for bunker in self.bot.structures(UnitTypeId.BUNKER).ready:
            enemy_units_in_sight: Units = self.bot.enemy_units.filter(
                lambda unit: unit.distance_to(bunker) <= 11
            )
            if (enemy_units_in_sight.amount == 0):
                self.draw_sphere_on_world(bunker.position, radius=7, draw_color=GREEN)
                self.draw_text_on_world(bunker.position, "No unit detected", GREEN)
                return
            if (bunker.cargo_left == 0):
                self.draw_sphere_on_world(bunker.position, radius=7, draw_color=WHITE)
                self.draw_text_on_world(bunker.position, "Bunker Full", WHITE)
                return
            bio_close_by: Units = self.bot.units.filter(
                lambda unit: unit.type_id in bin and unit.distance_to(bunker) <= 10
            )
            if (bio_close_by.amount == 0):
                self.draw_sphere_on_world(bunker.position, radius=7, draw_color=RED)
                self.draw_text_on_world(bunker.position, "No ally unit closeby", RED)
                return
            bio_in_range: List[Unit] = bio_close_by.filter(lambda unit: unit.distance_to(bunker) <= 3)[:4]
            if (bio_in_range.__len__() == 0):
                bio_close_by.sort(key = lambda unit: unit.distance_to(bunker))
                bio_moving_towards_bunker: List[Unit] = bio_close_by.copy()[:4]
                for bio_unit in bio_moving_towards_bunker:
                    self.draw_sphere_on_world(bio_unit.position, draw_color=BLUE)
                    self.draw_text_on_world(bio_unit.position, "moving towards bunker", draw_color=BLUE)
                    self.draw_sphere_on_world(bunker.position, radius=7, draw_color=BLUE)
                    self.draw_text_on_world(bunker.position, "Units closeby", BLUE)
                    return
                
    async def drop_path(self):
        for center in self.bot.map.centers:
            self.draw_flying_box(center, 5)

    async def unscouted_b2(self):
        for point in self.bot.expansions.b2.unscouted_points:
            center: Point2 = Point2((point.x + 0.5, point.y + 0.5))
            self.draw_box_on_world(center, 0.5)

    async def bases_content(self):
        for expansion in self.bot.expansions.taken:
            below_expansion_point: Point2 = Point2((expansion.position.x, expansion.position.y - 0.5))
            self.draw_text_on_world(expansion.position, f'[{expansion.mineral_worker_count}/{expansion.optimal_mineral_workers.__round__(1)}] Minerals', LIGHTBLUE)
            self.draw_text_on_world(below_expansion_point, f'[{expansion.vespene_worker_count}/{expansion.optimal_vespene_workers.__round__(1)}] Gas[{expansion.vespene_geysers_refinery.amount}]', GREEN)

    async def bases_bunkers(self):
        for expansion in self.bot.expansions.taken:
            below_expansion_point: Point2 = Point2((expansion.position.x, expansion.position.y - 0.5))
            self.draw_text_on_world(expansion.position, f'defended [{expansion.is_defended}]', LIGHTBLUE)
            defending_bunker: Unit = expansion.defending_bunker
            if (defending_bunker):
                self.draw_text_on_world(below_expansion_point, f'[{defending_bunker.position}]', GREEN)
                self.draw_grid_on_world(defending_bunker.position, 3, "Bunker")

    async def bases_distance(self):
        last_expansion: Expansion = self.bot.expansions.last_taken
        for expansion in self.bot.expansions.taken:
            is_last: bool = last_expansion and expansion.position == last_expansion.position
            text: str = f'[LAST : {is_last}] : {expansion.distance_from_main}'
            self.draw_text_on_world(expansion.position, text)

    async def selection(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        # for unit in selected_units:
        #     print(f'Selected unit: {unit.name}')
        #     print(f'is dropping: {unit.is_using_ability(AbilityId.UNLOADALLAT_MEDIVAC)}')
        #     print(f'unit buffs: {unit.buffs}')
        
        selected_positions: List[Point2] = []
        for unit in selected_units:
            buildable: bool = self.bot.map.in_building_grid(unit.position)
            color: tuple = GREEN if buildable else RED
            self.draw_box_on_world(unit.position, 0.5, color)
            selected_positions.append(unit.position)
        if (selected_units.amount == 2):
            # draw the pathing grid between the two selected units
            
            min_x, max_x = sorted([pos.x for pos in selected_positions])
            min_y, max_y = sorted([pos.y for pos in selected_positions])

            start_x = math.ceil(min_x) - 0.5
            end_x = math.floor(max_x) + 0.5
            start_y = math.ceil(min_y) - 0.5
            end_y = math.floor(max_y) + 0.5

            x = start_x
            while (x <= end_x):
                y = start_y
                while (y <= end_y):
                    color = GREEN if self.bot.map.in_building_grid(Point2((x, y))) else RED
                    self.draw_box_on_world(Point2((x, y)), 0.5, color)
                    y += 1.0
                x += 1.0
            
        for unit in selected_units:
            buff_count: int = len(unit.buffs)
            self.draw_text_on_world(unit.position, f'{unit.name} : {buff_count} buffs')
            
            for i, buff in enumerate(unit.buffs):
                self.draw_text_on_world(Point2((unit.position.x, unit.position.y + 2 * i)), f'Buff : {buff.name}')
            
            # draw target
            if (unit.is_idle):
                break
            target: int|Point2 = unit.orders[0].target
            if (target is Point2):
                self.draw_box_on_world(target)
            else:
                # find target unit
                target_unit: Unit = find_by_tag(self.bot, target)
                if (target_unit):
                    self.draw_box_on_world(target_unit.position)

    async def invisible_units(self):
        invisible_units: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: (
                unit.is_visible
                and (unit.is_burrowed or unit.is_cloaked)
            )
        )
        for unit in invisible_units:
            self.draw_sphere_on_world(unit.position, radius=1, draw_color=YELLOW)
            self.draw_text_on_world(unit.position, f'{unit.type_id.name} [{unit.health}/{unit.health_max}]', YELLOW)

    
    async def loaded_stuff(self, iteration: int):
        if (iteration % 10 != 0):
            return
        print("units amount: ", self.bot.units.amount)
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            if (unit.has_cargo):
                passengers: Units = Units(unit.passengers, self.bot)
                print("loaded units: ", passengers)


    async def bunker_positions(self):
        for expansion in self.bot.expansions:
            bunker_forward_in_pathing: Optional[Point2] = expansion.bunker_forward_in_pathing
            bunker_ramp: Optional[Point2] = expansion.bunker_ramp
            if (expansion.is_defended or expansion.is_main):
                continue
            if (bunker_forward_in_pathing):
                self.draw_grid_on_world(bunker_forward_in_pathing, 3, "forward in pathing")
            if (bunker_ramp):
                self.draw_grid_on_world(bunker_ramp, 3, "ramp")
            
    async def wall_placement(self):
        self.draw_grid_on_world(self.bot.map.wall_placement[0], 2, "Depot")
        self.draw_grid_on_world(self.bot.map.wall_placement[1], 3, "Barracks")
        self.draw_grid_on_world(self.bot.map.wall_placement[2], 2, "Depot")
        # self.draw_grid_on_world(self.bot.main_base_ramp.barracks_correct_placement, 3, "Barracks")

    async def pathing_grid(self):
        radius: float = 12
        position: Point2 = self.bot.expansions.main.position
        # Iterate over the bounding square of the circle
        for x in range(int(position.x) - radius, int(position.x) + radius + 1):
            for y in range(int(position.y) - radius, int(position.y) + radius + 1):
                # Check if the point lies within the circle
                if math.sqrt((x - position.x)**2 + (y - position.y)**2) <= radius:
                    point = Point2((x, y))
                    if (not self.bot.in_pathing_grid(point)):
                        center: Point2 = Point2((point.x + 0.5, point.y + 0.5))
                        self.draw_box_on_world(center, 0.5, RED)                    

    async def placement_grid(self):
        radius: float = 12
        position: Point2 = self.bot.expansions.main.position
        # Iterate over the bounding square of the circle
        for x in range(int(position.x) - radius, int(position.x) + radius + 1):
            for y in range(int(position.y) - radius, int(position.y) + radius + 1):
                # Check if the point lies within the circle
                if math.sqrt((x - position.x)**2 + (y - position.y)**2) <= radius:
                    point = Point2((x, y))
                    if (not self.bot.in_placement_grid(point)):
                        center: Point2 = Point2((point.x + 0.5, point.y + 0.5))
                        self.draw_box_on_world(center, 0.5, PURPLE)

    async def building_grid(self):
        radius: float = 10
        positions: List[Point2] = self.bot.expansions.positions + [structure.position for structure in self.bot.structures]
        for position in positions:
            for x in range(int(position.x) - radius, int(position.x) + radius + 1):
                for y in range(int(position.y) - radius, int(position.y) + radius + 1):
                    # Check if the point lies within the circle
                    if math.sqrt((x - position.x)**2 + (y - position.y)**2) <= radius:
                        point = Point2((x, y))
                        if (not self.bot.map.in_building_grid(point)):
                            center: Point2 = Point2((point.x + 0.5, point.y + 0.5))
                            self.draw_box_on_world(center, 0.5, RED)

    def parse_unit_type(self, name: str) -> UnitTypeId | None:
        try:
            # normalize to uppercase, remove spaces if needed
            return UnitTypeId[name.upper()]
        except KeyError:
            return None

    async def _create_units(
        self,
        amount: int,
        unit_id: UnitTypeId,
        player_id: int = 1,
    ) -> None:  # pragma: no cover
        """Create units at player camera location.

        Parameters
        ----------
        amount :
            Number of units to create
        unit_id :
            What type of unit to create
        player_id :
            Which player should be controlling the unit

        Returns
        -------

        """

        player_camera = self.bot.state.observation_raw.player.camera
        pos = Point2((player_camera.x, player_camera.y))
        await self.bot.client.debug_create_unit([[unit_id, amount, pos, player_id]])

    async def spawn_test_units(self):
        if (len(self.bot.state.chat) == 1 and self.bot.state.chat[0].player_id == self.bot.player_id):
            message: str = self.bot.state.chat[0].message
            if (message.startswith("Tag:")):
                return

            parts = message.split(" ", 2)  # split into at most 3 parts
            amount_str: str = parts[0]
            unit_str: str = parts[1] if len(parts) > 1 else ""
            player_str: str = parts[2] if len(parts) > 2 else ""
            
            amount: int = int(amount_str)
            unit: str = unit_str
            player: int = 1 if player_str else 2
            
            print(f'Spawning {amount} {unit}')
            unit_type: UnitTypeId | None = self.parse_unit_type(unit)
            if (unit_type is None):
                print(f'Unknown unit type: {unit} !')
                return
            await self._create_units(amount, unit_type, player)


    async def zerg_rush(self):
        time: int = 4*60 + 20  # 4:20
        zerglings_count: int = 58
        if (self.bot.time != time):
            return
        if (self.rush_started):
            return
        await self.bot.chat_send(f'Zerg Rush [{zerglings_count}] started at {time}!')
        self.rush_started = True
        spawn_position: Point2 = self.bot.expansions.b2.position.towards(self.bot.expansions.enemy_main.position, 10)
        await self.bot.client.debug_create_unit([[UnitTypeId.ZERGLING, zerglings_count, spawn_position, 2]])
        await self.bot.client.debug_control_enemy()
        await self.bot.client.debug_show_map()
            

    async def composition_manager(self):
        composition: Composition = self.bot.composition_manager.composition
        for i, (string, color) in enumerate(composition.debug_info):
            position: Point2 = Point2((0.01, 0.01 + 0.015 * (i + 1)))
            self.draw_text_on_screen(string, position, color)

    async def composition_priorities(self):
        for i, unit_type in enumerate(self.bot.trainer.ordered_unit_types):
            position: Point2 = Point2((0.9, 0.02 + 0.015 * (i + 1)))
            self.draw_text_on_screen(unit_type.name, position)