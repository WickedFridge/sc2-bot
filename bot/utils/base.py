import math
from bot.combat.micro import Micro
from bot.combat.threats import Threat
from bot.superbot import Superbot
from bot.utils.ability_tags import AbilityRepair
from bot.utils.army import Army
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types

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

    def attack_threat(self) -> None:
        if (self.available_workers.amount == 0):
            print("no workers to pull, o7")
            return
        attackable_enemy_units: Units = self.enemy_units.filter(
            lambda unit: unit.is_flying == False and unit.can_be_attacked
        ).sorted(lambda unit: unit.health + unit.shield)

        for worker in self.available_workers:
            enemy_units_on_main_ramp: Units = attackable_enemy_units.filter(
                lambda unit: (
                    unit.position.distance_to(self.bot.main_base_ramp.top_center) <= 5
                    and unit.position.distance_to(self.bot.main_base_ramp.bottom_center) <= 5
                )
            )
            # Don't pull workers from the main if the wall is up and units are outside
            if (
                self.bot.expansions.closest_to(worker).position == self.bot.expansions.main.position
                and enemy_units_on_main_ramp.amount >= 1
            ):
                return
            if (attackable_enemy_units.amount >= 1):
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
                else:
                    target: Unit = enemy_in_range.first if enemy_in_range.amount >= 1 else attackable_enemy_units.first
                    worker.attack(target)
            else:
                Micro.move_away(worker, self.enemy_units.closest_to(worker), 1)
                
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