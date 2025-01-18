from bot.combat.micro import Micro
from bot.combat.threats import Threat
from bot.utils.ability_tags import AbilityRepair
from bot.utils.army import Army
from bot.utils.base import Base
from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types

BASE_SIZE: int = 20
THREAT_DISTANCE: int = 8

class Macro:
    bot: BotAI

    def __init__(self, bot) -> None:
        self.bot = bot

    async def detect_threat(self):
        self.bases = []
        # if enemies in range of a CC, activate panic mode
        for cc in self.bot.townhalls:
            local_buildings: Units = self.bot.structures.filter(lambda unit: unit.distance_to(cc.position) < BASE_SIZE)
            enemy_towers: Units = self.bot.enemy_structures.filter(
                lambda unit: (
                    unit.type_id in tower_types
                    and local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
                    # and unit.distance_to(cc) <= BASE_SIZE
                )
            )
            if (enemy_towers.amount >= 1):
                self.bases.append(Base(self.bot, cc, Threat.CANONRUSH))
                break

            local_enemy_units: Units = self.bot.enemy_units.filter(
                lambda unit: local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE and unit.can_attack
            )
            enemy_workers_harassing: Units = self.bot.enemy_units.filter(
                lambda unit: (
                    local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
                    and unit.can_attack
                    and unit.type_id in worker_types
                )
            )
            if (local_enemy_units.amount == 0):
                self.bases.append(Base(self.bot, cc, Threat.NO_THREAT))
                break

            if (enemy_workers_harassing.amount >= 1):
                self.bases.append(Base(self.bot, cc, Threat.WORKER_SCOUT))
                break

            local_units: Units = self.bot.units.filter(
                lambda unit: (
                    local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
                    and unit.type_id not in worker_types
                    and not unit.is_structure
                )
            )
            local_army: Army = Army(local_units, self.bot)
            local_enemy_army: Army = Army(local_enemy_units, self.bot)

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
            local_buildings: Units = self.bot.structures.filter(lambda unit: unit.distance_to(base.position) <= BASE_SIZE)
            in_threat_distance = lambda unit: local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
            workers: Units = self.bot.workers.filter(in_threat_distance)
            if (workers.amount == 0):
                break
            local_buildings: Units = self.bot.structures.filter(in_threat_distance)
            local_enemy_units: Units = self.bot.enemy_units.filter(in_threat_distance)
            
            match base.threat:
                case Threat.NO_THREAT:
                    # ask all chasing SCVs to stop
                    attacking_workers = workers.filter(lambda unit: unit.is_attacking)
                    for attacking_worker in attacking_workers:
                        attacking_worker.stop()
                    mules: Units = self.bot.units(UnitTypeId.MULE).collecting
                    damaged_mechanical_units = self.bot.units.filter(in_threat_distance).filter(
                        lambda unit: (unit.is_mechanical and unit.health_percentage < 1)
                    )
                    self.repair_units(workers + mules, damaged_mechanical_units)
                case Threat.ATTACK:
                    if (workers.collecting.amount == 0):
                        print("no workers to pull, o7")
                        break
                    attackable_enemy_units: Units = local_enemy_units.filter(lambda unit: unit.is_flying == False and unit.can_be_attacked)
                    for worker in workers.collecting:
                        if (attackable_enemy_units.amount >= 1):
                            worker.attack(attackable_enemy_units.closest_to(worker))
                        else:
                            Micro.move_away(worker, local_enemy_units.closest_to(worker), 1)
                case Threat.WORKER_SCOUT:
                    for enemy_scout in local_enemy_units:
                        if (workers.collecting.amount == 0):
                            break
                        closest_worker: Unit = workers.collecting.closest_to(enemy_scout)
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
                            Micro.move_away(worker, closest_enemy, 1)
                case Threat.CANONRUSH:
                    enemy_towers: Units = self.bot.enemy_structures.filter(
                        lambda unit: (
                            unit.type_id in tower_types
                            and local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
                        )
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
    

    def repair_units(self, workers: Units, damaged_mechanical_units: Units):
        if(damaged_mechanical_units.amount == 0):
            return
        if (workers.amount == 0):
            print("no workers available to repair o7")
            return

        for damaged_unit in damaged_mechanical_units:
            workers_repairing_unit: Units = self.bot.workers.filter(
                lambda unit: (
                    unit.orders.__len__() >= 1
                    and unit.orders[0].ability.id in AbilityRepair
                    and unit.order_target == damaged_unit.tag
                )
            )
            max_workers_repairing: int = 1
            if (workers_repairing_unit.amount >= max_workers_repairing):
                print("max worker repairing already")
                return
            
            close_workers: Units = workers.filter(
                lambda unit: unit.distance_to(damaged_unit) < 25 and unit.tag != damaged_unit.tag
            ).collecting
            if (close_workers.amount >= 1):
                print("Repairing SCV")
                close_workers.closest_to(damaged_unit).repair(damaged_unit)

    async def split_workers(self):
        cc: Unit = self.bot.townhalls.first
        mineral_fields: Units = self.bot.mineral_field.filter(lambda unit: unit.distance_to(cc) <= 10)
        for worker in self.bot.workers:
            closest_mineral: Unit = mineral_fields.closest_to(worker)
            worker.gather(closest_mineral)
        for mineral_field in mineral_fields:
            closest_worker: Unit = self.bot.workers.closest_to(mineral_field)
            closest_worker.gather(mineral_field)

    async def mule_idle(self):
        if (self.bot.mineral_field.amount == 0):
            print("no mineral field left")
            return
        mules_idle = self.bot.units(UnitTypeId.MULE).idle
        for mule in mules_idle:
            closest_mineral_field: Unit = self.bot.mineral_field.closest_to(mule)
            mule.gather(closest_mineral_field)