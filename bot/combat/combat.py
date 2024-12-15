import math
from typing import List, Set
from bot.combat.execute_orders import Execute
from bot.combat.orders import Orders
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, PURPLE, RED, WHITE, YELLOW
from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, hq_types, menacing
from ..utils.unit_supply import supply


class Combat:
    bot: BotAI
    execute: Execute
    workers_pulled_amount: int = 0
    enemy_threats_amount: int = 0
    enemy_towers_amount: int = 0
    known_enemy_army: Army
    armies: List[Army] = []
    
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        self.execute = Execute(bot)
        self.known_enemy_army = Army(Units([], bot), bot)

    def debug_cluster(self) -> None:
        clusters: List[Units] = self.get_army_clusters()
        for i, cluster in enumerate(clusters):
            army = Army(cluster, self.bot)
            print("army", i)
            print(army.recap())
            

    def get_army_clusters(self, radius: float = 15) -> List[Army]:
        army: Units = (self.bot.units(UnitTypeId.MARINE) + self.bot.units(UnitTypeId.MEDIVAC))
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

    def get_army_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.army_supply()
        return result

    async def pull_workers(self):
        # TODO: estimate enemy threat
        # retreat workers if army > enemy threat
        # else pull workers
        
        # TODO: fill bunkers
        # for bunker in self.structures(UnitTypeId.BUNKER).ready:
        #     for marine in self.units(UnitTypeId.MARINE).closest_n_units(bunker, 4):
        #         marine(AbilityId.LOAD_BUNKER, bunker)
        if not self.bot.panic_mode:
            # ask all chasing SCVs to stop
            attacking_workers = self.bot.workers.filter(
                lambda unit: unit.is_attacking
            )
            for attacking_worker in attacking_workers:
                attacking_worker.stop()
            return

        if self.bot.workers.collecting.amount == 0:
            print("no workers to pull, o7")
            return

        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.bot.townhalls.amount == 0):
            print("no townhalls left, o7")
            for worker in self.bot.workers:
                worker.attack(self.bot.enemy_units.closest_to(worker))
            return
        
        for cc in self.bot.townhalls:
            # define threats in function of distance to townhalls
            # threats need to be attackable, ground units close to a CC

            enemy_threats = self.bot.enemy_units.filter(
                lambda unit: unit.distance_to(cc) <= 10 and unit.can_be_attacked and not unit.is_flying
            )
            
            enemy_towers: Units = self.bot.enemy_structures.filter(
                lambda unit: unit.type_id in tower_types and unit.distance_to(cc) <= 20
            )

            if (enemy_threats.amount != self.enemy_threats_amount or enemy_towers.amount != self.enemy_towers_amount):
                self.enemy_threats_amount = enemy_threats.amount
                self.enemy_towers_amount = enemy_towers.amount
                # print("panic attack : ", enemy_towers.amount, "enemy towers, ", enemy_threats.amount, "enemy units")
            # respond to canon/bunker/spine rush
            for tower in enemy_towers:
                # Pull 3 workers by tower by default, less if we don't have enough
                # Only pull workers if we don't have enough workers attacking yet
                workers_attacking_tower = self.bot.workers.filter(
                    lambda unit: unit.is_attacking and unit.order_target == tower.tag
                ).amount
                if (workers_attacking_tower >= 3):
                    break

                amount_to_pull: int = 3 - workers_attacking_tower
                workers: Units = self.bot.workers.collecting.sorted_by_distance_to(tower)

                workers_pulled: Units = workers[:amount_to_pull] if workers.amount >= amount_to_pull else workers

                for worker_pulled in workers_pulled:
                    worker_pulled.attack(tower)

            # collecting workers close to threats should be pulled
            workers: Units = self.bot.workers.collecting
            
            for threat in enemy_threats:
                closest_worker: Unit = workers.closest_to(threat)
                
                # handle scouting worker identified as threat
                if threat.type_id in worker_types:
                    # if no scv is already chasing
                    attacking_workers: Unit = self.bot.workers.filter(
                        lambda unit: unit.is_attacking and unit.order_target == threat.tag
                    )
                    if (attacking_workers.amount == 0):
                        # pull 1 scv to follow it
                        closest_worker.attack(threat)
                # else pull against close units
                elif (closest_worker.distance_to(threat) <= 20):
                        closest_worker.attack(threat)

            workers_pulled_amount: int = self.bot.workers.filter(lambda unit: unit.is_attacking).amount
            if (workers_pulled_amount != self.workers_pulled_amount):
                self.workers_pulled_amount = workers_pulled_amount
                print(workers_pulled_amount, "workers pulled")


    async def select_orders(self):
        # update local armies
        # Scale radius in function of army supply
        army_radius: float = 0.2 * self.get_army_supply() + 15

        self.armies = self.get_army_clusters(army_radius)
        global_enemy_buildings: Units = self.bot.enemy_structures
        global_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )
        
        for army in self.armies:
            # define local enemies
            
            local_enemy_units: Units = global_enemy_units.filter(
                lambda unit: unit.distance_to(army.units.center) <= 20
            )
            local_enemy_towers: Units = self.bot.enemy_structures.filter(
                lambda unit: unit.type_id in tower_types and unit.can_be_attacked
            )
            local_enemy_units += local_enemy_towers
            local_enemy_buildings: Units = self.bot.enemy_structures.filter(
                lambda unit: unit.distance_to(army.units.center) <= 10 and unit.can_be_attacked
            )
            local_enemy_buildings.sort(key=lambda building: building.health)
            local_enemy_workers: Units = self.bot.enemy_units.filter(
                lambda unit: (
                    unit.distance_to(army.units.center) <= 30
                    and unit.can_be_attacked
                    and unit.type_id in worker_types
                )
            )

            army_supply: float = army.army_supply()
            local_enemy_army: Army = Army(local_enemy_units, self.bot)
            local_enemy_supply: float = local_enemy_army.army_supply()
            unseen_enemy_army: Army = Army(self.known_enemy_army.units_not_in_sight(), self.bot)
            unseen_enemy_supply: float = unseen_enemy_army.army_supply()
            potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
            closest_building_to_enemies: Unit = None if global_enemy_units.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_units)
            distance_building_to_enemies: float = 1000 if global_enemy_units.amount == 0 else global_enemy_units.closest_distance_to(closest_building_to_enemies)
            closest_army_distance: float = self.get_closest_army_distance(army)
            
            # TODO: add regroup
            # if local_army_supply > local threat
            # attack local_threat if it exists
            if (local_enemy_supply + local_enemy_buildings.amount >= 1):
                
                # TODO: move stim in the write place
                # If units or buildings in sight, should be stimmed if above 25 hp
                self.stim(army.units, local_enemy_units, local_enemy_buildings)
    
                # if enemy is a threat, micro if we win or we panic, retreat if we don't
                if (
                    army_supply >= potential_enemy_supply
                    or self.bot.panic_mode
                    or distance_building_to_enemies <= 10
                ):
                    army.orders = Orders.FIGHT
                else:
                    print(f'not fighting against {potential_enemy_supply} supply')
                    print("local_enemy_army:", local_enemy_army.recap())
                    print("unseen_enemy_army:", unseen_enemy_army.recap())
                    army.orders = Orders.RETREAT
                    
            # if we should defend
            elif (
                self.bot.panic_mode
                or distance_building_to_enemies <= 10
            ):
                army.orders = Orders.DEFEND

            # if enemy is a workers, focus them
            elif (local_enemy_workers.amount >= 1):
                army.orders = Orders.HARASS
                
            # if another army is close, we should regroup
            elif (
                self.armies.__len__() >= 2
                and closest_army_distance <= 20
            ):
                army.orders = Orders.REGROUP
            
            # if enemy is buildings, focus the lowest on life among those in range
            elif (local_enemy_buildings.amount >= 1):
                army.orders = Orders.KILL_BUILDINGS
            
            # else find next building
            elif (
                global_enemy_buildings.amount >= 1
                and army_supply >= 10
                and army_supply >= potential_enemy_supply
            ):
                army.orders = Orders.CHASE_BUILDINGS

            # if our local_army_supply is higher than known army
            elif (
                local_enemy_supply == 0
                and army_supply >= 10
                and army_supply >= potential_enemy_supply
            ):
                # move towards closest enemy base
                army.orders = Orders.ATTACK_NEAREST_BASE
            else:
                army.orders = Orders.RETREAT

    async def execute_orders(self):
        for army in self.armies:            
            match army.orders:
                case Orders.RETREAT:
                    self.execute.retreat_army(army)
                
                case Orders.FIGHT:
                    await self.execute.fight(army)
                                 
                case Orders.DEFEND:
                    self.execute.defend(army)

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
    
    async def debug_colorize_army(self):
        color: tuple
        for army in self.armies:
            match army.orders:
                case Orders.RETREAT:
                    color = GREEN
                case Orders.FIGHT:
                    color = RED
                case Orders.DEFEND:
                    color = YELLOW
                case Orders.HARASS:
                    color = BLUE
                case Orders.CHASE_BUILDINGS:
                    color = LIGHTBLUE
                case Orders.ATTACK_NEAREST_BASE:
                    color = PURPLE
                case Orders.KILL_BUILDINGS:
                    color = PURPLE
                case Orders.CHASE_BUILDINGS:
                    color = PURPLE
                case Orders.REGROUP:
                    color = WHITE
                case _:
                    color = WHITE
            army_descriptor: str = f'[{army.orders.__repr__()}] (S: {army.army_supply()}, D: {self.get_closest_army_distance(army)})'
            radius: float = army.army_supply() / 50 + 2
            self.draw_sphere_on_world(army.units.center, radius, color)
            self.draw_text_on_world(army.units.center, army_descriptor, color)

    def draw_sphere_on_world(self, pos: Point2, radius: float = 2, draw_color: tuple = (255, 0, 0)):
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_sphere_out(
            Point3((pos.x, pos.y, z_height)), 
            radius, color=draw_color
        )

    def draw_text_on_world(self, pos: Point2, text: str, draw_color: tuple = (255, 102, 255), font_size: int = 14) -> None:
        z_height: float = self.bot.get_terrain_z_height(pos)
        self.bot.client.debug_text_world(
            text,
            Point3((pos.x - 2, pos.y, z_height)),
            color=draw_color,
            size=font_size,
        )

    async def attack(self):
        marines: Units = self.bot.units(UnitTypeId.MARINE).ready
        medivacs: Units = self.bot.units(UnitTypeId.MEDIVAC).ready
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        army_supply: int = 0
        army = (marines + medivacs)
        for unit in army:
            army_supply += supply[unit.type_id]

        for medivac in medivacs:
            await self.micro_medivac(medivac, marines)

        for marine in marines:            
            enemy_units: Units = self.bot.enemy_units.filter(lambda unit: not unit.is_structure and unit.can_be_attacked and unit.type_id not in dont_attack)
            enemy_towers: Units = self.bot.enemy_structures.filter(lambda unit: unit.type_id in tower_types)
            enemy_units += enemy_towers
            enemy_buildings: Units = self.bot.enemy_structures.filter(lambda unit: unit.can_be_attacked)
            # local_army: Units = army.filter(lambda unit: unit.distance_to(marine) <= 20)
            # local_army_supply: float = units_supply(local_army)

            enemy_units_in_range: Units = enemy_units.filter(
                lambda unit: marine.target_in_range(unit)
            )
            enemy_units_in_sight: Units = enemy_units.filter(
                lambda unit: unit.distance_to(marine) <= 20 
            )
            enemy_units_outside_of_range: Units = enemy_units.filter(
                lambda unit: not marine.target_in_range(unit)
            )
            enemy_buildings_in_range: Units = enemy_buildings.filter(
                lambda unit: marine.target_in_range(unit)
            )
            enemy_buildings_outside_of_range: Units = enemy_buildings.filter(
                lambda unit: not marine.target_in_range(unit)
            )

            # TODO: This only if we're taking a fight
            # If units in sight, should be stimmed if above 25 hp
            # For building we only stim if high on life
            if (
                (enemy_units_in_sight and marine.health >= 25 or (enemy_buildings_in_range and marine.health >= 45))
                and self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                and not marine.has_buff(BuffId.STIMPACK)
            ):
                marine(AbilityId.EFFECT_STIM_MARINE)


            # if panic mode, should defend
            # if my army supply is above opponent known army, take the fight
            # if (local_army_supply > self.known_enemy_army.army_supply()):
                # pass
            
            # If units in range, attack the one with the least HPs, closest if tied
            if (enemy_units_in_range) :
                self.micro(marine, enemy_units_in_range)
            elif (enemy_units_in_sight and army_supply >= self.known_enemy_army.army_supply()) :
                marine.attack(enemy_units_in_sight.closest_to(marine))
            elif (enemy_buildings_in_range) :
                marine.attack(enemy_buildings_in_range.closest_to(marine))
            elif (marines.amount >= 10 and army_supply >= self.known_enemy_army.army_supply()) :
                # find nearest opposing townhalls
                
                enemy_workers: Units = self.bot.enemy_units.filter(lambda unit: unit.type_id in worker_types)
                enemy_bases: Units = self.bot.enemy_structures.filter(lambda structure: structure.type_id in hq_types)
                close_army: Units = army.closest_n_units(enemy_main_position, army.amount // 2)

                # if enemy workers in sight, focus them
                if (enemy_workers.amount >= 1):
                    marine.attack(enemy_workers.closest_to(marine))

                # group first
                elif (marine.distance_to(close_army.center) > 6):
                    marine.move(close_army.center)
                
                # attack nearest base
                elif (enemy_bases.amount >= 1):
                    marine.attack(enemy_bases.closest_to(marine))
                
                # attack nearest building
                elif (enemy_buildings_outside_of_range.amount >= 1):
                    marine.attack(enemy_buildings_outside_of_range.closest_to(marine))
                
                # attack enemy location
                else:
                    marine.attack(enemy_main_position)
            elif (
                enemy_units_outside_of_range.amount >= 1
                and self.bot.townhalls.amount >= 1
            ):
                distance_to_hq: float = enemy_units_outside_of_range.closest_distance_to(self.bot.townhalls.first)
                distance_to_oppo: float = enemy_units_outside_of_range.closest_distance_to(enemy_main_position)
                
                # meet revealed enemy outside of range if they are in our half of the map
                if (distance_to_hq < distance_to_oppo):
                    marine.move(enemy_units_outside_of_range.closest_to(marine))
                else:
                    self.retreat(marine)
            else:
                self.retreat(marine)

    def stim(self, army: Units, local_threats: Units, local_enemy_buildings: Units):
        for unit in army:
            if (unit.type_id != UnitTypeId.MARINE):
                break
            # If units in sight, should be stimmed if above 25 hp
            # For building we only stim if high on life
            if (
                (local_threats and unit.health >= 25 or (local_enemy_buildings and unit.health >= 45))
                and self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
                and not unit.has_buff(BuffId.STIMPACK)
            ):
                unit(AbilityId.EFFECT_STIM_MARINE)
    
    async def micro(self, unit: Unit, local_army: Units):
        enemy_units_in_range: Units = self.bot.enemy_units.filter(
                lambda enemy_unit: (
                    unit.target_in_range(enemy_unit)
                    and unit.can_be_attacked
                    and unit.type_id not in dont_attack
                )
        )
        if (unit.type_id == UnitTypeId.MARINE):
            self.micro_marine(unit, enemy_units_in_range)
        elif(unit.type_id == UnitTypeId.MEDIVAC):
            await self.micro_medivac(unit, local_army)

    async def micro_medivac(self, medivac: Unit, local_army: Units):
        enemy_main_position: Point2 = self.bot.enemy_start_locations[0]
        # if not boosting, boost
        available_abilities = (await self.bot.get_available_abilities([medivac]))[0]
        if AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS in available_abilities:
            medivac(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
        
        # heal closest damaged ally
        damaged_allies: Units = self.bot.units.filter(
            lambda unit: (
                unit.is_biological
                and unit.health_percentage < 1
            )
        )

        if (damaged_allies.amount >= 1):
            medivac(AbilityId.MEDIVACHEAL_HEAL,damaged_allies.closest_to(medivac))
        else:
            closest_marines: Units = local_army.closest_n_units(enemy_main_position, local_army.amount // 2)
            if (closest_marines.amount >= 1):
                medivac.move(closest_marines.center)
            elif (self.bot.townhalls.amount >= 1):
                medivac.move(self.bot.townhalls.closest_to(enemy_main_position))
    
    def get_closest_army_distance(self, army: Army):
        if (self.armies.__len__() < 2):
            return -1
        other_armies = list(filter(lambda other_army: other_army.center != army.center, self.armies))
        closest_distance_to_other: float = army.center.distance_to(other_armies[0].center)
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < closest_distance_to_other):
                closest_distance_to_other = army.center.distance_to(other_army.center)
        return round(closest_distance_to_other, 1)
                


    async def detect_panic(self):
        panic_mode: bool = False
        # if enemies in range of a CC, activate panic mode
        for cc in self.bot.townhalls:
            threats = (
                self.bot.enemy_units + self.bot.enemy_structures
            ).filter(lambda unit: unit.distance_to(cc) <= 12)
            
            if (threats.amount >= 1):
                panic_mode = True
                break
        if self.bot.panic_mode != panic_mode:
            print("Panic mode:", panic_mode)
            self.bot.panic_mode = panic_mode

    async def detect_enemy_army(self):
        enemy_units: Units = self.bot.enemy_units
        self.known_enemy_army.detect_units(enemy_units)
            
    def unit_died(self, unit_tag: int):
        if unit_tag not in self.known_enemy_army.units.tags:
            return
        self.known_enemy_army.remove_by_tag(unit_tag)
        enemy_army: dict = self.known_enemy_army.recap()
        print("remaining enemy units :", enemy_army)

    def away(selected: Unit, enemy: Unit, distance: int = 2):
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        return selected_position.towards(target, distance)

    def move_away(selected: Unit, enemy: Unit, distance: int = 2):
        # print("Moving away 1 from 2", selected.name, enemy.name)
        selected_position: Point2 = selected.position
        offset: Point2 = selected_position.negative_offset(enemy.position)
        target: Point2 = selected_position.__add__(offset)
        selected.move(selected_position.towards(target, distance))