import math
from typing import List, Optional, Set

import numpy as np
from bot.army_composition.composition import Composition
from bot.macro.map.influence_maps.danger.danger_evaluator import DangerEvaluator
from bot.macro.expansion import Expansion
from bot.macro.map.influence_maps.influence_map import InfluenceMap
from bot.macro.map.influence_maps.layers.buildings_layer import BuildingTile
from bot.strategy.build_order.build_order import BuildOrder
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, ORANGE, PURPLE, RED, WHITE, YELLOW
from bot.utils.point2_functions.utils import evaluate_path_debug, grid_offsets, sample_tile_path
from bot.utils.unit_functions import calculate_bunker_range, find_by_tag, is_being_constructed, scv_build_progress
from sc2.game_state import EffectData
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit, UnitOrder
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
            case 7:
                point_positions = grid_offsets(3, initial_position = pos.rounded_half)
        for i, point_position in enumerate(point_positions):
            tile: BuildingTile = self.bot.map.influence_maps.buildings.get_tile(point_position)
            draw_color: tuple = RED if tile.blocked else GREEN
            if (not tile.blocked and tile.reserved_for is not None):
                text: str = ''
                draw_color = YELLOW
                if (UnitTypeId.COMMANDCENTER in tile.reserved_for):
                    draw_color = BLUE
                    text = 'CC'
                elif (UnitTypeId.SUPPLYDEPOT in tile.reserved_for):
                    draw_color = PURPLE
                    text = 'Dpt'
                elif (UnitTypeId.MISSILETURRET in tile.reserved_for):
                    draw_color = ORANGE
                    text = 'MT'
                elif (UnitTypeId.BARRACKSREACTOR in tile.reserved_for):
                    draw_color = YELLOW
                    text = 'Ad'
                elif (UnitTypeId.BARRACKS in tile.reserved_for):
                    draw_color = YELLOW
                    text = 'Prd'
                elif (UnitTypeId.BUNKER in tile.reserved_for):
                    draw_color = ORANGE
                    text = 'Bkr'
                self.draw_text_on_world(point_position, text, draw_color, 10)
            self.draw_box_on_world(point_position, 0.45, draw_color)


    def draw_text_on_world(self, pos: Point2, text: str, draw_color: tuple = (255, 102, 255), font_size: int = 14) -> None:
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_text_world(
            text,
            Point3((pos.x, pos.y, z_height)),
            color=draw_color,
            size=font_size,
        )

    def draw_line_world(self, p0: Point2, p1: Point2, draw_color: tuple = (255, 102, 255)) -> None:
        z_height: float = self.bot.get_terrain_z_height(p0)
        self.bot.client.debug_line_out(
            Point3((p0.x, p0.y, z_height)),
            Point3((p1.x, p1.y, z_height)),
            color=draw_color,
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
            defending_bunker: Unit = expansion.defending_structure
            if (defending_bunker):
                self.draw_text_on_world(below_expansion_point, f'[{defending_bunker.position}]', GREEN)
                self.draw_grid_on_world(defending_bunker.position, 3, "Bunker")

    async def bases_distance(self):
        last_expansion: Expansion = self.bot.expansions.last_taken
        for expansion in self.bot.expansions.taken:
            is_last: bool = last_expansion and expansion.position == last_expansion.position
            text: str = f'[LAST : {is_last}] : {expansion.distance_from_main}'
            self.draw_text_on_world(expansion.position, text)

    def unit_type(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            self.draw_text_on_world(unit.position, f'{unit.name} [{unit.type_id}]')
    
    def building(self):
        selected_structures: Units = self.bot.structures.selected
        for structure in selected_structures:
            constructing: bool = is_being_constructed(self.bot, structure)
            progress: float = scv_build_progress(self.bot, self.bot.workers.closest_to(structure))
            self.draw_text_on_world(structure.position, f'Constructing: {constructing}, Progress: {progress:.2f}')

    
    def orders(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            order: str = "idle" if unit.is_idle else unit.orders[0].ability.exact_id
            target: str = "none" if len(unit.orders) == 0 or unit.orders[0].target is None else str(unit.orders[0].target)
            
            self.draw_text_on_world(unit.position, f'{unit.name} [{order}] target: {target} (cooldown : {unit.weapon_cooldown:.2f})')

            # draw target
            if (unit.is_idle):
                break
            target: int|Point2 = unit.orders[0].target
            if (isinstance(target, Point2)):
                self.draw_box_on_world(target)
            else:
                # find target unit
                target_unit: Unit = find_by_tag(self.bot, target)
                if (target_unit):
                    self.draw_box_on_world(target_unit.position)
    
    async def selection(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        selected_positions: List[Point2] = []
        for unit in selected_units:
            tile: BuildingTile = self.bot.map.influence_maps.buildings.get_tile(unit.position)
            color: tuple = RED if tile.blocked else GREEN
            if (tile.reserved_for is not None):
                color = ORANGE
                self.draw_text_on_world(unit.position, tile.reserved_for, 0.5, color)
            self.draw_box_on_world(unit.position, 0.5, color)
            selected_positions.append(unit.position)
            
        for unit in selected_units:
            for i, buff in enumerate(unit.buffs):
                self.draw_text_on_world(Point2((unit.position.x, unit.position.y + 2 * i)), f'Buff : {buff.name}')
            
            # draw "virtual range"
            range: float = unit.ground_range + unit.distance_to_weapon_ready
            self.draw_sphere_on_world(unit.position, radius=range, draw_color=ORANGE)

    def range(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        if (selected_units.amount == 0):
            selected_units = self.bot.enemy_units
        for unit in selected_units:
            # self.draw_sphere_on_world(unit.position, radius=1, draw_color=GREEN)
            # self.draw_sphere_on_world(unit.position, radius=2, draw_color=YELLOW)
            # self.draw_sphere_on_world(unit.position, radius=3, draw_color=RED)
            

            ground_range: float = unit.ground_range
            radius: float = unit.radius
            footprint: float = unit.footprint_radius
            if (unit.type_id == UnitTypeId.BUNKER):
                ground_range, air_range = calculate_bunker_range(self.bot, unit)
            self.draw_sphere_on_world(unit.position, radius=ground_range, draw_color=YELLOW)
            self.draw_text_on_world(unit.position, f'range: {ground_range}, radius: {radius}, footprint: {footprint}')
    
    def danger_map(self):
        selected_units: Units = self.bot.units.selected
        if (selected_units.amount == 0):
            return
        
        center: Point2 = selected_units.center
        flying_only: bool = all(u.is_flying for u in selected_units)
        # Read a region of size radius=8 around the center
        x1, y1, masked = self.bot.map.influence_maps.read(
            center,
            radius=8,
            air=flying_only,
            include_terrain_penalty=False,
        )
        
        # Iterate only over valid unmasked cells
        ys, xs = np.where(~masked.mask)

        for iy, ix in zip(ys, xs):
            danger = float(masked[iy, ix])
            # if (danger <= 0 or danger >= 999):
            #     continue

            # Convert tile coords back to world coords
            world_x = x1 + ix
            world_y = y1 + iy
            world_pos = Point2((world_x, world_y))

            # Build a readable color scale
            red = min(255, int(danger * 255 / 40))
            color = (red, 255 - red, 128)

            # Draw on SC2 world
            self.draw_text_on_world(world_pos, f"{danger:.1f}", color)

    def danger_trajectories(self):
        selected_units: Units = self.bot.units.selected
        if (selected_units.amount == 0):
            return

        start: Point2 = selected_units.center
        flying_only: bool = all(u.is_flying for u in selected_units)

        x1, y1, masked = self.bot.map.influence_maps.read(
            start,
            radius=8,
            air=flying_only,
            include_terrain_penalty=False,
        )

        evaluator = DangerEvaluator(self.bot, masked, x1, y1)

        ys, xs = np.where(~masked.mask)

        for iy, ix in zip(ys, xs):
            end = Point2((x1 + ix, y1 + iy))

            path = sample_tile_path(start, end)
            danger: float = evaluator.evaluate_path(path)

            # Build a readable color scale
            red = min(255, int(danger * 255 / 40))
            color = (red, 255 - red, 128)

            self.draw_text_on_world(
                end,
                f"{danger:.1f}",
                color,
            )
    
    def creep_map(self):
        selected_units: Units = self.bot.units.selected
        if (selected_units.amount == 0):
            return
        center: Point2 = selected_units.center
        # Read a region of size radius=8 around the center
        x1, y1, masked = self.bot.map.influence_maps.creep.density.read_values(center, radius=10)
        
        # Iterate only over valid unmasked cells
        ys, xs = np.where(~masked.mask)

        for iy, ix in zip(ys, xs):
            creep = float(masked[iy, ix])
            if (creep <= 0):
                continue

            # Convert tile coords back to world coords
            world_x = x1 + ix
            world_y = y1 + iy
            world_pos = Point2((world_x, world_y))

            # Build a readable color scale
            red = min(255, int(creep * 255))
            color = (red, 255 - red, 128)

            # Draw on SC2 world
            self.draw_text_on_world(world_pos, f"{creep:.1f}", color)

    def detection_map(self):
        selected_units: Units = self.bot.units.selected
        if (selected_units.amount == 0):
            return
        center: Point2 = selected_units.center
        # Read a region of size radius=8 around the center
        x1, y1, masked = self.bot.map.influence_maps.detection.detected.read_values(center, radius=15)
        
        # Iterate only over valid unmasked cells
        ys, xs = np.where(~masked.mask)

        for iy, ix in zip(ys, xs):
            detected = masked[iy, ix]
            if (detected == 0):
                continue

            # Convert tile coords back to world coords
            world_x = x1 + ix
            world_y = y1 + iy
            world_pos = Point2((world_x, world_y))

            # Draw on SC2 world
            self.draw_text_on_world(world_pos, 'X', GREEN)

    
    def full_effects(self, iteration: int):
        if (iteration % 10 != 0):
            return
        effects: Set[EffectData] = self.bot.state.effects
        print("full effects")
        print(effects)
        for effect in effects:
            print(f'effect {effect.id}')
            for i, position in enumerate(effect.positions):
                print(f'position[{i}] = {position}')
    
    def full_composition(self, iteration: int):
        if (iteration % 10 != 0):
            return
        units: Units = self.bot.units + self.bot.structures
        army: Army = Army(units, self.bot)
        print("full units")
        print(army.recap)
    
    async def loaded_stuff(self, iteration: int):
        if (iteration % 10 != 0):
            return
        print("units amount: ", self.bot.units.amount)
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            if (unit.has_cargo):
                passengers: Units = Units(unit.passengers, self.bot)
                print("loaded units: ", passengers)

    def tag(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            self.draw_text_on_world(unit.position, f'Tag: {unit.tag}', ORANGE)

    def radius(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            self.draw_text_on_world(unit.position, f'radius: {unit.radius}', ORANGE)
            self.draw_text_on_world(Point2((unit.position.x, unit.position.y - 1)), f'footprint: {unit.footprint_radius}', ORANGE)

    def addon_position(self):
        selected_units: Units = self.bot.structures.selected
        for unit in selected_units:
            position: Point2 = unit.add_on_position
            self.draw_text_on_world(unit.position, f'Addon Pos: {position}', ORANGE)

    async def bunker_positions(self):
        for expansion in self.bot.expansions.not_defended:
            bunker_position: Point2 = expansion.bunker_position
            self.draw_grid_on_world(bunker_position, 3, "Bunker")
            
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
        selected_units: Units = self.bot.units.selected
        if (selected_units.amount == 0):
            return
        position: Point2 = selected_units.center.rounded_half
        radius: float = 7
        # Read a region of size radius=8 around the center
        self.draw_grid_on_world(position, radius)
        

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
        pos: Optional[Point2] = None
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

        if (pos is None):
            player_camera = self.bot.state.observation_raw.player.camera
            pos = Point2((player_camera.x, player_camera.y))
        await self.bot.client.debug_create_unit([[unit_id, amount, pos, player_id]])

    async def spawn_test_units(self, message: str):
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

    
    async def spawn_creep(self):
        tumor_count: int = 100
        pathing: np.ndarray = self.bot.game_info.pathing_grid.data_numpy
        # Step 1: find all coordinates where pathing is True
        ys, xs = np.where(pathing == True)
        
        for i in range(tumor_count):
            # Step 2: pick a random index
            idx: int = np.random.randint(0, len(xs))

            # Step 3: construct a Point2
            pos: Point2 = Point2((xs[idx], ys[idx]))
            tumor_type: UnitTypeId = UnitTypeId.CREEPTUMORBURROWED
            # tumor_type: UnitTypeId = random.choice([UnitTypeId.CREEPTUMORBURROWED, UnitTypeId.CREEPTUMOR, UnitTypeId.CREEPTUMORQUEEN])
            await self._create_units(1, tumor_type, 2, pos)

    async def chat_commands(self):
        if (len(self.bot.state.chat) == 0 or self.bot.state.chat[0].player_id != self.bot.player_id):
            return
        message: str = self.bot.state.chat[0].message
        print(f'message: {message}')

        if (message.startswith("order")):
            print(f'Order info')
            self.order()
            return
        
        if (message[0].isdigit()):
            print(f'Spawning test units')
            await self.spawn_test_units(message)
            return
        
        if (message.startswith("tumors")):
            print(f'Spawning creep')
            await self.spawn_creep()
            return
        print(f'No command recognized')


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
            

    async def build_order(self):
        build_order: BuildOrder = self.bot.build_order.build
        for i, step in enumerate(build_order.steps):
            position: Point2 = Point2((0, 0.3 + 0.015 * (i + 1)))
            color = RED
            can_check, why = step.is_available_debug()
            if (can_check):
                color = YELLOW
            if (step.is_satisfied):
                color = GREEN
            self.draw_text_on_screen(f'{step.name} {why}', position, color, font_size=14)
    
    async def composition_manager(self):
        composition: Composition = self.bot.composition_manager.composition
        for i, (string, color) in enumerate(composition.debug_info):
            position: Point2 = Point2((0.01, 0.01 + 0.015 * (i + 1)))
            self.draw_text_on_screen(string, position, color)

    async def composition_priorities(self):
        for i, unit_type in enumerate(self.bot.trainer.ordered_unit_types):
            position: Point2 = Point2((0.9, 0.02 + 0.015 * (i + 1)))
            self.draw_text_on_screen(unit_type.name, position)

    def enemy_composition(self):
        start_position: float = 0.65 - 0.015 * len(self.bot.scouting.possible_enemy_composition)
        for i, unit_type in enumerate(self.bot.scouting.possible_enemy_composition):
            position: Point2 = Point2((0.9, start_position + 0.015 * (i + 1)))
            color = GREEN if unit_type in self.bot.scouting.known_enemy_composition else YELLOW
            self.draw_text_on_screen(unit_type.name, position, color)

    def ghost_units(self):
        ghost_units: Units = self.bot.ghost_units.assumed_enemy_units
        for unit in ghost_units:
            self.draw_box_on_world(unit.position, size=1, draw_color = ORANGE)
            self.draw_text_on_world(unit.position, f'{unit.type_id}', ORANGE)
    
    def invisible_units(self):
        invisible_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.is_visible == False
            )
        )
        for unit in invisible_units:
            self.draw_box_on_world(unit.position, size=1, draw_color=YELLOW)
            self.draw_text_on_world(unit.position, f'invisible', YELLOW)