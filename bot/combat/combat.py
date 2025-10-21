from typing import List, Set
from bot.combat.execute_orders import Execute
from bot.combat.orders import Orders
from bot.macro.macro import BASE_SIZE
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, ORANGE, PURPLE, RED, WHITE, YELLOW
from bot.utils.base import Base
from bot.utils.point2_functions import grid_offsets
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, bio, menacing
    
class Combat:
    bot: Superbot
    execute: Execute
    armies: List[Army] = []
    bases: List[Base] = []
    
    def __init__(self, bot: Superbot) -> None:
        self.bot = bot
        self.execute = Execute(bot)
    
    @property
    def army_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.supply
        return result

    @property
    def army_radius(self) -> float:
        return self.army_supply * 0.15 + 10

    @property
    def armored_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.armored_ground_supply
        return result
            
    def get_army_clusters(self, radius: float = 15) -> List[Army]:
        army: Units = self.bot.units.of_type([
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.GHOST,
            UnitTypeId.MEDIVAC,
            UnitTypeId.VIKINGFIGHTER,
        ])
        # deep copy to ensure self.units isn't modified
        units_copy: Units = army.copy()
        visited_ids: Set[int] = set()
        clusters: List[Units] = []

        # create a first cluster with all Reapers
        reapers: Units = self.bot.units(UnitTypeId.REAPER)
        if (reapers.amount >= 1):
            clusters.append(Army(Units(reapers, self.bot), self.bot))
        
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

    
    @property
    def global_enemy_units(self) -> Units:
        return self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )    
    
    def debug_cluster(self) -> None:
        clusters: List[Units] = self.get_army_clusters()
        for i, cluster in enumerate(clusters):
            army = Army(cluster, self.bot)
            print("army", i)
            print(army.recap)

    async def select_orders(self, iteration: int):
        # update local armies
        # Scale radius in function of army supply
        # old_armies: List[Army] = self.armies.copy()
        self.armies = self.get_army_clusters(self.army_radius)
        
        for army in self.armies:
            army.orders = self.get_army_orders(army)

    def reapers_orders(self, army: Army) -> Orders:
        situation: Situation = self.bot.scouting.situation
        local_enemy_units: Units = self.get_local_enemy_units(army.units.center, self.army_radius)
        local_enemy_army: Army = Army(local_enemy_units, self.bot)
        local_enemy_supply: float = local_enemy_army.weighted_supply
        global_enemy_buildings: Units = self.bot.enemy_structures
        local_enemy_workers: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.distance_to(army.units.center) <= 30
                and unit.can_be_attacked
                and unit.type_id in worker_types
            )
        )
        # useful in case of canon/bunker rush
        global_enemy_menacing_units_buildings: Units = self.global_enemy_units.filter(lambda unit: unit.can_attack or unit.type_id in menacing or unit.is_burrowed) + global_enemy_buildings.filter(
            lambda unit: unit.type_id in tower_types
        )
        closest_building_to_enemies: Unit = None if global_enemy_menacing_units_buildings.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_menacing_units_buildings)
        distance_building_to_enemies: float = 1000 if global_enemy_menacing_units_buildings.amount == 0 else global_enemy_menacing_units_buildings.closest_distance_to(closest_building_to_enemies)

        # if there are units, fight or retreat
        if (situation == Situation.BUNKER_RUSH):
            return Orders.DEFEND_BUNKER_RUSH
        if (situation == Situation.CANON_RUSH):
            return Orders.DEFEND_CANON_RUSH
            
        if (local_enemy_supply > 0):        
            if (distance_building_to_enemies <= BASE_SIZE):
                return Orders.FIGHT_DEFENSE
            return Orders.FIGHT_OFFENSE
        
        # if we should defend
        if (distance_building_to_enemies <= 10):
            return Orders.DEFEND

        # if enemy is a workers, focus them
        if (local_enemy_workers.amount >= 1):
            return Orders.HARASS
        
        # if we have few life, heal up
        if (army.bio_health_percentage <= 0.3):
            return Orders.HEAL_UP
        return Orders.SCOUT
    
    def get_army_orders(self, army: Army) -> Orders:
        # specific orders for reapers
        if (army.units(UnitTypeId.REAPER).amount >= 1):
            return self.reapers_orders(army)
        
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
        global_enemy_buildings: Units = self.bot.enemy_structures
        # useful in case of canon/bunker rush
        situation: Situation = self.bot.scouting.situation
        global_enemy_menacing_units_buildings: Units = self.global_enemy_units.filter(lambda unit: unit.can_attack or unit.type_id in menacing) + global_enemy_buildings.filter(
            lambda unit: unit.type_id in tower_types
        )

        usable_medivacs: Units = army.units.of_type(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.health_percentage >= 0.5
        )
        fighting_army_supply: float = army.weighted_supply
        potential_army_supply: float = army.potential_supply
        potential_bio_supply: float = army.potential_bio_supply
        local_enemy_army: Army = Army(local_enemy_units, self.bot)
        local_enemy_supply: float = local_enemy_army.weighted_supply
        unseen_enemy_army: Army = Army(self.bot.scouting.known_enemy_army.units_not_in_sight, self.bot)
        unseen_enemy_supply: float = unseen_enemy_army.supply
        potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
        closest_building_to_enemies: Unit = None if global_enemy_menacing_units_buildings.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_menacing_units_buildings)
        distance_building_to_enemies: float = 1000 if global_enemy_menacing_units_buildings.amount == 0 else global_enemy_menacing_units_buildings.closest_distance_to(closest_building_to_enemies)
        
        stim_completed: bool = self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
        stim_almost_completed: bool = self.bot.already_pending_upgrade(UpgradeId.STIMPACK) >= 0.85

        closest_army: Army = self.get_closest_army(army)
        closest_army_distance: float = self.get_closest_army_distance(army)
        
        # debug info
        # self.draw_text_on_world(army.center, f'{local_enemy_army.recap}')

        # first handle specific situations
        if (situation == Situation.BUNKER_RUSH):
            return Orders.DEFEND_BUNKER_RUSH
        if (situation == Situation.CANON_RUSH):
            return Orders.DEFEND_CANON_RUSH
        
        # Deal with local enemy supply
        if (local_enemy_supply):
            # if enemy is a threat, micro if we win or we need to defend the base, retreat if we don't
            if (
                stim_completed and (
                    fighting_army_supply >= local_enemy_supply
                    or potential_army_supply >= local_enemy_supply * 1.25
                )
            ):
                if (potential_army_supply >= army.supply * 2):
                    # only fight if our medivacs are healthy
                    if (usable_medivacs.amount >= 2):
                        return Orders.FIGHT_DROP
                    else:
                        return Orders.RETREAT
                else:
                    return Orders.FIGHT_OFFENSE
            if (distance_building_to_enemies <= BASE_SIZE):
                return Orders.FIGHT_DEFENSE
            if (
                army.ground_units.amount >= 6 and (
                    fighting_army_supply >= local_enemy_supply * 0.7
                    or potential_army_supply >= local_enemy_supply * 0.9    
                )
            ):
                print(f'disengaging')
                return Orders.FIGHT_DISENGAGE
            
            print(f'army too strong [{round(fighting_army_supply, 1)}/{round(potential_army_supply, 1)} vs {round(local_enemy_supply, 1)}/{round(local_enemy_supply * 1.25, 1)}], not taking the fight')
            return Orders.PICKUP_LEAVE
                
        # if we should defend
        if (distance_building_to_enemies <= 10 and Army(global_enemy_menacing_units_buildings, self.bot).supply >= 12):
            return Orders.DEFEND

        # if enemy is a workers, focus them
        if (local_enemy_workers.amount >= 1):
            if (potential_army_supply >= army.supply * 2):
                return Orders.FIGHT_DROP
            else:
                return Orders.HARASS
        
        # if another army is close, we should regroup
        # only merge ground armies
        if (
            self.armies.__len__() >= 2
            and closest_army_distance <= self.army_radius * 1.2
            and 2/3 < closest_army.supply / army.supply < 3/2
            and army.bio_supply + closest_army.bio_supply >= 12
        ):
            return Orders.REGROUP
        
        # if enemy is buildings, focus the lowest on life among those in range
        if (local_enemy_buildings.amount >= 1):
            return Orders.KILL_BUILDINGS
        
        # if we have enough army and we're not under attack we attack
        if (
            potential_army_supply >= 8
            and potential_army_supply >= army.supply * 0.7
            and (usable_medivacs.amount >= 2 or potential_army_supply >= 40)
            and potential_bio_supply >= 12
            and stim_almost_completed
            and situation != Situation.UNDER_ATTACK
        ):
            # if we would lose a fight
            if (
                potential_army_supply < potential_enemy_supply
            ):
                # if our bio is too low, heal up
                if (army.bio_health_percentage < 0.7):
                    return Orders.HEAL_UP
                # only drop if opponent doesn't have several phoenixes
                elif (self.bot.scouting.known_enemy_army.units(UnitTypeId.PHOENIX).amount < 2):
                    return Orders.DROP
                else:
                    return Orders.RETREAT
            
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
                    await self.execute.retreat_army(army)

                case Orders.HEAL_UP:
                    await self.execute.heal_up(army)
                
                case Orders.FIGHT_OFFENSE:
                    await self.execute.fight(army)

                case Orders.FIGHT_DROP:
                    await self.execute.fight_drop(army)

                case Orders.FIGHT_DISENGAGE:
                    await self.execute.disengage(army)
                
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
                    await self.execute.kill_buildings(army, self.army_radius)

                case Orders.CHASE_BUILDINGS:
                    await self.execute.chase_buildings(army)

                case Orders.ATTACK_NEAREST_BASE:
                    await self.execute.attack_nearest_base(army)

                case Orders.REGROUP:
                    self.execute.regroup(army, self.armies)

                case Orders.SCOUT:
                    self.execute.scout(army)
    
    async def handle_bunkers(self):
        for expansion in self.bot.expansions.defended:
            bunker: Unit = expansion.defending_bunker
            enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: bunker.target_in_range(unit)
            )
            enemy_units_potentially_in_range: Units  = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: bunker.distance_to(unit) <= 7 + bunker.radius + unit.radius
            )

            # unload bunker if no enemy can shoot the bunker and the bunker can't shoot any unit => bunker is safe and doesn't need to be loaded
            enemy_units_menacing: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: unit.target_in_range(bunker)
            )
                
            # unload bunker if no unit around
            if (enemy_units_menacing.amount == 0 and enemy_units_in_range.amount == 0 and enemy_units_potentially_in_range.amount == 0):
                if (len(bunker.rally_targets) == 0):
                    rally_point: Point2 = expansion.retreat_position
                    bunker(AbilityId.RALLY_UNITS, rally_point)
                if (bunker.cargo_used >= 1):
                    print("unload bunker")
                    bunker(AbilityId.UNLOADALL_BUNKER)
                # continue
            
            # If bunker under 20 hp, unload
            if (bunker.health <= 20):
                bunker(AbilityId.UNLOADALL_BUNKER)
                continue
            
            # Attack the weakest enenmy in range
            if (enemy_units_in_range.amount >= 1):
                enemy_units_in_range.sort(key = lambda unit: unit.health + unit.shield)
                bunker.attack(enemy_units_in_range.first)
            
            # load the bunker with bio if there is space
            if (bunker.cargo_left == 0):
                continue
            
            bio_in_range: Units = self.bot.units.filter(
                lambda unit: unit.type_id in bio and unit.distance_to(bunker) <= 3
            )
            if (bio_in_range.amount == 0):
                continue
            SAFETY_RADIUS: float = 1.5
            bio_in_danger: Units = bio_in_range.filter(
                lambda unit: (
                    self.bot.enemy_units.filter(
                        lambda enemy: enemy.can_attack_ground
                        and enemy.distance_to(unit) <= enemy.ground_range + SAFETY_RADIUS
                    ).amount > 0
                )
            )
            if (
                bio_in_danger.amount == 0
                and enemy_units_potentially_in_range.amount == 0
            ):
                continue

            # load the bunker with bio
            # prioritize marines, then marauders
            bio_should_load: Units = bio_in_range(UnitTypeId.MARINE).take(bunker.cargo_left)
            if (bio_should_load.amount < 4):
                bio_should_load += bio_in_range(UnitTypeId.MARAUDER).take(bunker.cargo_left - bio_should_load.amount)
            for unit in bio_should_load:
                bunker(AbilityId.LOAD_BUNKER, unit)

    
    async def debug_army_orders(self):
        color: tuple = WHITE
        colors: dict = {
            Orders.PICKUP_LEAVE: RED,
            Orders.RETREAT: GREEN,
            Orders.HEAL_UP: GREEN,
            Orders.FIGHT_OFFENSE: RED,
            Orders.FIGHT_DROP: RED,
            Orders.FIGHT_DEFENSE: ORANGE,
            Orders.FIGHT_DISENGAGE: ORANGE,
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
    
    async def debug_drop_target(self):
        drop_target: Point2 = self.execute.drop_target
        best_edge: Point2 = self.execute.best_edge
        self.draw_grid_on_world(drop_target, text="Drop Target")
        self.draw_flying_box(best_edge, 5, PURPLE)
        self.bot.client.debug_line_out(
            Point3((drop_target.x, drop_target.y, 10)),
            Point3((best_edge.x, best_edge.y, 10)),
            color=PURPLE,
        )
        self.draw_text_on_world(best_edge, "Best Edge", PURPLE)

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
        local_enemy_units: Units = self.global_enemy_units.filter(
            lambda unit: (
                unit.distance_to(position) <= (10 + radius)
                and unit.type_id not in worker_types
            )
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