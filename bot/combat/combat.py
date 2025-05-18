import math
from typing import List, Optional, Set, Tuple
from bot.combat.execute_orders import Execute
from bot.combat.micro import Micro
from bot.combat.orders import Orders
from bot.combat.threats import Threat
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions, get_expansions
from bot.macro.macro import BASE_SIZE
from bot.strategy.strategy_types import Situation
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, PURPLE, RED, WHITE, YELLOW
from bot.utils.base import Base
from bot.utils.point2_functions import center, grid_offsets
from bot.utils.unit_functions import find_by_tag, worker_amount_vespene_geyser, worker_amount_mineral_field
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, bio
    
class Combat:
    bot: BotAI
    execute: Execute
    # expansions: Expansions
    known_enemy_army: Army
    armies: List[Army] = []
    bases: List[Base] = []
    
    def __init__(self, bot: BotAI, expansions: Expansions) -> None:
        self.bot = bot
        # self.expansions = expansions
        self.execute = Execute(bot, expansions)
        self.known_enemy_army = Army(Units([], bot), bot)

    @property
    def expansions(self) -> Expansions:
        return get_expansions(self.bot)
    
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
        global_enemy_units_buildings: Units = global_enemy_units + global_enemy_buildings

        army_supply: float = army.weighted_supply
        local_enemy_army: Army = Army(local_enemy_units, self.bot)
        local_enemy_supply: float = local_enemy_army.weighted_supply
        unseen_enemy_army: Army = Army(self.known_enemy_army.units_not_in_sight, self.bot)
        unseen_enemy_supply: float = unseen_enemy_army.supply
        potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
        closest_building_to_enemies: Unit = None if global_enemy_units_buildings.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_units_buildings)
        distance_building_to_enemies: float = 1000 if global_enemy_units_buildings.amount == 0 else global_enemy_units_buildings.closest_distance_to(closest_building_to_enemies)
        
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
                army_supply >= local_enemy_supply
                and self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
            ):
                return Orders.FIGHT_OFFENSE
            if (distance_building_to_enemies <= BASE_SIZE):
                return Orders.FIGHT_DEFENSE
            
            print(f'army too strong [{army_supply.__round__(1)} vs {local_enemy_supply.__round__(1)}], not taking the fight')
            return Orders.PICKUP_LEAVE
            
            # TODO: fix "enemy too fast"
            # local_enemy_units.sort(key=lambda unit: unit.real_speed, reverse=True)
            # local_enemy_speed: Unit = local_enemy_units.first.real_speed
            # closest_unit: Unit = army.units.closest_to(local_enemy_units.first)
            # if (local_enemy_speed > army.speed and local_enemy_units.first.is_facing(closest_unit, math.pi / 2)):
            #     print("enemy too fast, taking the fight")
            #     army.orders = Orders.FIGHT
            # else:
            #     print(f'not fighting against {local_enemy_supply} supply')
            #     print("local_enemy_army:", local_enemy_army.recap)
            #     print("unseen_enemy_army:", unseen_enemy_army.recap)
            #     army.orders = Orders.RETREAT
                
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
            army_supply >= 10
            and army.units.of_type(UnitTypeId.MEDIVAC).amount >= 1
            and army_supply >= potential_enemy_supply
        ):
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
        for expansion in self.expansions.defended:
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
                    bunker(AbilityId.UNLOADALL_BUNKER)
                return
            
            # If bunker under 20 hp, unload
            if (bunker.health <= 20):
                bunker(AbilityId.UNLOADALL_BUNKER)
                return
            
            # Attack the weakest enenmy in range
            if (enemy_units_in_range.amount >= 1):
                enemy_units_in_range.sort(key = lambda unit: unit.health + unit.shield)
                bunker.attack(enemy_units_in_range.first)
            if (bunker.cargo_left == 0):
                return
            bio_close_by: Units = self.bot.units.filter(
                lambda unit: unit.type_id in bio and unit.distance_to(bunker) <= 10
            )
            if (bio_close_by.amount == 0):
                return
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
            Orders.FIGHT_OFFENSE: RED,
            Orders.FIGHT_DEFENSE: YELLOW,
            Orders.DEFEND: YELLOW,
            Orders.HARASS: BLUE,
            Orders.CHASE_BUILDINGS: LIGHTBLUE,
            Orders.ATTACK_NEAREST_BASE: PURPLE,
            Orders.KILL_BUILDINGS: PURPLE,
            Orders.CHASE_BUILDINGS: PURPLE,
            Orders.REGROUP: WHITE,
        }
        for army in self.armies:
            if (army.orders in colors):
                color = colors[army.orders]
            army_descriptor: str = f'[{army.orders.__repr__()}] (S: {army.weighted_supply.__round__(2)})'
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
        for expansion in self.expansions.taken:
            below_expansion_point: Point2 = Point2((expansion.position.x, expansion.position.y - 0.5))
            self.draw_text_on_world(expansion.position, f'[{expansion.mineral_worker_count}/{expansion.optimal_mineral_workers.__round__(1)}] Minerals', LIGHTBLUE)
            self.draw_text_on_world(below_expansion_point, f'[{expansion.vespene_worker_count}/{expansion.optimal_vespene_workers.__round__(1)}] Gas[{expansion.vespene_geysers_refinery.amount}]', GREEN)

    async def debug_bases_distance(self):
        last_expansion: Expansion = self.expansions.last_taken
        for expansion in self.expansions.taken:
            is_last: bool = last_expansion and expansion.position == last_expansion.position
            text: str = f'[LAST : {is_last}] : {expansion.distance_from_main}'
            self.draw_text_on_world(expansion.position, text)

    async def debug_selection(self):
        selected_units: Units = self.bot.units.selected + self.bot.structures.selected
        selected_positions: List[Point2] = []
        for unit in selected_units:
            selected_positions.append(unit.position)
        if (selected_units.amount > 1):
            center_point: Point2 = center(selected_positions)
            self.draw_sphere_on_world(center_point)
        else:
            for unit in selected_units:
                self.draw_text_on_world(unit.position, f'{unit.position}')
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
        # for unit in selected_units:
        #     order = "Idle" if unit.is_idle else unit.orders[0].ability.id.__str__()
        #     order_target = "" if unit.is_idle else unit.orders[0].target
        #     distance_to_cc: float = self.bot.townhalls.closest_distance_to(unit) if self.bot.townhalls else 0
        #     self.draw_text_on_world(unit.position, f'{order}[{order_target}], ({round(distance_to_cc, 2)})')

    async def debug_unscouted_b2(self):
        for point in self.expansions.b2.unscouted_points:
            self.draw_box_on_world(point, 0.5)

    async def debug_bunker_positions(self):
        for expansion in self.expansions:
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