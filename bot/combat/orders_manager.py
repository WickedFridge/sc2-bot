import math
from typing import List, Optional, Set
from bot.macro.map.danger_map import DangerMap
from bot.combat.execute_orders import Execute
from bot.combat.orders import Orders
from bot.macro.macro import BASE_SIZE
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, ORANGE, PURPLE, RED, WHITE, YELLOW
from bot.utils.base import Base
from bot.utils.point2_functions.utils import grid_offsets
from bot.utils.unit_cargo import get_building_cargo
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, bio, menacing

class OrdersManager:
    bot: Superbot
    execute: Execute
    armies: List[Army] = []
    bases: List[Base] = []
    DEFENSE_RANGE_LIMIT: int = 40
    
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
        return math.sqrt(self.army_supply) + 10

    @property
    def armored_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.armored_ground_supply
        return result
            
    def load_clusters(self) -> List[Army]:
        clusters: List[Army] = []
        for army in self.armies:
            units: List[Unit] = []
            for tag in army.tags:
                unit: Unit = self.bot.units.find_by_tag(tag)
                if (unit is not None):
                    units.append(unit)
            if (len(units) == 0):
                continue
            new_army: Army = Army(Units(units, self.bot), self.bot)
            new_army.orders = army.orders
            clusters.append(new_army)
        return clusters
    
    def get_army_clusters(self, iteration: int, radius: float = 15) -> List[Army]:
        # calculate the army cluster only every 4 frames
        if (iteration % 4 != 0 and len(self.armies) >= 0):
            clusters: List[Army] = self.load_clusters()
            if (len(clusters) >= 1):
                return clusters

        army: Units = self.bot.units.of_type([
            UnitTypeId.REAPER,
            UnitTypeId.MARINE,
            UnitTypeId.MARAUDER,
            UnitTypeId.GHOST,
            UnitTypeId.MEDIVAC,
            UnitTypeId.VIKINGFIGHTER,
            UnitTypeId.RAVEN,
        ])

        # deep copy to ensure self.units isn't modified
        units_copy: Units = army.copy()
        visited_ids: Set[int] = set()
        clusters: List[Army] = []
        
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
    
    @property
    def stim_completed(self) -> bool:
        return self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
    
    @property
    def stim_almost_completed(self) -> bool:
        return self.bot.already_pending_upgrade(UpgradeId.STIMPACK) >= 0.85
    
    @property
    def enemy_anti_air(self) -> Units:
        return self.bot.scouting.known_enemy_army.units(
            [UnitTypeId.PHOENIX, UnitTypeId.VIKING, UnitTypeId.CORRUPTOR]
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
        self.armies = self.get_army_clusters(iteration, self.army_radius)
        
        # if (iteration % 4 != 0):
        #     return
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
        global_enemy_menacing_units_buildings: Units = self.global_enemy_units.filter(
            lambda unit: unit.can_attack or unit.type_id in menacing or unit.is_burrowed
        ) + global_enemy_buildings.filter(
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
        if (distance_building_to_enemies <= 10 and closest_building_to_enemies.distance_to(army.center) <= self.DEFENSE_RANGE_LIMIT):
            return Orders.DEFEND

        # if enemy is a workers, focus them
        if (local_enemy_workers.amount >= 1):
            return Orders.HARASS
        
        # if we have few life, heal up
        if (army.bio_health_percentage <= 0.3):
            return Orders.HEAL_UP
        return Orders.SCOUT
    
    def get_army_orders(self, army: Army) -> Orders:
        # -- Specific orders for reapers
        if (army.units(UnitTypeId.REAPER).amount >= 1):
            return self.reapers_orders(army)
        
        # -- Define local enemies
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
        
        # -- Useful in case of canon/bunker rush
        situation: Situation = self.bot.scouting.situation
        global_enemy_menacing: Units = (
            self.global_enemy_units.filter(lambda u: u.can_attack or u.type_id in menacing)
            + global_enemy_buildings.filter(lambda u: u.type_id in tower_types)
        )
                
        local_enemy_army: Army = Army(local_enemy_units, self.bot)
        local_enemy_supply: float = local_enemy_army.weighted_supply
        
        unseen_enemy_army: Army = Army(self.bot.scouting.known_enemy_army.units_not_in_sight, self.bot)
        unseen_enemy_supply: float = unseen_enemy_army.supply
        potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
                
        # -- High-priority hardcoded situations
        if (situation == Situation.BUNKER_RUSH):
            return Orders.DEFEND_BUNKER_RUSH
        if (situation == Situation.CANON_RUSH):
            return Orders.DEFEND_CANON_RUSH
        
        # -- Drop logic
        if (army.is_drop):
            return self.get_drop_orders(
                army=army,
                local_enemy_supply=local_enemy_supply,
                local_enemy_workers=local_enemy_workers,
                local_enemy_buildings=local_enemy_buildings,
            )
        
        # -- Remaining general army logic
        if (local_enemy_supply > 0):
            return self.get_fight_orders(
                army=army,
                local_enemy_supply=local_enemy_supply,
                global_enemy_menacing=global_enemy_menacing
            )
        
        # -- Defend buildings under threat
        if (self.should_defend_buildings(army, global_enemy_menacing)):
            return Orders.DEFEND

        # -- Worker harassment
        if (local_enemy_workers.amount >= 1):
            return Orders.HARASS

        # -- Merge with nearby army
        if (self.should_regroup(army)):
            return Orders.REGROUP

        # -- Kill nearby buildings
        if (local_enemy_buildings.amount >= 1):
            return Orders.KILL_BUILDINGS

        # -- Global push decision
        if (self.should_attack(army, situation)):
            return self.get_attack_orders(army, global_enemy_buildings, potential_enemy_supply)

        # Nothing else → retreat by default
        return Orders.RETREAT
        
    def get_drop_orders(
        self,
        army: Army,
        local_enemy_supply: float,
        local_enemy_workers: Units,
        local_enemy_buildings: Units,
    ) -> Optional[Orders]:
        
        # If enemy near → follow the normal fighting logic
        if (local_enemy_supply > 0):
            # If winning with stim
            if (self.stim_completed and army.potential_supply >= local_enemy_supply):
                if (army.potential_supply >= army.supply * 2):
                    if (army.usable_medivacs.amount >= 2):
                        return Orders.FIGHT_OFFENSE
                    return Orders.PICKUP_LEAVE

                if (army.potential_supply >= local_enemy_supply * 1.5):
                    return Orders.FIGHT_CHASE
                return Orders.FIGHT_OFFENSE

            # If losing fight
            return Orders.PICKUP_LEAVE

        # Harass Workers or buildings we fly above
        if (local_enemy_workers.amount >= 1 or local_enemy_buildings.amount >= 1):
            if (army.potential_supply >= army.supply * 2):
                return Orders.FIGHT_DROP
            return Orders.HARASS
            
        # Heal up first if low bio HP
        if (army.bio_health_percentage < 0.7):
            if (army.usable_medivacs.filter(lambda m: m.energy >= 20).amount >= 1):
                return Orders.HEAL_UP
            return Orders.RETREAT

        # Otherwise continue drop if not too much AA
        if (self.enemy_anti_air.amount < 2 and army.usable_medivacs.amount >= 2):
            if (army.cargo_left >= 1 and army.ground_units.amount >= 1):
                return Orders.DROP_RELOAD
            return Orders.DROP_MOVE
        return Orders.RETREAT
                
    def get_fight_orders(
        self,
        army: Army,
        local_enemy_supply: float,
        global_enemy_menacing: Units
    ):
        weighted_army_supply: float = army.weighted_supply
        
        # if enemy is a threat, micro if we win or we need to defend the base, retreat if we don't
        if (
            self.stim_completed and (
                weighted_army_supply >= local_enemy_supply
                or army.potential_supply >= local_enemy_supply * 1.5
            )
        ):
            if (weighted_army_supply >= local_enemy_supply * 2):
                return Orders.FIGHT_CHASE
            else:
                return Orders.FIGHT_OFFENSE
        
        closest_building_to_enemies: Unit = None if global_enemy_menacing.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_menacing)
        distance_building_to_enemies: float = 1000 if global_enemy_menacing.amount == 0 else global_enemy_menacing.closest_distance_to(closest_building_to_enemies)
        
        if (
            distance_building_to_enemies <= BASE_SIZE
            and closest_building_to_enemies.distance_to(army.center) <= self.DEFENSE_RANGE_LIMIT
        ):
            return Orders.FIGHT_DEFENSE
        
        if (
            army.ground_units.amount >= 6 and (
                weighted_army_supply >= local_enemy_supply * 0.7
                # or army.potential_supply >= local_enemy_supply * 1.2
            )
        ):
            return Orders.FIGHT_DISENGAGE
        return Orders.PICKUP_LEAVE
    
    def should_defend_buildings(self, army: Army, global_enemy_menacing: Units) -> bool:
        closest_building_to_enemies: Unit = None if global_enemy_menacing.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_menacing)
        distance_building_to_enemies: float = 1000 if global_enemy_menacing.amount == 0 else global_enemy_menacing.closest_distance_to(closest_building_to_enemies)
        
        return (
            distance_building_to_enemies <= 10
            and Army(global_enemy_menacing, self.bot).supply >= 12
            and global_enemy_menacing.closest_distance_to(army.center) <= self.DEFENSE_RANGE_LIMIT
        )
    
    def should_regroup(self, army: Army) -> bool:
        closest_army: Army = self.get_closest_army(army)
        closest_army_distance: float = self.get_closest_army_distance(army)
        
        return (
            self.armies.__len__() >= 2
            and closest_army_distance <= self.army_radius * 1.2
            and 2/3 < closest_army.supply / army.supply < 3/2
            and army.bio_supply + closest_army.bio_supply >= 12
        )

    def should_attack(
        self,
        army: Army,
        situation: Situation
    ) -> bool:
        return (
            army.potential_supply >= 8
            # and army.potential_supply >= army.supply * 0.7
            and army.bio_health_percentage >= 0.7
            and (army.usable_medivacs.amount >= 2 or army.potential_supply >= 40)
            and army.potential_bio_supply >= 12
            and self.stim_almost_completed
            and situation != Situation.UNDER_ATTACK
        )

    def get_attack_orders(
        self,
        army: Army,
        global_enemy_buildings: Units,
        potential_enemy_supply: float,
    ) -> Orders:
        global_full_medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).filter(
            lambda unit: unit.tag not in army.tags and unit.cargo_left == 0
        )
        # the amount of medivacs allowed to drop is 2 by default, going up to 4 once we hit 8 medivacs
        # maximal_medivacs_dropping: int = max(2, self.bot.units(UnitTypeId.MEDIVAC).amount - 4)
        maximal_medivacs_dropping: int = 10
        
        # if we would lose a fight
        if (
            army.potential_supply < potential_enemy_supply
        ):
            # if our bio is too low, heal up if we have enough energy
            if (army.bio_health_percentage < 0.7):
                medivacs_with_energy: Units = army.usable_medivacs.filter(
                    lambda unit: unit.energy >= 20
                )
                if (medivacs_with_energy.amount >= 1):
                    return Orders.HEAL_UP
                else:
                    return Orders.RETREAT
            # only drop if opponent doesn't have enough anti air
            elif (
                self.enemy_anti_air.amount < 2
                and army.usable_medivacs.amount >= 2
                and maximal_medivacs_dropping - global_full_medivacs.amount >= 2
            ):
                return Orders.DROP_LOAD
            else:
                return Orders.RETREAT
        
        # if we would win a fight, we attack front
        else:
            # the next building if we know where it is, the nearest base if we don't
            if (global_enemy_buildings.amount >= 1):
                return Orders.CHASE_BUILDINGS
            else:
                return Orders.ATTACK_NEAREST_BASE

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
                
                case Orders.FIGHT_CHASE:
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

                case Orders.DROP_LOAD | Orders.DROP_RELOAD:
                    await self.execute.drop_load(army)
                
                case Orders.DROP_MOVE:
                    await self.execute.drop_move(army)
                
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
            bunker: Unit = expansion.defending_structure
            bunker_default_range: int = 6
            bunker_bonus_range: int = 2 if self.bot.already_pending_upgrade(UpgradeId.HISECAUTOTRACKING) == 1 else 1
            bunker_ground_range: float = bunker_default_range + bunker_bonus_range + bunker.radius
            bunker_air_range: float = bunker_default_range + bunker_bonus_range + bunker.radius
            for passenger in bunker.passengers:
                bunker_ground_range = max(bunker_ground_range, passenger.ground_range + bunker_bonus_range)
                bunker_air_range = max(bunker_air_range, passenger.air_range + bunker_bonus_range)

            enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: (
                    (unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_air_range + unit.radius) ** 2)
                    or (not unit.is_flying and bunker.distance_to_squared(unit) <= (bunker_ground_range + unit.radius) ** 2)
                )
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
            
            # If bunker under 20 hp, unload
            if (bunker.health <= 20):
                bunker(AbilityId.UNLOADALL_BUNKER)
                continue
            
            # Attack the weakest enenmy in range
            if (enemy_units_in_range.amount >= 1):
                # if any units inside the bunkers is full life, stim them
                if (
                    self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                    and any(passenger.health_percentage == 1 for passenger in bunker.passengers)
                ):
                    print("stimming passengers")
                    bunker(AbilityId.EFFECT_STIM)
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
            # prioritize marines, then marauders, unless enemy army is mostly armored
            default_load_priority: List[UnitTypeId] = [
                UnitTypeId.GHOST,
                UnitTypeId.MARINE,
                UnitTypeId.MARAUDER,
                UnitTypeId.REAPER,
            ]
            armored_load_priority: List[UnitTypeId] = [
                UnitTypeId.MARAUDER,
                UnitTypeId.GHOST,
                UnitTypeId.MARINE,
                UnitTypeId.REAPER,
            ] 
            enemy_army: Army = Army(enemy_units_menacing, self.bot)
            load_priority: List[UnitTypeId] = armored_load_priority if enemy_army.armored_ratio >= 0.5 else default_load_priority
            
            cargo_left: int = bunker.cargo_left
            for unit_type in load_priority:
                unit_cargo: int = get_building_cargo(unit_type)
                if (unit_cargo > cargo_left):
                    continue
                for unit in bio_in_range(unit_type):
                    bunker(AbilityId.LOAD_BUNKER, unit)
                    cargo_left -= unit_cargo
                    if (unit_cargo > cargo_left):
                        break
    
    async def micro_planetary_fortresses(self):
        for pf in self.bot.units(UnitTypeId.PLANETARYFORTRESS):
            enemy_units_in_range: Units = (self.bot.enemy_units + self.bot.enemy_structures).filter(
                lambda unit: pf.target_in_range(unit)
            )
            if (enemy_units_in_range.amount >= 1 and pf.weapon_cooldown == 0):
                enemy_units_in_range.sort(key = lambda unit: unit.health + unit.shield)
                pf.attack(enemy_units_in_range.first)

    
    async def debug_army_orders(self):
        color: tuple = WHITE
        colors: dict = {
            Orders.PICKUP_LEAVE: RED,
            Orders.RETREAT: GREEN,
            Orders.HEAL_UP: GREEN,
            Orders.FIGHT_OFFENSE: RED,
            Orders.FIGHT_CHASE: RED,
            Orders.FIGHT_DROP: RED,
            Orders.FIGHT_DEFENSE: ORANGE,
            Orders.FIGHT_DISENGAGE: ORANGE,
            Orders.DEFEND: YELLOW,
            Orders.HARASS: LIGHTBLUE,
            Orders.DROP_LOAD: LIGHTBLUE,
            Orders.DROP_MOVE: LIGHTBLUE,
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

        for expansion in self.bot.expansions.potential_enemy_bases:
            self.draw_grid_on_world(expansion.position, text="Potential Enemy Base")
    
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
        self.draw_text_on_world(pos.rounded_half, text, font_size=10)
        

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