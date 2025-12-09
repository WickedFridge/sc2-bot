import math
from typing import List
from bot.combat.micro import Micro
from bot.combat.threats import Threat
from bot.macro.expansion import Expansion
from bot.strategy.strategy_types import Situation
from bot.superbot import Superbot
from bot.utils.ability_tags import AbilityRepair
from bot.utils.army import Army
from bot.utils.unit_supply import get_unit_supply
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types, menacing

class Base:
    bot: Superbot
    cc: Unit
    threat: Threat
    buildings: Units
    workers: Units
    units: Units
    enemy_units: Units
    enemy_structures: Units
    BASE_SIZE: int = 20
    REPAIR_THRESHOLD: float = 0.6
    MAX_INDIVIDUAL_REPAIRERS: int = 3
    RANGE_THRESHOLD: float = 1.5

    def __init__(self, bot: Superbot, cc: Unit, threat: Threat) -> None:
        self.bot = bot
        self.cc = cc
        self.threat = threat
        self.buildings = Units([cc], bot)
        self.workers = Units([], bot)
        self.units = Units([], bot)
        self.enemy_units = Units([], bot)
        self.enemy_structures = Units([], bot)
        
    @property
    def position(self) -> Point2:
        return self.cc.position
    
    @property
    def available_workers(self) -> Units:
        return self.workers.filter(lambda unit: unit.is_collecting or unit.is_moving or unit.is_idle)

    @property
    def full_available_workers(self) -> Units:
        return self.bot.workers.filter(lambda unit: unit.is_collecting or unit.is_moving or unit.is_idle)

    def distance_to(self, position: Unit | Point2) -> float:
        return self.buildings.closest_distance_to(position.position)
    
    def threat_detection(self) -> Threat:
        # we only detect towers in the main and b2 as canon rush
        enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: (
                (
                    unit.type_id in tower_types
                    or unit.type_id == UnitTypeId.PYLON
                ) and (
                    unit.distance_to(self.bot.expansions.b2.position) <= self.BASE_SIZE
                    or unit.distance_to(self.bot.expansions.main.position) <= self.BASE_SIZE
                )
            )
        )
        if (enemy_towers.amount >= 1):
            match(enemy_towers.random.type_id):
                case UnitTypeId.PYLON:
                    return Threat.CANON_RUSH
                case UnitTypeId.PHOTONCANNON:
                    return Threat.CANON_RUSH
                case UnitTypeId.BUNKER:
                    return Threat.BUNKER_RUSH
                case _:
                    return Threat.HARASS
                
        local_enemy_units: Units = self.enemy_units.filter(lambda unit: unit.can_attack)
        if (local_enemy_units.amount == 0):
            return Threat.NO_THREAT

        # Every base is under attack when there's a cheese ling drone going on
        if (self.bot.scouting.situation == Situation.CHEESE_LING_DRONE):
            return Threat.ATTACK
        
        enemy_workers_harassing: Units = self.enemy_units.filter(lambda unit: unit.type_id in worker_types)
        if (enemy_workers_harassing.amount >= 1):
            return Threat.WORKER_SCOUT
        
        # local units are bunkers and units that are close to any of our buildings
        local_units: Units = self.buildings([UnitTypeId.BUNKER, UnitTypeId.PLANETARYFORTRESS]) + self.units.filter(
            lambda unit: unit.type_id not in worker_types
        )
        local_army: Army = Army(local_units, self.bot)
        local_enemy_army: Army = Army(local_enemy_units, self.bot)

        if (local_enemy_army.supply == 0):
            return Threat.NO_THREAT
        if (local_army.supply == 0 and local_enemy_army.supply >= 10 * self.cc.health_percentage):
            return Threat.OVERWHELMED
        if (local_army.supply < local_enemy_army.supply):
            return Threat.ATTACK
        if (local_army.center.distance_to(self.position) > local_enemy_army.center.distance_to(self.position)):
            return Threat.HARASS
        return Threat.NO_THREAT
    
    
    def workers_response_to_threat(self) -> None:
        if (self.workers.amount == 0):
            return        

        match self.threat:
            case Threat.NO_THREAT:
                self.no_threat()
                
            case Threat.OVERWHELMED:
                self.evacuate()
            
            case Threat.ATTACK:
                self.attack_threat()

            case Threat.WORKER_SCOUT:
                self.track_enemy_scout()

            case Threat.HARASS:
                self.avoid_harass()

            case Threat.CANON_RUSH:
                self.defend_cannon_rush()

            case Threat.BUNKER_RUSH:
                self.defend_bunker_rush()
    
    def defend_bunker_rush(self) -> None:
        bunkers: Units = self.enemy_structures(UnitTypeId.BUNKER)
        # track the SCVs with 3 workers each
        self.track_enemy_scout(3)
        
        # try to destroy the constructing bunkers but commit on finished bunkers
        for bunker in bunkers:
            if (bunker.build_progress <= 0.5):
                self.pull_workers(bunker, 3)
            else:
                self.pull_workers(bunker, round((bunker.build_progress * 8)))
            
    def defend_cannon_rush(self) -> None:
        canons: Units = self.enemy_structures(UnitTypeId.PHOTONCANNON)
        pylons: Units = self.enemy_structures(UnitTypeId.PYLON)
        # track the probes with 3 workers each
        self.track_enemy_scout(3)
        # respond to canon rush
        # Pull 3 workers by tower, 4 by pylon, less if we don't have enough
        if (canons.amount == 0):
            for pylon in pylons:
                self.pull_workers(pylon, 4)

        for canon in canons:
            if (canon.build_progress <= 0.5):
                self.pull_workers(canon, 3)
            else:
                self.pull_workers(canon, round((canon.build_progress * 8)))

    def avoid_harass(self) -> None:
        # we don't move away if we're repairing or full life
        for worker in self.workers.filter(lambda unit: not unit.is_repairing and unit.health_percentage < 1):
            enemies_facing_almost_in_range: Units = self.enemy_structures + self.enemy_units.filter(
                lambda enemy: (
                    enemy.is_facing(worker, math.pi / 2)
                    and enemy.distance_to(worker) < enemy.ground_range + enemy.radius + worker.radius + self.RANGE_THRESHOLD
                )
            )
            # we don't move away from unit not dangerous to us
            if (enemies_facing_almost_in_range.amount == 0):
                return
            Micro.move_away(worker, enemies_facing_almost_in_range.center, self.RANGE_THRESHOLD / 2)

    def track_enemy_scout(self, max_scv_attacking = 1) -> None:
        for enemy_scout in self.enemy_units.filter(lambda unit: unit.type_id in worker_types):
            if (self.full_available_workers.amount == 0):
                return
            # if no scv is already chasing
            attacking_workers: Units = self.workers.filter(
                lambda unit: unit.is_attacking and unit.order_target == enemy_scout.tag
            )
            if (attacking_workers.amount < max_scv_attacking):
                # pull 1 scv to follow it
                closest_worker: Unit = self.full_available_workers.closest_to(enemy_scout)
                closest_worker.attack(enemy_scout)
        
        damaged_workers = self.workers.filter(
            lambda unit: unit.health_percentage < 1
        ).sorted(lambda unit: unit.health_percentage)

        max_workers_repairing: int = max(5, self.workers.amount / 3)
        self.repair_units(self.available_workers, damaged_workers, max_workers_repairing)

    def get_worker_amount_to_pull(self, enemy_units: Units, attackable_enemy_units: Units, bunkers: Units) -> int:
        specific_amount_to_pull: dict[UnitTypeId, int] = {
            UnitTypeId.REAPER: 2.5,
            UnitTypeId.MARINE: 1.5,
            UnitTypeId.MARAUDER: 3.5,
            UnitTypeId.ZERGLING: 1.5,
            UnitTypeId.DRONE: 1,
            UnitTypeId.BANELING: 0,
            UnitTypeId.ROACH: 3,
            UnitTypeId.HELLION: 2.5,
            UnitTypeId.ZEALOT: 4,
            UnitTypeId.STALKER: 4,
            UnitTypeId.IMMORTAL: 5,
        }
        
        amount_to_pull: float = 0
        for enemy_unit in attackable_enemy_units:
            if (enemy_unit.type_id in specific_amount_to_pull):
                amount_to_pull += specific_amount_to_pull[enemy_unit.type_id]
            else:
                amount_to_pull += get_unit_supply(enemy_unit) * 2

        amount_to_pull = round(amount_to_pull)

        # if we don't have a bunker, just pull everything
        if (bunkers.amount == 0):
            return amount_to_pull

        # otherwise it depends on the life of the bunker and the amount of enemy in range
        # 2 if no units
        amount_to_pull: int = 2
        for bunker in bunkers:
            enemies_in_range: Units = enemy_units.filter(lambda unit: unit.target_in_range(bunker))
            if (enemies_in_range.amount >= 1 or bunker.health_percentage < 1):
                # add between 2 and 6 if there's units around and life is down
                amount_to_pull += 4 + 2 * (math.cos(math.pi * bunker.health_percentage))
                
        return amount_to_pull

    
    def attack_threat(self) -> None:
        if (self.available_workers.amount == 0):
            print("no workers to pull, o7")
            return
        
        SCV_HEALTH_THRESHOLD: int = 15
        local_enemy_units: Units = self.enemy_units.closer_than(self.BASE_SIZE, self.position).filter(lambda unit: unit.can_attack or unit.type_id in menacing)
        attackable_enemy_units: Units = local_enemy_units.filter(
            lambda unit: unit.is_flying == False and unit.can_be_attacked
        ).sorted(lambda unit: unit.health + unit.shield)

        bunkers: Units = self.buildings(UnitTypeId.BUNKER)
        max_worker_to_pull: int = self.get_worker_amount_to_pull(local_enemy_units, attackable_enemy_units, bunkers)
        workers_pulled: Units = self.workers.filter(lambda unit: unit.is_attacking)
        workers_to_pullback: Units = workers_pulled.filter(lambda unit: (unit.health < SCV_HEALTH_THRESHOLD))

        # pull workers back to mining if not needed
        if (workers_to_pullback.amount >= 1):
            print(f'pulling {workers_to_pullback.amount} workers back to mining')
        for worker in workers_to_pullback:
            closest_mineral: Unit = self.bot.mineral_field.closest_to(self.position)
            worker.gather(closest_mineral)

        additional_workers_needed: int = max_worker_to_pull - (workers_pulled.amount - workers_to_pullback.amount)

        if (additional_workers_needed <= 0):
            return
        
        print(f'pulling {additional_workers_needed} workers')
        
        workers_to_pull: Units = self.available_workers.filter(
            lambda unit: (unit.health >= SCV_HEALTH_THRESHOLD)
        ).sorted(
            lambda unit: (-unit.health_percentage, unit.distance_to(attackable_enemy_units.center))
        ).take(additional_workers_needed)
        

        for worker in workers_to_pull:
            enemy_units_not_on_main_ramp: Units = attackable_enemy_units.filter(
                lambda unit: (
                    unit.position.distance_to(self.bot.main_base_ramp.top_center) > 5
                    and unit.position.distance_to(self.bot.main_base_ramp.bottom_center) > 5
                )
            )
            wall_depots_lifted: Units = self.bot.structures(UnitTypeId.SUPPLYDEPOT).filter(
                lambda unit: (
                    unit.type_id != UnitTypeId.SUPPLYDEPOTLOWERED
                    and unit.position.distance_to(self.bot.main_base_ramp.top_center) <= 5
                )
            )
            # Don't pull workers from the main if the wall is up and units are outside
            
            if (
                self.bot.expansions.closest_to(worker).position == self.bot.expansions.main.position
                and enemy_units_not_on_main_ramp.amount == 0
                and wall_depots_lifted.amount >= 1
            ):
                return
            
            # if we're being attacked by flying/invisible units, move away if we're in range
            if (attackable_enemy_units.amount == 0):
                closest_enemy: Unit = local_enemy_units.closest_to(worker)
                if (closest_enemy.target_in_range(worker)):
                    Micro.move_away(worker, closest_enemy.position, 1)
            else:
                # attack enemy units in range if we can (choose the weakest one)
                enemy_in_range: Units = attackable_enemy_units.filter(
                    lambda unit: unit.distance_to(worker) <= 1
                )
                
                # Move towards the bunker if there is one and we can't attack
                if (
                    self.buildings(UnitTypeId.BUNKER).filter(lambda unit: unit.build_progress >= 0.95).amount >= 1
                    and (
                        enemy_in_range.amount == 0
                        or worker.weapon_cooldown > 0
                    )
                ):
                    bunker: Unit = self.buildings(UnitTypeId.BUNKER).closest_to(worker)
                    worker.move(bunker.position.towards(worker))
                elif (worker.type_id != UnitTypeId.MULE):
                    target: Unit = enemy_in_range.first if enemy_in_range.amount >= 1 else attackable_enemy_units.first
                    worker.attack(target)
                
    def workers_attack(self, workers: Units) -> List[int]:
        """
        Attack with workers

        Returns the list of tags of workers that attacked
        """
        worker_orders: List[int] = []
        for worker in workers.filter(lambda worker: worker.weapon_ready):
            attackable_units: Units = self.bot.enemy_units.filter(
                lambda unit: worker.target_in_range(unit)
            ).sorted(lambda unit: unit.health, True)
            if (attackable_units.amount >= 1):
                worker.attack(attackable_units.first)
                worker_orders.append(worker.tag)
        return worker_orders
    
    def workers_repair(self, workers: Units) -> List[int]:
        """
        repair with workers

        Returns the list of tags of workers that repaired
        """
        if (self.bot.minerals <= 0 or workers.amount == 0):
            return []
        
        all_workers: Units = self.bot.workers
        damaged_workers: Units = all_workers.filter(lambda worker: worker.health_percentage < 1).sorted(lambda worker: worker.health_percentage)
        if (damaged_workers.amount == 0):
            return []
        
        worker_orders: List[int] = []
        for damaged_worker in damaged_workers:
            range: float = damaged_worker.radius * 2
            close_workers: Units = workers.filter(lambda worker: worker.tag not in worker_orders).closer_than(range, damaged_worker)
            for close_worker in close_workers:
                close_worker.repair(damaged_worker)
                worker_orders.append(close_worker.tag)
            
        return worker_orders
    
    # def handle_cheese_ling_drone(self):
    #     all_workers: Units = self.bot.workers
    #     if (all_workers.amount == 0):
    #         return
    #     main: Expansion = self.bot.expansions.main
    #     central_mineral_patch: Unit = self.bot.mineral_field.closest_to(main.mineral_line)
        
    #     worker_orders: List[int] = []

    #     # 1 - each worker that's on cooldown and can attack something, attack
    #     worker_orders.extend(self.workers_attack(all_workers))
        
    #     # 2 - if a worker can repair another worker, do it
    #     other_workers: Units = all_workers.filter(lambda worker: worker.tag not in worker_orders)
    #     worker_orders.extend(self.workers_repair(other_workers))
        
        
    #     # 3 - if my workers are near the mineral lines and unstacked, stack them
    #     other_workers: Units = other_workers.filter(lambda worker: worker.tag not in worker_orders)
    #     if (other_workers.center.distance_to(main.mineral_line) < 10):
    #         if (other_workers.furthest_distance_to(other_workers.center) > 1):
    #             for worker in other_workers:
    #                 worker.gather(central_mineral_patch)
    #             return
    
    def evacuate(self) -> None:
        # find closest safe expansion
        retreat_base: Expansion = None
        safe_expansions: Units = self.bot.expansions.safe
        if (safe_expansions.amount == 0):
            retreat_base = self.bot.expansions.main
        else:
            retreat_base = safe_expansions.closest_to(self.position)
        
        # move all workers to the closest expansion
        for worker in self.workers:
            if (retreat_base.mineral_fields.amount):
                worker.gather(retreat_base.mineral_fields.random)
            else:
                worker.move(retreat_base.mineral_line)
        
        # if cc isn't a PF or the main, lift it
        if (self.cc.type_id == UnitTypeId.PLANETARYFORTRESS or self.cc.position == self.bot.expansions.main.position):
            return
        print("Lifting CC to evacuate")
        if (self.cc.type_id == UnitTypeId.ORBITALCOMMAND):
            self.cc.stop()
            self.cc(AbilityId.LIFT_ORBITALCOMMAND)
        else:
            self.cc.stop()
            self.cc(AbilityId.LIFT_COMMANDCENTER)
    
    def no_threat(self) -> None:
        # ask all chasing SCVs to stop
        attacking_workers = self.workers.filter(lambda unit: unit.is_attacking)
        for attacking_worker in attacking_workers:
            attacking_worker.stop()
        
        damaged_mechanical_units = self.units.filter(
            lambda unit: (unit.is_mechanical and unit.health_percentage < self.REPAIR_THRESHOLD)
        ).sorted(lambda unit: unit.health_percentage)

        max_workers_repairing: int = max(5, self.workers.amount / 3)
        self.repair_units(self.available_workers, damaged_mechanical_units, max_workers_repairing)

    def pull_workers(self, target: Unit, amount: int) -> None:
        workers_attacking_tower: Units = self.bot.workers.filter(
            lambda unit: unit.is_attacking and unit.order_target == target.tag
        )

        if (workers_attacking_tower.amount == amount):
            return
        if (workers_attacking_tower.amount > amount):
            # stop excess workers
            workers_attacking_reversed: Units = workers_attacking_tower.sorted_by_distance_to(target, True)
            workers_to_stop: Units = workers_attacking_reversed.take(workers_attacking_tower.amount - amount)
            for worker in workers_to_stop:
                worker.stop()
            return

        workers_pulled: Units = self.full_available_workers.sorted_by_distance_to(target).take(amount - workers_attacking_tower.amount)
        
        for worker_pulled in workers_pulled:
            worker_pulled.attack(target)

    def repair_units(self, avaialble_workers: Units, damaged_mechanical_units: Units, max_workers_repairing: int = 8):
        if (damaged_mechanical_units.amount == 0 or avaialble_workers.amount == 0):
            return
        workers_repairing: Units = self.bot.workers.filter(
            lambda unit: (
                len(unit.orders) >= 1
                and unit.orders[0].ability.id in AbilityRepair
            )
        )

        workers_repairing_amount: int = workers_repairing.amount
        
        for damaged_unit in damaged_mechanical_units:
            if (workers_repairing_amount >= max_workers_repairing):
                return
            workers_repairing_unit: Units = workers_repairing.filter(
                lambda unit: (unit.order_target == damaged_unit.tag)
            )
            
            if (workers_repairing_unit.amount >= self.MAX_INDIVIDUAL_REPAIRERS):
                continue
            
            close_workers: Units = avaialble_workers.filter(
                lambda unit: unit.distance_to(damaged_unit) < 10 and unit.tag != damaged_unit.tag
            ).sorted_by_distance_to(damaged_unit)
            
            if (close_workers.amount >= 1):
                close_workers.first.repair(damaged_unit)
                workers_repairing_amount += 1