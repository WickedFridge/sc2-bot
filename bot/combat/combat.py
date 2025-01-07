import math
from typing import List, Set
from bot.combat.execute_orders import Execute
from bot.combat.micro import Micro
from bot.combat.orders import Orders
from bot.combat.threats import Threat
from bot.utils.army import Army
from bot.utils.colors import BLUE, GREEN, LIGHTBLUE, PURPLE, RED, WHITE, YELLOW
from bot.utils.base import Base
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, dont_attack, bio


class Combat:
    bot: BotAI
    execute: Execute
    workers_pulled_amount: int = 0
    known_enemy_army: Army
    armies: List[Army] = []
    bases: List[Base] = []
    panic: bool = False
    # threats: dict[Point2, Threat] = []
    
    def __init__(self, bot) -> None:
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
    def armored_supply(self) -> float:
        result: float = 0
        for army in self.armies:
            result += army.armored_supply
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

    async def detect_panic(self):
        panic_mode: bool = False
        # if enemies in range of a CC, activate panic mode
        for cc in self.bot.townhalls:
            threats = (
                self.bot.enemy_units + self.bot.enemy_structures
            ).filter(lambda unit: unit.distance_to(cc) <= 10)
            
            if (threats.amount >= 1):
                panic_mode = True
                break
        if self.bot.panic_mode != panic_mode:
            print("Panic mode:", panic_mode)
            self.bot.panic_mode = panic_mode

    async def detect_threat(self):
        self.bases = []
        # if enemies in range of a CC, activate panic mode
        for cc in self.bot.townhalls:
            enemy_towers: Units = self.bot.enemy_structures.filter(
                lambda unit: unit.type_id in tower_types and unit.distance_to(cc) <= 20
            )
            if (enemy_towers.amount >= 1):
                self.bases.append(Base(self.bot, cc, Threat.CANONRUSH))
                break

            local_enemy_units: Units = self.bot.enemy_units.filter(
                lambda unit: unit.distance_to(cc) <= 20 and unit.can_attack
            )
            if (local_enemy_units.amount == 0):
                self.bases.append(Base(self.bot, cc, Threat.NO_THREAT))
                break

            if (local_enemy_units.amount == 1 and local_enemy_units.random.type_id in worker_types):
                self.bases.append(Base(self.bot, cc, Threat.WORKER_SCOUT))
                break

            local_units: Units = self.bot.units.filter(
                lambda unit: (
                    unit.distance_to(cc) <= 20
                    and unit.type_id not in worker_types
                    and not unit.is_structure
                )
            )
            local_army: Army = Army(local_units, self.bot)
            local_enemy_army: Army = Army(local_enemy_units, self.bot)

            if (local_army.supply == 0):
                self.bases.append(Base(self.bot, cc, Threat.ATTACK))
                break
            if (local_enemy_army.supply == 0):
                self.bases.append(Base(self.bot, cc, Threat.NO_THREAT))
                break
            if (local_army.supply < local_enemy_army.supply):
                self.bases.append(Base(self.bot, cc, Threat.ATTACK))
                break
            if (local_army.center.distance_to(cc) > local_enemy_army.center.distance_to(cc)):
                self.bases.append(Base(self.bot, cc, Threat.HARASS))
                break
            self.bases.append(Base(self.bot, cc, Threat.NO_THREAT))

    async def workers_response_to_threat(self):
        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.bot.townhalls.amount == 0):
            print("no townhalls left, o7")
            for worker in self.bot.workers:
                worker.attack(self.bot.enemy_units.closest_to(worker))
            return
        
        for base in self.bases:
            workers: Units = self.bot.workers.filter(lambda unit: unit.distance_to(base.position) < 20)
            if (workers.amount == 0):
                break
            local_enemy_units: Units = self.bot.enemy_units.filter(lambda unit: unit.distance_to(base.position) < 20)
            
            match base.threat:
                case Threat.NO_THREAT:
                    # ask all chasing SCVs to stop
                    attacking_workers = workers.filter(lambda unit: unit.is_attacking)
                    for attacking_worker in attacking_workers:
                        attacking_worker.stop()
                case Threat.ATTACK:
                    if (self.bot.workers.collecting.amount == 0):
                        print("no workers to pull, o7")
                        break
                    for worker in workers.collecting:
                        worker.attack(local_enemy_units.closest_to(worker))
                case Threat.WORKER_SCOUT:
                    enemy_scout = local_enemy_units.random                    
                    closest_worker: Unit = workers.closest_to(enemy_scout)
                    # if no scv is already chasing
                    attacking_workers: Unit = workers.filter(
                        lambda unit: unit.is_attacking and unit.order_target == enemy_scout.tag
                    )
                    if (attacking_workers.amount == 0):
                        # pull 1 scv to follow it
                        closest_worker.attack(enemy_scout)
                case Threat.HARASS:
                    for worker in workers:
                        closest_enemy: Unit = local_enemy_units.closest_to(worker)
                        if (closest_enemy.distance_to(worker) < closest_enemy.ground_range + 2):
                            Micro.move_away(worker, local_enemy_units.center, 1)
                case Threat.CANONRUSH:
                    enemy_towers: Units = self.bot.enemy_structures.filter(
                        lambda unit: unit.type_id in tower_types and unit.distance_to(base.position) <= 20
                    )
                    # respond to canon/bunker/spine rush
                    for tower in enemy_towers:
                        # Pull 3 workers by tower by default, less if we don't have enough
                        # Only pull workers if we don't have enough workers attacking yet
                        workers_attacking_tower = workers.filter(
                            lambda unit: unit.is_attacking and unit.order_target == tower.tag
                        ).amount
                        if (workers_attacking_tower >= 3):
                            break

                        amount_to_pull: int = 3 - workers_attacking_tower
                        closest_workers: Units = workers.collecting.sorted_by_distance_to(tower)

                        workers_pulled: Units = closest_workers[:amount_to_pull] if closest_workers.amount >= amount_to_pull else closest_workers

                        for worker_pulled in workers_pulled:
                            worker_pulled.attack(tower)
    
    async def pull_workers(self):
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
                elif (closest_worker.distance_to(threat) <= 10):
                    closest_worker.attack(threat)

            workers_pulled_amount: int = self.bot.workers.filter(lambda unit: unit.is_attacking).amount
            if (workers_pulled_amount != self.workers_pulled_amount):
                self.workers_pulled_amount = workers_pulled_amount
                print(workers_pulled_amount, "workers pulled")

    async def select_orders(self):
        # update local armies
        # Scale radius in function of army supply
        army_radius: float = 0.15 * self.army_supply + 15

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
            local_enemy_units: Units = self.get_local_enemy_units(army.units.center)
            local_enemy_buildings = self.get_local_enemy_buildings(army.units.center)
            local_enemy_workers: Units = self.bot.enemy_units.filter(
                lambda unit: (
                    unit.distance_to(army.units.center) <= 30
                    and unit.can_be_attacked
                    and unit.type_id in worker_types
                )
            )

            army_supply: float = army.supply
            local_enemy_army: Army = Army(local_enemy_units, self.bot)
            local_enemy_supply: float = local_enemy_army.supply
            unseen_enemy_army: Army = Army(self.known_enemy_army.units_not_in_sight, self.bot)
            unseen_enemy_supply: float = unseen_enemy_army.supply
            potential_enemy_supply: float = local_enemy_supply + unseen_enemy_supply
            closest_building_to_enemies: Unit = None if global_enemy_units.amount == 0 else self.bot.structures.in_closest_distance_to_group(global_enemy_units)
            distance_building_to_enemies: float = 1000 if global_enemy_units.amount == 0 else global_enemy_units.closest_distance_to(closest_building_to_enemies)
            closest_army_distance: float = self.get_closest_army_distance(army)
            
            # if local_army_supply > local threat
            # attack local_threat if it exists
            if (local_enemy_supply + local_enemy_buildings.amount >= 1):
                
                
                # if enemy is a threat, micro if we win or we panic, retreat if we don't
                if (
                    army_supply >= local_enemy_supply
                    or self.bot.panic_mode
                    or distance_building_to_enemies <= 10
                ):
                    army.orders = Orders.FIGHT
                else:
                    local_enemy_units.sort(key=lambda unit: unit.real_speed, reverse=True)
                    local_enemy_speed: Unit = local_enemy_units.first.real_speed
                    closest_unit: Unit = army.units.closest_to(local_enemy_units.first)
                    army.orders = Orders.RETREAT
                    
                    # TODO: fix "enemy too fast"
                    # if (local_enemy_speed > army.speed and local_enemy_units.first.is_facing(closest_unit, math.pi / 2)):
                    #     print("enemy too fast, taking the fight")
                    #     army.orders = Orders.FIGHT
                    # else:
                    #     print(f'not fighting against {local_enemy_supply} supply')
                    #     print("local_enemy_army:", local_enemy_army.recap)
                    #     print("unseen_enemy_army:", unseen_enemy_army.recap)
                    #     army.orders = Orders.RETREAT
                    
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
                and closest_army_distance <= 15
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
                # army.orders = Orders.RETREAT

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
    
    async def handle_bunkers(self):
        for bunker in self.bot.structures(UnitTypeId.BUNKER).ready:
            enemy_units_in_range: Units = self.bot.enemy_units.filter(
                lambda unit: unit.distance_to(bunker) <= 7
            )
            if (enemy_units_in_range.amount == 0):
                if(bunker.cargo_used == 0):
                    return
                bunker(AbilityId.UNLOADALL_BUNKER)
                return
            enemy_units_in_range: Units = self.bot.enemy_units.filter(
                lambda unit: bunker.target_in_range(unit)
            )
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
            bio_in_range: List[Unit] = bio_close_by.filter(lambda unit: unit.distance_to(bunker) <= 3)[:4]
            if (bio_in_range.__len__() == 0):
                bio_close_by.sort(key = lambda unit: unit.distance_to(bunker))
                bio_moving_towards_bunker: List[Unit] = bio_close_by.copy()[:4]
                for bio_unit in bio_moving_towards_bunker:
                    bio_unit.move(bunker)
                    return
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
            army_descriptor: str = f'[{army.orders.__repr__()}] (S: {army.supply})'
            radius: float = army.supply * 0.15 + 1
            self.draw_sphere_on_world(army.units.center, radius, color)
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
                case Threat.CANONRUSH:
                    color = PURPLE
                case _:
                    color = WHITE
            base_descriptor: str = f'[{base.threat.__repr__()}]'
            radius: float = 15
            # self.draw_sphere_on_world(base.position, radius, color)
            self.draw_text_on_world(base.position, base_descriptor, color)

    async def debug_selection(self):
        selected_units: Units = self.bot.units.selected
        for unit in selected_units:
            order = "Idle" if unit.is_idle else unit.orders[0].ability.id.__str__()
            self.draw_text_on_world(unit.position, order)

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
    
    def get_closest_army_distance(self, army: Army):
        if (self.armies.__len__() < 2):
            return -1
        other_armies = list(filter(lambda other_army: other_army.center != army.center, self.armies))
        closest_distance_to_other: float = army.center.distance_to(other_armies[0].center)
        for other_army in other_armies:
            if (army.center.distance_to(other_army.center) < closest_distance_to_other):
                closest_distance_to_other = army.center.distance_to(other_army.center)
        return round(closest_distance_to_other, 1)
                
    def get_local_enemy_units(self, position: Point2) -> Units:
        global_enemy_units: Units = self.bot.enemy_units.filter(
            lambda unit: (
                unit.can_be_attacked
                and unit.type_id not in dont_attack
            )
        )
        local_enemy_units: Units = global_enemy_units.filter(
            lambda unit: unit.distance_to(position) <= 25
        )
        local_enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.type_id in tower_types and unit.can_be_attacked
        )
        return local_enemy_units + local_enemy_towers

    def get_local_enemy_buildings(self, position: Point2) -> Units:
        local_enemy_buildings: Units = self.bot.enemy_structures.filter(
            lambda unit: unit.distance_to(position) <= 10 and unit.can_be_attacked
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