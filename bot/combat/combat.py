import math
from typing import List, Optional, Set
from bot.combat.execute_orders import Execute
from bot.combat.orders import Orders
from bot.combat.threats import Threat
from bot.macro.expansion import Expansion
from bot.macro.macro import BASE_SIZE
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, ORANGE, PURPLE, RED, WHITE, YELLOW
from bot.utils.base import Base
from bot.utils.point2_functions import grid_offsets
from bot.utils.unit_functions import find_by_tag
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, bio
    
class Combat:
    bot: Superbot
    execute: Execute
    known_enemy_army: Army
    armies: List[Army] = []
    bases: List[Base] = []
    
    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.execute = Execute(bot)
        self.known_enemy_army = Army(Units([], bot), bot)
    
    @property
    def army_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.supply
        return result

    @property
    def army_radius(self) -> float:
        return self.army_supply * 0.2 + 10

    @property
    def armored_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.armored_ground_supply
        return result

    def debug_cluster(self) -> None:
        clusters: List[Units] = self.get_army_clusters()
        for i, cluster in enumerate(clusters):
            army = Army(cluster, self.bot)
            print("army", i)
            print(army.recap)
            
    def get_army_clusters(self, radius: float = 15) -> List[Army]:
        army: Units = (
            self.bot.units(UnitTypeId.MARINE)
            + self.bot.units(UnitTypeId.MARAUDER)
            + self.bot.units(UnitTypeId.MEDIVAC)
        )
        # deep copy to ensure self.units isn't modified
        units_copy: Units = army.copy()
        visited_ids: Set[int] = set()
        clusters: List[Units] = []

        for unit in units_copy:
            if unit.tag in visited_ids:
                continue  # Skip if already visited

            # Start a new cluster
            cluster: List[Unit] = []
            stack: List[int] = [unit.tag]

            while(stack):
                current_id: int = stack.pop()
                if current_id in visited_ids:
                    continue
                
                visited_ids.add(current_id)
                cluster.append(units_copy.find_by_tag(current_id))

                # Find neighbors within the radius
                for other_unit in units_copy:
                    if (
                        other_unit.tag not in visited_ids
                        and unit.position.distance_to(other_unit.position) <= radius
                    ):
                        stack.append(other_unit.tag)

            clusters.append(Army(Units(cluster, self.bot), self.bot))
        return clusters

    async def select_orders(self, iteration: int, situation: Situation):
        # update local armies
        # Scale radius in function of army supply
        # old_armies: List[Army] = self.armies.copy()
        self.armies = self.get_army_clusters(self.army_radius)
        
        global_enemy_buildings: Units = self.bot.enemy_structures
        global_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )
        
        for army in self.armies:
            army.orders = self.get_army_orders(army, situation, global_enemy_buildings, global_enemy_units)

    def get_army_orders(self, army: Army, situation: Situation, global_enemy_buildings: Units, global_enemy_units: Units) -> Orders:
        # define local enemies
        local_enemy_units: Units = self.get_local_enemy_units(army.units.center, self.army_radius)
        local_enemy_buildings = self.get_local_enemy_buildings(army.units.center, self.army_radius)
        local_enemy_workers: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.distance_to(army.units.center) <= 30
                and unit.can_be_attacked
                and unit.type_id in worker_types
            )
        )
        # useful in case of canon/bunker rush
        global_enemy_menacing_units_buildings: Units = global_enemy_units + global_enemy_buildings.filter(
            lambda unit: unit.type_id in tower_types
        )

        usable_medivacs: Units = army.units.of_type(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.health_percentage >= 0.5
        )
        fighting_army_supply: float = army.weighted_supply
        potential_army_supply: float = army.potential_supply
        local_enemy_army: Army = Army(local_enemy_units, self.bot)
        local_enemy_supply: float = local_enemy_army.weighted_supply
        unseen_enemy_army: Army = Army(self.known_enemy_army.units_not_in_sight, self.bot)
        unseen_enemy_supply: float = unseen_enemy_army.supply
        potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
        closest_building_to_enemies: Unit = None if global_enemy_menacing_units_buildings.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_menacing_units_buildings)
        distance_building_to_enemies: float = 1000 if global_enemy_menacing_units_buildings.amount == 0 else global_enemy_menacing_units_buildings.closest_distance_to(closest_building_to_enemies)
        
        stim_completed: bool = self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1

        closest_army: Army = self.get_closest_army(army)
        closest_army_distance: float = self.get_closest_army_distance(army)
        
        # debug info
        # self.draw_text_on_world(army.center, f'{local_enemy_army.recap}')

        # if local_army_supply > local threat
        # attack local_threat if it exists
        if (local_enemy_supply + local_enemy_buildings.amount > 0):
            
            if (situation == Situation.BUNKER_RUSH):
                return Orders.DEFEND_BUNKER_RUSH
            if (situation == Situation.CANON_RUSH):
                return Orders.DEFEND_CANON_RUSH

            # if enemy is a threat, micro if we win or we need to defend the base, retreat if we don't
            if (
                stim_completed and (
                    fighting_army_supply >= local_enemy_supply
                    or potential_army_supply >= local_enemy_supply * 1.25
                )
            ):
                return Orders.FIGHT_OFFENSE
            if (distance_building_to_enemies <= BASE_SIZE):
                return Orders.FIGHT_DEFENSE
            
            print(f'army too strong [{round(fighting_army_supply, 1)}/{round(potential_army_supply, 1)} vs {round(local_enemy_supply, 1)}/{round(local_enemy_supply * 1.5, 1)}], not taking the fight')
            return Orders.PICKUP_LEAVE
                
        # if we should defend
        if (distance_building_to_enemies <= 10):
            return Orders.DEFEND

        # if enemy is a workers, focus them
        if (local_enemy_workers.amount >= 1):
            return Orders.HARASS
        
        # if another army is close, we should regroup
        if (
            self.armies.__len__() >= 2
            and closest_army_distance <= self.army_radius * 1.2
            and 2/3 < closest_army.supply / army.supply < 3/2
        ):
            return Orders.REGROUP
        
        # if enemy is buildings, focus the lowest on life among those in range
        if (local_enemy_buildings.amount >= 1):
            return Orders.KILL_BUILDINGS
        
        # if we have enough army we attack
        if (
            potential_army_supply >= 8
            and potential_army_supply >= army.supply * 0.7
            and usable_medivacs.amount >= 1
            and stim_completed
        ):
            # if we would lose a fight
            if (
                potential_army_supply < potential_enemy_supply
            ):
                # if our bio is too low, heal up
                if (army.bio_health_percentage < 0.6):
                    return Orders.HEAL_UP
                else:
                    return Orders.DROP
            
            # if we would win a fight, we attack front
            else:
                # the next building if we know where it is, the nearest base if we don't
                if (global_enemy_buildings.amount >= 1):
                    return Orders.CHASE_BUILDINGS
                else:
                    return Orders.ATTACK_NEAREST_BASE

        return Orders.RETREAT

    async def execute_orders(self):
        for army in self.armies:            
            match army.orders:
                case Orders.PICKUP_LEAVE:
                    await self.execute.pickup_leave(army)
                
                case Orders.RETREAT:
                    self.execute.retreat_army(army)

                case Orders.HEAL_UP:
                    await self.execute.heal_up(army)
                
                case Orders.FIGHT_OFFENSE:
                    await self.execute.fight(army)
                
                case Orders.FIGHT_DEFENSE:
                    await self.execute.fight_defense(army)
                                 
                case Orders.DEFEND:
                    self.execute.defend(army)

                case Orders.DEFEND_BUNKER_RUSH:
                    self.execute.defend_bunker_rush(army)

                case Orders.DEFEND_CANON_RUSH:
                    self.execute.defend_canon_rush(army)

                case Orders.DROP:
                    await self.execute.drop(army)
                
                case Orders.HARASS:
                    await self.execute.harass(army)            
                     
                case Orders.KILL_BUILDINGS:
                    await self.execute.kill_buildings(army)

                case Orders.CHASE_BUILDINGS:
                    await self.execute.chase_buildings(army)

                case Orders.ATTACK_NEAREST_BASE:
                    await self.execute.attack_nearest_base(army)

                case Orders.REGROUP:
                    self.execute.regroup(army, self.armies)
    
    async def handle_bunkers(self):
        for expansion in self.bot.expansions.defended:
            bunker: Unit = expansion.defending_bunker
            enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: bunker.target_in_range(unit)
            )
            enemy_units_around: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: unit.distance_to(bunker) <= 8.5
            )
                
            # unload bunker if no unit around
            if (enemy_units_around.amount == 0):
                if (len(bunker.rally_targets) == 0):
                    rally_point: Point2 = bunker.position.towards(expansion.retreat_position, 3)
                    bunker(AbilityId.RALLY_UNITS, rally_point)
                if (bunker.cargo_used >= 1):
                    print("unload bunker")
                    bunker(AbilityId.UNLOADALL_BUNKER)
                continue
            
            # If bunker under 20 hp, unload
            if (bunker.health <= 20):
                bunker(AbilityId.UNLOADALL_BUNKER)
                continue
            
            # Attack the weakest enenmy in range
            if (enemy_units_in_range.amount >= 1):
                enemy_units_in_range.sort(key = lambda unit: unit.health + unit.shield)
                bunker.attack(enemy_units_in_range.first)
            if (bunker.cargo_left == 0):
                continue
            
            bio_close_by: Units = self.bot.units.filter(
                lambda unit: unit.type_id in bio and unit.distance_to(bunker) <= 10
            )
            if (bio_close_by.amount == 0):
                print("no bio closeby")
                continue
            bio_in_range: Units = Units(bio_close_by.filter(lambda unit: unit.distance_to(bunker) <= 3)[:4], self.bot)
            print("bio should load")
            for unit in bio_in_range:
                bunker(AbilityId.LOAD_BUNKER, unit)

    async def debug_colorize_bunkers(self):
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
                lambda unit: unit.type_id in bio and unit.distance_to(bunker) <= 10
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

    async def debug_army_orders(self):
        color: tuple = WHITE
        colors: dict = {
            Orders.PICKUP_LEAVE: RED,
            Orders.RETREAT: GREEN,
            Orders.HEAL_UP: GREEN,
            Orders.FIGHT_OFFENSE: RED,
            Orders.FIGHT_DEFENSE: ORANGE,
            Orders.DEFEND: YELLOW,
            Orders.HARASS: LIGHTBLUE,
            Orders.DROP: LIGHTBLUE,
            Orders.CHASE_BUILDINGS: LIGHTBLUE,
            Orders.ATTACK_NEAREST_BASE: PURPLE,
            Orders.KILL_BUILDINGS: PURPLE,
            Orders.CHASE_BUILDINGS: PURPLE,
            Orders.REGROUP: WHITE,
        }
        for army in self.armies:
            if (army.orders in colors):
                color = colors[army.orders]
            army_descriptor: str = f'[{army.orders.__repr__()}] (S: {army.weighted_supply.__round__(2)}/{army.potential_supply.__round__(2)})'
            self.draw_sphere_on_world(army.units.center, self.army_radius * 0.7, color)
            self.draw_text_on_world(army.units.center, army_descriptor, color)

    async def debug_bases_threat(self):
        color: tuple
        for base in self.bases:
            match base.threat:
                case Threat.NO_THREAT:
                    color = GREEN
                case Threat.ATTACK:
                    color = RED
                case Threat.WORKER_SCOUT:
                    color = YELLOW
                case Threat.HARASS:
                    color = BLUE
                case Threat.CANON_RUSH:
                    color = PURPLE
                case _:
                    color = WHITE
            base_descriptor: str = f'[{base.threat.__repr__()}]'
            # radius: float = 15
            # self.draw_sphere_on_world(base.position, radius, color)
            self.draw_text_on_world(base.position, base_descriptor, color)

    async def debug_bases_content(self):
        for expansion in self.bot.expansions.taken:
            below_expansion_point: Point2 = Point2((expansion.position.x, expansion.position.y - 0.5))
            self.draw_text_on_world(expansion.position, f'[{expansion.mineral_worker_count}/{expansion.optimal_mineral_workers.__round__(1)}] Minerals', LIGHTBLUE)
            self.draw_text_on_world(below_expansion_point, f'[{expansion.vespene_worker_count}/{expansion.optimal_vespene_workers.__round__(1)}] Gas[{expansion.vespene_geysers_refinery.amount}]', GREEN)

    async def debug_bases_bunkers(self):
        for expansion in self.bot.expansions.taken:
            below_expansion_point: Point2 = Point2((expansion.position.x, expansion.position.y - 0.5))
            self.draw_text_on_world(expansion.position, f'defended [{expansion.is_defended}]', LIGHTBLUE)
            defending_bunker: Unit = expansion.defending_bunker
            if (defending_bunker):
                self.draw_text_on_world(below_expansion_point, f'[{defending_bunker.position}]', GREEN)
                self.draw_grid_on_world(defending_bunker.position, 3, "Bunker")

    async def debug_bases_distance(self):
        last_expansion: Expansion = self.bot.expansions.last_taken
        for expansion in self.bot.expansions.taken:
            is_last: bool = last_expansion and expansion.position == last_expansion.position
            text: str = f'[LAST : {is_last}] : {expansion.distance_from_main}'
            self.draw_text_on_world(expansion.position, text)

    async def debug_selection(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        selected_positions: List[Point2] = []
        for unit in selected_units:
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
            while x <= end_x:
                y = start_y
                while y <= end_y:
                    color = GREEN if self.bot.map.in_building_grid(Point2((x, y))) else RED
                    self.draw_box_on_world(Point2((x, y)), 0.5, color)
                    y += 1.0
                x += 1.0
            
            # for x in range(0, right.x - left.x + 1):
            #     for y in range(0, up.y - bottom.y + 1):
            #         point: Point2 = Point2((left.x + x, bottom.y + y))
            #         color = GREEN if (self.bot.in_pathing_grid(point)) else RED
            #         self.draw_box_on_world(point, 0.5, color)
                    # if (self.bot.in_pathing_grid(point)):
                    #     self.draw_box_on_world(point, 0.25, GREEN)
                    # else:
                    #     self.draw_box_on_world(point, 0.25, RED)
        else:
            for unit in selected_units:
                self.draw_text_on_world(unit.position, f'Cloaked {unit.is_cloaked}, Burrowed {unit.is_burrowed}')
                
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

    async def debug_invisible_units(self):
        invisible_units: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
            lambda unit: (
                unit.is_visible
                and (unit.is_burrowed or unit.is_cloaked)
            )
        )
        for unit in invisible_units:
            self.draw_sphere_on_world(unit.position, radius=1, draw_color=YELLOW)
            self.draw_text_on_world(unit.position, f'{unit.type_id.name} [{unit.health}/{unit.health_max}]', YELLOW)

    
    async def debug_loaded_stuff(self, iteration: int):
        if (iteration % 10 != 0):
            return
        print("units amount: ", self.bot.units.amount)
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        for unit in selected_units:
            if (unit.has_cargo):
                passengers: Units = Units(unit.passengers, self.bot)
                print("loaded units: ", passengers)


    async def debug_drop_path(self):
        for center in self.bot.map.centers:
            self.draw_flying_box(center, 5)

    async def debug_unscouted_b2(self):
        for point in self.bot.expansions.b2.unscouted_points:
            self.draw_box_on_world(point, 0.5)

    async def debug_bunker_positions(self):
        for expansion in self.bot.expansions:
            bunker_forward_in_pathing: Optional[Point2] = expansion.bunker_forward_in_pathing
            bunker_ramp: Optional[Point2] = expansion.bunker_ramp
            if (expansion.is_defended or expansion.is_main):
                continue
            if (bunker_forward_in_pathing):
                self.draw_grid_on_world(bunker_forward_in_pathing, 3, "forward in pathing")
            if (bunker_ramp):
                self.draw_grid_on_world(bunker_ramp, 3, "ramp")
            
    def debug_barracks_correct_placement(self):
        self.draw_grid_on_world(self.bot.main_base_ramp.barracks_correct_placement, 3, "Barracks")
    
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
            draw_color = GREEN if (self.bot.in_pathing_grid(point_position)) else RED
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
    
    def get_closest_army(self, army: Army) -> Army:
        if (self.armies.__len__() < 2):
            return -1
        other_armies: List[Army] = list(filter(lambda other_army: other_army.center != army.center, self.armies))
        closest_army: Army = other_armies[0]
        closest_distance_to_other: float = army.center.distance_to(other_armies[0].center)
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < closest_distance_to_other):
                closest_distance_to_other = army.center.distance_to(other_army.center)
                closest_army = other_army
        return closest_army
    
    def get_closest_army_distance(self, army: Army):
        if (self.armies.__len__() < 2):
            return -1
        other_armies = list(filter(lambda other_army: other_army.center != army.center, self.armies))
        closest_distance_to_other: float = army.center.distance_to(other_armies[0].center)
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < closest_distance_to_other):
                closest_distance_to_other = army.center.distance_to(other_army.center)
        return round(closest_distance_to_other, 1)
                
    def get_local_enemy_units(self, position: Point2, radius: int = 15) -> Units:
        global_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )
        local_enemy_units: Units = global_enemy_units.filter(
            lambda unit: unit.distance_to(position) <= (10 + radius)
        )
        local_enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.type_id in tower_types and unit.can_be_attacked
        )
        return local_enemy_units + local_enemy_towers

    def get_local_enemy_buildings(self, position: Point2, radius: int = 10) -> Units:
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(position) <= radius and unit.can_be_attacked
        )
        local_enemy_buildings.sort(key=lambda building: building.health)
        return local_enemy_buildings

    async def detect_enemy_army(self):
        enemy_units: Units = self.bot.enemy_units
        self.known_enemy_army.detect_units(enemy_units)
            
    def unit_died(self, unit_tag: int):
        if unit_tag not in self.known_enemy_army.units.tags:
            return
        self.known_enemy_army.remove_by_tag(unit_tag)
        enemy_army: dict = self.known_enemy_army.recap
        print("remaining enemy units :", enemy_army)