import math
from typing import List
from bot.combat.micro import Micro
from bot.combat.threats import Threat
from bot.macro.expansion import Expansion
from bot.macro.expansion_manager import Expansions
from bot.macro.speed_mining import SpeedMining
from bot.utils.ability_tags import AbilityRepair
from bot.utils.army import Army
from bot.utils.base import Base
from bot.utils.point2_functions import center
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit, UnitOrder
from sc2.units import Units
from ..utils.unit_tags import tower_types, worker_types

BASE_SIZE: int = 20
THREAT_DISTANCE: int = 8
REPAIR_THRESHOLD: float = 0.8

class Macro:
    bot: BotAI
    bases: List[Base]
    speed_mining: SpeedMining

    def __init__(self, bot: BotAI, expansions: Expansions) -> None:
        self.bot = bot
        self.expansions = expansions
        self.bases = []
        self.speed_mining = SpeedMining(bot)

    async def update_threat_level(self):
        self.bases = self.threat_detection()

    # due to speedmining, some workers sometimes bug
    async def unbug_workers(self):
        for worker in self.bot.workers.filter(lambda worker: worker.is_idle == False):
            order: UnitOrder = worker.orders[0]
            townhall_ids: List[int] = [townhall.tag for townhall in self.bot.townhalls]
            if (order.ability.id == AbilityId.MOVE and order.target in townhall_ids):
                worker.stop()
    
    def threat_detection(self) -> List[Base]:
        bases: List[Base] = []
        for cc in self.bot.townhalls:
            bases.append(Base(self.bot, cc, self.local_threat_detection(cc)))
        return bases

    def local_threat_detection(self, cc: Unit) -> Threat:
        local_buildings: Units = self.bot.structures.filter(lambda unit: unit.distance_to(cc.position) < BASE_SIZE)
        enemy_towers: Units = self.bot.enemy_structures.filter(
            lambda unit: (
                unit.type_id in tower_types
                and local_buildings.closest_distance_to(unit) <= BASE_SIZE
            )
        )
        if (enemy_towers.amount >= 1):
            match(enemy_towers.random.type_id):
                case UnitTypeId.PHOTONCANNON:
                    return Threat.CANON_RUSH
                case UnitTypeId.BUNKER:
                    return Threat.BUNKER_RUSH
                case _:
                    return Threat.HARASS

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
            return Threat.NO_THREAT

        if (enemy_workers_harassing.amount >= 1):
            return Threat.WORKER_SCOUT

        local_units: Units = self.bot.structures(UnitTypeId.BUNKER).filter(
            lambda unit: local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE 
        ) + self.bot.units.filter(
            lambda unit: (
                local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
                and unit.type_id not in worker_types
            )
        )
        local_army: Army = Army(local_units, self.bot)
        local_enemy_army: Army = Army(local_enemy_units, self.bot)

        if (local_enemy_army.supply == 0):
            return Threat.NO_THREAT
        if (local_army.supply < local_enemy_army.supply):
            return Threat.ATTACK
        if (local_army.center.distance_to(cc) > local_enemy_army.center.distance_to(cc)):
            return Threat.HARASS
        return Threat.NO_THREAT

    async def workers_response_to_threat(self):
        # if every townhalls is dead, just attack the nearest unit with every worker
        if (self.bot.townhalls.amount == 0):
            print("no townhalls left, o7")
            for worker in self.bot.workers:
                worker.attack(self.bot.enemy_units.filter(lambda unit: unit.is_flying == False).closest_to(worker))
            return
        
        for base in self.bases:
            local_buildings: Units = self.bot.structures.filter(lambda unit: unit.distance_to(base.position) <= BASE_SIZE)
            in_threat_distance = lambda unit: local_buildings.closest_distance_to(unit) <= THREAT_DISTANCE
            workers: Units = self.bot.workers.filter(in_threat_distance)
            if (workers.amount == 0):
                break
            # local_buildings: Units = self.bot.structures.filter(in_threat_distance)
            local_enemy_buildings: Units = self.bot.structures.filter(in_threat_distance)
            local_enemy_units: Units = self.bot.enemy_units.filter(in_threat_distance)
            
            match base.threat:
                case Threat.NO_THREAT:
                    # ask all chasing SCVs to stop
                    attacking_workers = workers.filter(lambda unit: unit.is_attacking)
                    for attacking_worker in attacking_workers:
                        attacking_worker.stop()
                    mules: Units = self.bot.units(UnitTypeId.MULE).collecting
                    damaged_mechanical_units = self.bot.units.filter(in_threat_distance).filter(
                        lambda unit: (unit.is_mechanical and unit.health_percentage < REPAIR_THRESHOLD)
                    )
                    self.repair_units(workers + mules, damaged_mechanical_units)
                
                case Threat.ATTACK:
                    if (workers.collecting.amount == 0):
                        print("no workers to pull, o7")
                        break
                    attackable_enemy_units: Units = local_enemy_units.filter(lambda unit: unit.is_flying == False and unit.can_be_attacked)
                    for worker in workers.collecting:
                        enemy_units_on_main_ramp: Units = attackable_enemy_units.filter(
                            lambda unit: (
                                unit.position.distance_to(self.bot.main_base_ramp.top_center) <= 5
                                and unit.position.distance_to(self.bot.main_base_ramp.bottom_center) <= 5
                            )
                        )
                        # Don't pull workers from the main if the wall is up and units are outside
                        if (
                            self.expansions.closest_to(worker).position == self.expansions.main.position
                            and enemy_units_on_main_ramp.amount >= 1
                        ):
                            return
                        if (attackable_enemy_units.amount >= 1):
                            worker.attack(attackable_enemy_units.closest_to(worker))
                        else:
                            Micro.move_away(worker, local_enemy_units.closest_to(worker), 1)
                
                case Threat.WORKER_SCOUT:
                    self.track_enemy_scout(workers, local_enemy_units, 1)
                
                case Threat.HARASS:
                    for worker in workers:
                        closest_enemy: Unit = (local_enemy_units + local_enemy_buildings).closest_to(worker)
                        if (closest_enemy.distance_to(worker) < closest_enemy.ground_range + 2):
                            Micro.move_away(worker, closest_enemy, 1)
                
                case Threat.CANON_RUSH:
                    canons: Units = self.bot.enemy_structures.filter(
                        lambda unit: (
                            unit.type_id == UnitTypeId.PHOTONCANNON
                            and local_buildings.closest_distance_to(unit) <= BASE_SIZE
                        )
                    )
                    pylons: Units = self.bot.enemy_structures.filter(
                        lambda unit: (
                            unit.type_id == UnitTypeId.PYLON
                            and local_buildings.closest_distance_to(unit) <= BASE_SIZE
                        )
                    )
                    # track the probes with 3 workers each
                    self.track_enemy_scout(workers, local_enemy_units, 3)
                    
                    # respond to canon rush
                    # Pull 3 workers by tower, 4 by pylon, less if we don't have enough
                    if (canons.amount == 0):
                        for pylon in pylons:
                            self.pull_workers(workers, pylon, 4)

                    for canon in canons:
                        if (canon.build_progress <= 0.5):
                            self.pull_workers(workers, canon, 3)
                        else:
                            self.pull_workers(workers, canon, (canon.build_progress * 8).__round__())
                
                case Threat.BUNKER_RUSH:
                    bunkers: Units = self.bot.enemy_structures.filter(
                        lambda unit: (
                            unit.type_id == UnitTypeId.BUNKER
                            and local_buildings.closest_distance_to(unit) <= BASE_SIZE
                        )
                    )
                    # track the SCVs with 3 workers each
                    self.track_enemy_scout(workers, local_enemy_units, 3)
                    
                    # try to destroy the constructing bunkers and give up on finished ones
                    for bunker in bunkers.filter(lambda unit: unit.build_progress < 1):
                        self.pull_workers(workers, bunker, 4)

    def pull_workers(self, workers: Units, target: Unit, amount: int):
        workers_attacking_tower = workers.filter(
            lambda unit: unit.is_attacking and unit.order_target == target.tag
        ).amount
        if (workers_attacking_tower >= 3):
            return

        amount_to_pull: int = amount - workers_attacking_tower
        closest_workers: Units = workers.collecting.sorted_by_distance_to(target)

        workers_pulled: Units = closest_workers[:amount_to_pull] if closest_workers.amount >= amount_to_pull else closest_workers

        for worker_pulled in workers_pulled:
            worker_pulled.attack(target)

    async def saturate_gas(self):
        # Saturate refineries
        for refinery in self.bot.gas_buildings:
            if (
                refinery.assigned_harvesters < refinery.ideal_harvesters
                and self.bot.vespene <= self.bot.minerals + 300
                and self.bot.workers.amount >= 5 * self.bot.townhalls.amount
            ):
                workers: Units = self.bot.workers.gathering.closer_than(10, refinery).filter(
                    lambda unit: self.bot.gas_buildings.find_by_tag(unit.orders[0].target) is None
                )
                if workers:
                    closest_worker = workers.closest_to(refinery)
                    closest_worker.gather(refinery)

    def track_enemy_scout(self, workers: Units, local_enemy_units: Units, max_scv_attacking = 1):
        for enemy_scout in local_enemy_units:
            if (workers.collecting.amount == 0):
                break
            closest_worker: Unit = workers.collecting.closest_to(enemy_scout)
            # if no scv is already chasing
            attacking_workers: Unit = workers.filter(
                lambda unit: unit.is_attacking and unit.order_target == enemy_scout.tag
            )
            if (attacking_workers.amount < max_scv_attacking):
                # pull 1 scv to follow it
                closest_worker.attack(enemy_scout)

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
            max_workers_repairing: int = 0.5 + (self.bot.townhalls.amount / 2).__round__()
            if (workers_repairing_unit.amount >= max_workers_repairing):
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

    async def distribute_workers(self):
        if (not self.bot.mineral_field or not self.bot.workers or not self.bot.townhalls.ready):
            return
        expansions_sorted_by_deficit_in_mining: Expansions = self.expansions.ready.sorted(
            key = lambda expansion: expansion.mineral_worker_count - expansion.optimal_mineral_workers,
        )

        most_saturated_expansion: Expansion = expansions_sorted_by_deficit_in_mining.last
        least_saturated_expansion: Expansion = expansions_sorted_by_deficit_in_mining.first
        for th in self.bot.townhalls.ready:
            if (len(th.rally_targets) >= 1 and th.rally_targets[0].tag not in least_saturated_expansion.mineral_fields.tags):
                th(AbilityId.RALLY_COMMANDCENTER, least_saturated_expansion.mineral_fields.random)
        
        for worker in self.bot.workers.idle:
            mineral_field_target: Unit = least_saturated_expansion.mineral_fields.random
            worker.gather(mineral_field_target)

        # make some movements with SCVs on oversaturated lines
        if (
            most_saturated_expansion.mineral_worker_count > most_saturated_expansion.optimal_mineral_workers
            and least_saturated_expansion.mineral_worker_count < least_saturated_expansion.optimal_mineral_workers - 2
        ):
            most_saturated_expansion.mineral_workers.random.stop()

        # saturate gas
        # v2
        # for expansion in self.expansions.filter(lambda expansion: expansion.refineries.amount >= 1):
        #     # Calculate the ideal number of gas workers per refinery
        #     total_vespene_workers_needed: int = expansion.desired_vespene_saturation * 3
        #     actual_vespene_workers: int = expansion.vespene_worker_count
        #     vespene_worker_difference: float = total_vespene_workers_needed - actual_vespene_workers

        #     # we don't change until we have a 0.75 difference
        #     if (abs(vespene_worker_difference) <= 0.5):
        #         break

        #     # Loop through refineries and check if they need workers
        #     for refinery in expansion.refineries:
        #         # Current assigned workers for the refinery
        #         current_workers = refinery.assigned_harvesters
                                
        #         # If the difference is above a threshold, we need to take action
        #         if (vespene_worker_difference > 0):  # If we need more workers (threshold of 0.5)
        #             # Find idle mineral workers
        #             mineral_workers: Units = expansion.mineral_workers.filter(
        #                 lambda unit: unit.is_carrying_minerals == False
        #             )
                    
        #             # If there are mineral workers, assign the closest to the refinery
        #             if mineral_workers.amount > 0:
        #                 mineral_workers.closest_to(refinery).gather(refinery)
        #                 break
                        
        #         elif (vespene_worker_difference < 0):  # If we have too many workers (threshold of -0.5)
        #             # Find vespene workers that are not carrying vespene and stop them
        #             vespene_workers: Units = expansion.vespene_workers.filter(
        #                 lambda unit: unit.is_carrying_vespene == False
        #             )
                    
        #             # Stop a worker if there's an excess
        #             if vespene_workers.amount >= 1:
        #                 vespene_workers.random.stop()
        #                 break

        # v1
        # for expansion in self.expansions.filter(lambda expansion: expansion.refineries.amount >= 1):
        #     # if we're oversaturated
        #     if (expansion.vespene_worker_count > expansion.desired_vespene_workers):
        #         vespene_workers: Units = expansion.vespene_workers.filter(lambda unit: unit.is_carrying_vespene == False)
        #         if (vespene_workers.amount >= 1):
        #             vespene_workers.random.stop()
        #     # if we're undersaturated
        #     if (expansion.vespene_worker_count < expansion.desired_vespene_workers):
        #         least_saturated_refinery: Unit = expansion.refineries.sorted(lambda unit: unit.assigned_harvesters).first
        #         mineral_workers: Units = expansion.mineral_workers.filter(
        #             lambda unit: unit.is_carrying_minerals == False
        #         )
        #         mineral_workers.closest_to(least_saturated_refinery).gather(least_saturated_refinery)
        #         break
        
        #v0
        expansion_sorted_by_vespene_mining: Expansions = self.expansions.filter(
            lambda expansion: expansion.refineries.amount >= 1
        ).sorted(
            key = lambda expansion: expansion.vespene_saturation,
            reverse = True
        )
        
        # we want 0 gas if saturation of any base is under 1/2 and we have 200 or more gas in bank
        if (least_saturated_expansion.mineral_saturation <= 1/2 and self.bot.vespene >= 200):
            # find a vespene worker and ask it to stop
            vespene_workers: Units = expansion_sorted_by_vespene_mining.first.vespene_workers
            if (vespene_workers.amount >= 1):
                vespene_workers.random.stop()
                return
        
        # we want to avoid oversaturation
        oversaturated_refineries: Units = self.bot.structures(UnitTypeId.REFINERY).filter(lambda unit: unit.assigned_harvesters >= 4)
        for oversaturated_ref in oversaturated_refineries:
            harvesters: Units = self.bot.workers.filter(
                lambda worker: worker.order_target == oversaturated_ref.tag and not worker.is_carrying_vespene
            )
            harvesters.random.stop()

        # we want saturation in gas if every mineral line is over 2/3rd saturation
        for expansion in self.expansions.taken:
            if (expansion.mineral_saturation <= 0.6):
                return
        
        expansions_not_saturated_in_vespene: Expansions = self.expansions.filter(
            lambda expansion: expansion.refineries.amount >= 1 and math.floor(expansion.vespene_saturation * 3) < expansion.desired_vespene_saturation * 3
        ).sorted(lambda expansion: expansion.vespene_saturation)
        
        for expansion in expansions_not_saturated_in_vespene:
            least_saturated_refinery: Unit = expansion.refineries.sorted(lambda unit: unit.assigned_harvesters).first
            mineral_workers: Units = expansion.mineral_workers.filter(
                lambda unit: unit.is_carrying_minerals == False
            )
            if (mineral_workers.amount == 0):
                continue
            mineral_workers.closest_to(least_saturated_refinery).gather(least_saturated_refinery)
            break